"""Exercise the installed agent-server SDK and real OTel globals without ingestion."""

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.mark.parametrize("existing_provider", [False, True])
def test_sdk_and_workflow_share_one_payload_safe_provider(existing_provider):
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith((
            "OTEL_", "APPLICATIONINSIGHTS_", "AZURE_AI_", "AGENT_",
            "LANGSMITH_", "LANGCHAIN_",
        ))
    }
    env["ENABLE_APPLICATION_INSIGHTS_LOGGER"] = "false"
    script = dedent("""
        import asyncio
        import os
        import sys
        from uuid import uuid4
        from unittest.mock import patch

        sys.path.insert(0, sys.argv[1])
        import main
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from azure.ai.agentserver.langgraph.langgraph import LangGraphAdapter
        from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer
        from approval_repository import ApprovalRepository
        from case_telemetry import trace_stage
        from graph import build_graph

        existing = sys.argv[2] == "True"
        exported = InMemorySpanExporter()
        providers = []
        adapters = []

        def capture_exporter(self, connection_string, provider):
            providers.append(provider)
            provider.add_span_processor(SimpleSpanProcessor(exported))

        if existing:
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(exported))
            trace.set_tracer_provider(provider)

        os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = "replaced-by-memory"

        def run(self, port):
            assert port == 8088
            adapters.append(self)
            credential = self.credentials
            self.init_tracing()
            self.init_tracing()
            assert self.credentials is credential
            async def invoke_graph(streaming):
                kwargs = {"config": {"callbacks": [self.azure_ai_tracer]}}
                if streaming:
                    async for _ in self._graph.astream({"case_id": "CASE-SYN-001"}, **kwargs):
                        pass
                else:
                    await self._graph.ainvoke({"case_id": "CASE-SYN-001"}, **kwargs)

            for streaming in (False, True):
                self._graph = build_graph(repository=ApprovalRepository(":memory:"))
                exported.clear()
                with self.tracer.start_as_current_span("HostedAgents-test") as root:
                    root_context = root.get_span_context()
                    asyncio.run(invoke_graph(streaming))
                spans = exported.get_finished_spans()
                stages = [span for span in spans if span.name.startswith("quote.")]
                assert [span.name for span in stages] == [
                    "quote.INTAKE", "quote.REFERENCE_LOOKUP", "quote.COMPOSITION",
                ]
                for span in stages:
                    assert span.context.trace_id == root_context.trace_id
                    assert span.parent.span_id == root_context.span_id
                    assert set(span.attributes) == {
                        "app.workflow.stage", "app.workflow.policy_sha256",
                        "app.workflow.execution_kind", "app.synthetic_case_id",
                    }
                    assert span.attributes["app.synthetic_case_id"] == "CASE-SYN-001"
            callback = self.azure_ai_tracer
            assert isinstance(callback, AzureAIOpenTelemetryTracer)
            callback_run = uuid4()
            callback.on_chain_start(
                {"name": "payload-test"}, {"private": "applicant-secret"},
                run_id=callback_run, name="LangGraph",
            )
            callback.on_chain_end({"private": "applicant-secret"}, run_id=callback_run)
            callback_run = uuid4()
            callback.on_chain_start(
                {"name": "payload-test"}, {"private": "applicant-secret"},
                run_id=callback_run, name="LangGraph",
            )
            callback.on_chain_error(RuntimeError("applicant-secret"), run_id=callback_run)
            assert callback._content_recording is False
            assert not monitor.called, "SDK callback created a second telemetry pipeline"
            assert len(providers) == (0 if existing else 1)
            assert trace.get_tracer_provider() is (provider if existing else providers[0])
            @trace_stage("failure", "bounded synthetic policy")
            def fails(state):
                raise RuntimeError("private failure payload")

            try:
                fails({"case_id": "person@example.test"})
            except RuntimeError as exc:
                assert str(exc) == "private failure payload"
            else:
                raise AssertionError("Stage error was swallowed")
            failure = exported.get_finished_spans()[-1]
            assert failure.name == "quote.failure"
            assert not failure.events
            assert failure.status.description is None
            assert "app.synthetic_case_id" not in failure.attributes
            assert "applicant-secret" not in str([
                (
                    dict(span.attributes),
                    [dict(event.attributes) for event in span.events],
                    span.status.description,
                )
                for span in exported.get_finished_spans()
            ])
            asyncio.run(self.credentials.close())

        with (
            patch.object(LangGraphAdapter, "setup_application_insights_exporter", capture_exporter),
            patch.object(LangGraphAdapter, "run", run),
            patch.object(AzureAIOpenTelemetryTracer, "_configure_azure_monitor") as monitor,
            patch.object(main, "build_graph", lambda: build_graph(repository=ApprovalRepository(":memory:"))),
        ):
            main.serve()
        assert len(adapters) == 1
        trace.get_tracer_provider().shutdown()
    """)
    result = subprocess.run(
        [sys.executable, "-c", script, str(Path(__file__).resolve().parents[1]), str(existing_provider)],
        env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
