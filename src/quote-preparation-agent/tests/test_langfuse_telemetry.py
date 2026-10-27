"""Langfuse projection and configuration stay private, optional, and isolated."""

import base64
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import langfuse_telemetry as telemetry  # noqa: E402


@pytest.fixture(name="configured")
def configured_exporter(monkeypatch):
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.example.test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    exporter = InMemorySpanExporter()
    factory = Mock(return_value=exporter)
    monkeypatch.setattr(telemetry, "OTLPSpanExporter", factory)
    return factory, exporter


def test_disabled_by_default(monkeypatch, configured):
    monkeypatch.delenv("LANGFUSE_TRACING_ENABLED")
    provider = TracerProvider()
    try:
        assert not telemetry.configure_langfuse_export(provider, "graph")
        configured[0].assert_not_called()
    finally:
        provider.shutdown()


@pytest.mark.parametrize("host", [
    "https://langfuse.example.test/", "http://127.0.0.1:3000",
    "http://localhost:3000", "http://[::1]:3000",
])
def test_configure_once_with_dedicated_auth(configured, monkeypatch, host):
    monkeypatch.setenv("LANGFUSE_HOST", host)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://azure.example.test")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer azure-token")
    provider = TracerProvider()
    try:
        assert telemetry.configure_langfuse_export(provider, "graph")
        assert telemetry.configure_langfuse_export(provider, "graph")
        configured[0].assert_called_once()
        arguments = configured[0].call_args.kwargs
        assert arguments["endpoint"] == host.rstrip("/") + "/api/public/otel/v1/traces"
        assert arguments["headers"] == {
            "Authorization": "Basic " + base64.b64encode(b"pk-test:sk-test").decode(),
            "x-langfuse-ingestion-version": "4",
        }
        with provider.get_tracer(telemetry.SERVER_SCOPE).start_as_current_span("request"):
            pass
        assert provider.force_flush()
        assert len(configured[1].get_finished_spans()) == 1
    finally:
        provider.shutdown()


@pytest.mark.parametrize("host", [
    "", "http://langfuse.example.test", "http://localhost.example.test:3000",
    "https://user:password@langfuse.example.test", "https://langfuse.example.test/path",
    "https://langfuse.example.test?secret=value", "https://langfuse.example.test#secret",
    "https://langfuse.example.test:bad", "https://langfuse.example.test:0",
])
def test_bad_endpoint_disables_only_optional_export(configured, monkeypatch, caplog, host):
    monkeypatch.setenv("LANGFUSE_HOST", host)
    provider = TracerProvider()
    try:
        assert not telemetry.configure_langfuse_export(provider, "graph")
        configured[0].assert_not_called()
        assert "Azure tracing is unchanged" in caplog.text
        assert "password" not in caplog.text and "sk-test" not in caplog.text
    finally:
        provider.shutdown()


