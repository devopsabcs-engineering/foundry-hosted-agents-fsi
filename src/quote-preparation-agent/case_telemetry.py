"""Payload-free workflow spans, exported through the existing agent-server provider."""

from __future__ import annotations

import hashlib
import re
from functools import wraps

from opentelemetry import trace

TRACER = trace.get_tracer("quote-preparation.workflow")


class HostedTracing:
    """Share the SDK's exporter with workflow and payload-free LangGraph spans."""

    def init_tracing(self):
        if getattr(self, "_workflow_tracing_initialized", False):
            return

        provider = trace.get_tracer_provider()
        if isinstance(provider, trace.ProxyTracerProvider):
            super().init_tracing()
        else:
            # OTel permits one global provider. Do not create orphan exporters
            # when the host has already installed its authenticated pipeline.
            self.tracer = provider.get_tracer("azure.ai.agentserver.core.server.base")
            self.init_tracing_internal()
        self._workflow_tracing_initialized = True

    def init_tracing_internal(self, exporter_endpoint=None, app_insights_conn_str=None):
        from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

        class WorkflowTracer(AzureAIOpenTelemetryTracer):
            def on_chain_error(self, error, *, run_id, **kwargs):
                # The SDK records exception text even with content disabled.
                super().on_chain_error(
                    RuntimeError("Deterministic workflow failed"),
                    run_id=run_id,
                    **kwargs,
                )

        # A nonempty connection string makes this callback configure Azure
        # Monitor a second time. It only needs the provider installed above.
        self.azure_ai_tracer = WorkflowTracer(
            connection_string="",
            enable_content_recording=False,
            name=self.get_agent_identifier(),
        )


def trace_stage(stage: str, policy: str):
    """Record actual deterministic stages, not invented model/token activity."""
    policy_hash = hashlib.sha256(policy.encode("utf-8")).hexdigest()

    def decorate(function):
        @wraps(function)
        def invoke(state):
            attributes = {
                "app.workflow.stage": stage,
                "app.workflow.policy_sha256": policy_hash,
                "app.workflow.execution_kind": "deterministic",
            }
            case_id = state.get("case_id")
            if isinstance(case_id, str) and re.fullmatch(r"CASE-SYN-[0-9]{3}", case_id):
                attributes["app.synthetic_case_id"] = case_id
            with TRACER.start_as_current_span(
                f"quote.{stage}",
                attributes=attributes,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                completed = False
                try:
                    result = function(state)
                    completed = True
                    return result
                finally:
                    if not completed:
                        span.set_status(trace.StatusCode.ERROR)

        return invoke

    return decorate
