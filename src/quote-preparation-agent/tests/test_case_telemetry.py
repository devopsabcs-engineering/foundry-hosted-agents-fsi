"""Actual stage spans retain provenance without applicant input or invented LLM activity."""

from __future__ import annotations

import hashlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import case_telemetry  # noqa: E402


class Tracer:
    def __init__(self):
        self.spans = []

    @contextmanager
    def start_as_current_span(self, name, *, attributes, record_exception, set_status_on_exception):
        assert record_exception is False
        assert set_status_on_exception is False
        self.spans.append({"name": name, "attributes": attributes})
        yield


@pytest.mark.parametrize("reference", ["CASE-SYN-001", "person@example.test", "CASE-SYN-001\n"])
def test_stage_has_policy_lineage_without_unvalidated_input(monkeypatch, reference):
    tracer = Tracer()
    monkeypatch.setattr(case_telemetry, "TRACER", tracer)
    state = {"case_id": reference, "applicant_note": "private input", "amountCents": 90000}

    @case_telemetry.trace_stage("intake", "synthetic deterministic policy")
    def stage(value):
        assert value is state
        return {"intake_valid": reference == "CASE-SYN-001"}

    assert stage(state) == {"intake_valid": reference == "CASE-SYN-001"}
    assert tracer.spans[0]["name"] == "quote.intake"
    attributes = tracer.spans[0]["attributes"]
    assert attributes["app.workflow.execution_kind"] == "deterministic"
    assert attributes["app.workflow.policy_sha256"] == hashlib.sha256(
        b"synthetic deterministic policy"
    ).hexdigest()
    assert ("app.synthetic_case_id" in attributes) == (reference == "CASE-SYN-001")
    assert "private input" not in str(attributes) and "90000" not in str(attributes)
    assert not any("token" in key or "gen_ai" in key for key in attributes)


def test_telemetry_does_not_swallow_stage_failure(monkeypatch):
    tracer = Tracer()
    monkeypatch.setattr(case_telemetry, "TRACER", tracer)

    @case_telemetry.trace_stage("reference_lookup", "synthetic")
    def stage(state):
        raise RuntimeError("tool unavailable")

    with pytest.raises(RuntimeError, match="tool unavailable"):
        stage({"case_id": "CASE-SYN-002"})
    assert len(tracer.spans) == 1


def test_hosted_tracing_does_not_hide_initialization_failure(monkeypatch):
    class BrokenSdk:
        def init_tracing(self):
            raise ValueError("invalid telemetry configuration")

    class Adapter(case_telemetry.HostedTracing, BrokenSdk):
        pass

    monkeypatch.setattr(
        case_telemetry.trace, "get_tracer_provider", case_telemetry.trace.ProxyTracerProvider
    )
    with pytest.raises(ValueError, match="invalid telemetry configuration"):
        Adapter().init_tracing()