@pytest.mark.parametrize("key", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"])
def test_missing_configuration_is_nonfatal(configured, monkeypatch, key):
    monkeypatch.delenv(key)
    provider = TracerProvider()
    try:
        assert not telemetry.configure_langfuse_export(provider, "graph")
        configured[0].assert_not_called()
    finally:
        provider.shutdown()


def test_projection_removes_payload_without_mutating_azure_spans():
    native = InMemorySpanExporter()
    copies = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource({"private.host": "applicant-secret"}))
    provider.add_span_processor(SimpleSpanProcessor(native))
    provider.add_span_processor(SimpleSpanProcessor(telemetry.MetadataOnlyExporter(copies, "graph")))
    try:
        server = provider.get_tracer(telemetry.SERVER_SCOPE)
        workflow = provider.get_tracer(telemetry.WORKFLOW_SCOPE)
        with server.start_as_current_span("applicant-secret") as root:
            root.set_attribute("private.input", "applicant-secret")
            root.record_exception(RuntimeError("applicant-secret"))
            root.set_status(trace.Status(trace.StatusCode.ERROR, "applicant-secret"))
            with workflow.start_as_current_span("applicant-secret", attributes={
                "app.workflow.stage": "INTAKE",
                "app.workflow.policy_sha256": "a" * 64,
                "app.synthetic_case_id": "CASE-SYN-001",
                "app.case_revision": 2,
                "app.preparation_id": "b" * 16,
                "gen_ai.prompt": "applicant-secret",
                "langfuse.observation.input": "applicant-secret",
                "private.output": "applicant-secret",
            }):
                pass
            with provider.get_tracer("database").start_as_current_span("applicant-secret"):
                pass
            with workflow.start_as_current_span("applicant-secret", attributes={
                "app.workflow.stage": "applicant-secret",
                "app.synthetic_case_id": "person@example.test",
                "app.workflow.policy_sha256": "applicant-secret",
                "app.case_revision": True,
            }):
                pass
        assert len(native.get_finished_spans()) == 4
        projected = copies.get_finished_spans()
        assert len(projected) == 3
        original_by_id = {span.context.span_id: span for span in native.get_finished_spans()}
        for span in projected:
            original = original_by_id[span.context.span_id]
            assert span.context.trace_id == original.context.trace_id
            assert span.parent == original.parent
            assert span.start_time == original.start_time and span.end_time == original.end_time
            assert span.status.status_code == original.status.status_code
            assert not span.events and not span.links
            assert span.status.description is None
            assert "applicant-secret" not in span.to_json()
            assert "person@example.test" not in span.to_json()
            assert not any(key.startswith("gen_ai.") for key in span.attributes)
        assert projected[0].name == "quote.INTAKE"
        assert projected[0].attributes["app.synthetic_case_id"] == "CASE-SYN-001"
        assert projected[1].name == "workflow.operation"
        assert "app.case_revision" not in projected[1].attributes
        assert native.get_finished_spans()[-1].events
        assert native.get_finished_spans()[-1].name == "applicant-secret"
    finally:
        provider.shutdown()


def test_failed_export_and_shutdown_never_raise_or_log_exception(caplog):
    exporter = Mock()
    exporter.export.side_effect = RuntimeError("credential-secret")
    exporter.shutdown.side_effect = RuntimeError("credential-secret")
    safe = telemetry.MetadataOnlyExporter(exporter, "graph")
    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    try:
        with provider.get_tracer(telemetry.SERVER_SCOPE).start_as_current_span("request"):
            pass
        assert safe.export(memory.get_finished_spans()) is SpanExportResult.FAILURE
        safe.shutdown()
        assert "Optional Langfuse export failed" in caplog.text
        assert "credential-secret" not in caplog.text
    finally:
        provider.shutdown()


def test_real_otlp_http_export_preserves_identity_without_payload(monkeypatch):
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    received = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, self.headers, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, message_format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Receiver)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    for key in list(os.environ):
        if key.startswith("OTEL_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    provider = TracerProvider(resource=Resource({"private.host": "applicant-secret"}))
    try:
        assert telemetry.configure_langfuse_export(provider, "graph")
        with provider.get_tracer(telemetry.SERVER_SCOPE).start_as_current_span("applicant-secret") as root:
            root.set_attribute("private.input", "applicant-secret")
            root.record_exception(RuntimeError("applicant-secret"))
            context = root.get_span_context()
        assert provider.force_flush(timeout_millis=10000)
        assert len(received) == 1
        path, headers, body = received[0]
        assert path == "/api/public/otel/v1/traces"
        assert headers["Authorization"] == "Basic " + base64.b64encode(b"pk-test:sk-test").decode()
        assert headers["authorization"] == headers["Authorization"]
        assert headers["x-langfuse-ingestion-version"] == "4"
        assert b"applicant-secret" not in body
        message = ExportTraceServiceRequest.FromString(body)
        (resource_spans,) = message.resource_spans
        (scope_spans,) = resource_spans.scope_spans
        (span,) = scope_spans.spans
        assert span.name == "agent.request"
        assert span.trace_id.hex() == f"{context.trace_id:032x}"
        assert span.span_id.hex() == f"{context.span_id:016x}"
        assert not span.events and not span.links
    finally:
        provider.shutdown()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)