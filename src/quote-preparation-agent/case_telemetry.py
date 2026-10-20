"""Payload-free workflow spans, exported through the existing agent-server provider."""

from __future__ import annotations

import hashlib
import re
from functools import wraps

from opentelemetry import trace

TRACER = trace.get_tracer("quote-preparation.workflow")


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
            with TRACER.start_as_current_span(f"quote.{stage}", attributes=attributes):
                return function(state)

        return invoke

    return decorate
