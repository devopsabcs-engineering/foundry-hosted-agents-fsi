"""Optional, metadata-only OTLP export alongside the SDK-owned Azure pipeline."""

from __future__ import annotations

import base64
import logging
import os
import re
from threading import Lock
from urllib.parse import urlsplit
from weakref import WeakSet

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

LOGGER = logging.getLogger(__name__)
CONFIGURATION_LOCK = Lock()
CONFIGURED_PROVIDERS = WeakSet()
WORKFLOW_SCOPE = "quote-preparation.workflow"
SERVER_SCOPE = "azure.ai.agentserver.core.server.base"
STAGES = {"INTAKE", "REFERENCE_LOOKUP", "COMPOSITION"}


def _context(context):
    if context is None:
        return None
    return trace.SpanContext(
        context.trace_id, context.span_id, context.is_remote, context.trace_flags
    )


def _safe_span(span):
    attributes = {"langfuse.trace.name": "quote-preparation"}
    name = "agent.request" if span.instrumentation_scope.name == SERVER_SCOPE else "workflow.operation"
    if span.instrumentation_scope.name == WORKFLOW_SCOPE:
        source = span.attributes or {}
        stage = source.get("app.workflow.stage")
        if isinstance(stage, str) and stage in STAGES:
            name = f"quote.{stage}"
            attributes["app.workflow.stage"] = stage
            attributes["langfuse.observation.metadata.stage"] = stage
        attributes["app.workflow.execution_kind"] = "deterministic"
        for key, pattern in (
            ("app.workflow.policy_sha256", r"[0-9a-f]{64}"),
            ("app.synthetic_case_id", r"CASE-SYN-[0-9]{3}"),
            ("app.preparation_id", r"[0-9a-f]{16}"),
        ):
            value = source.get(key)
            if isinstance(value, str) and re.fullmatch(pattern, value):
                attributes[key] = value
        revision = source.get("app.case_revision")
        if isinstance(revision, int) and not isinstance(revision, bool) and 0 < revision <= 1_000_000:
            attributes["app.case_revision"] = revision
    return ReadableSpan(
        name=name,
        context=_context(span.context),
        parent=_context(span.parent),
        resource=Resource({"service.name": "quote-preparation-agent"}),
        attributes=attributes,
        kind=span.kind,
        status=trace.Status(span.status.status_code),
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=InstrumentationScope("quote-preparation.langfuse"),
    )


class MetadataOnlyExporter(SpanExporter):
    """Project approved scopes without mutating spans sent to Azure."""

    def __init__(self, exporter, callback_scope):
        self.exporter = exporter
        self.scopes = {WORKFLOW_SCOPE, SERVER_SCOPE, callback_scope}

    def export(self, spans):
        try:
            selected = [
                _safe_span(span) for span in spans
                if span.instrumentation_scope and span.instrumentation_scope.name in self.scopes
            ]
            if not selected:
                return SpanExportResult.SUCCESS
            return self.exporter.export(selected)
        except Exception:
            LOGGER.warning("Optional Langfuse export failed; Azure tracing is unchanged.")
            return SpanExportResult.FAILURE

    def shutdown(self):
        try:
            self.exporter.shutdown()
        except Exception:
            LOGGER.warning("Optional Langfuse exporter shutdown failed.")


def configure_langfuse_export(provider, callback_scope):
    """Attach once after the host initializes tracing; never replace its provider."""
    if os.getenv("LANGFUSE_TRACING_ENABLED", "false").lower() != "true":
        return False
    with CONFIGURATION_LOCK:
        if provider in CONFIGURED_PROVIDERS:
            return True
        try:
            host = os.environ["LANGFUSE_HOST"].rstrip("/")
            parsed = urlsplit(host)
            loopback_http = parsed.scheme == "http" and parsed.hostname in {
                "localhost", "127.0.0.1", "::1"
            }
            if (
                (parsed.scheme != "https" and not loopback_http) or not parsed.hostname
                or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment
                or parsed.port == 0
            ):
                raise ValueError("HTTPS or a loopback-only HTTP origin is required")
            public_key = os.environ["LANGFUSE_PUBLIC_KEY"]
            secret_key = os.environ["LANGFUSE_SECRET_KEY"]
            if not public_key or not secret_key or ":" in public_key:
                raise ValueError("Project credentials are required")
            if not isinstance(provider, TracerProvider):
                raise ValueError("The host must initialize its provider first")
            authorization = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode("ascii")
            exporter = OTLPSpanExporter(
                endpoint=f"{host}/api/public/otel/v1/traces",
                headers={"Authorization": f"Basic {authorization}", "x-langfuse-ingestion-version": "4"},
                timeout=5,
            )
            processor = BatchSpanProcessor(
                MetadataOnlyExporter(exporter, callback_scope),
                max_queue_size=512,
                max_export_batch_size=64,
                schedule_delay_millis=1000,
                export_timeout_millis=5000,
            )
            provider.add_span_processor(processor)
            CONFIGURED_PROVIDERS.add(provider)
            return True
        except Exception:
            LOGGER.warning("Optional Langfuse tracing is not configured; Azure tracing is unchanged.")
            return False