"""End-to-end tests for the quote-preparation LangGraph agent.

Runs the full intake -> reference-lookup -> composition graph against
synthetic fixtures, using a stubbed model callable (no live network call)
and a spy ApprovalRepository that fails immediately if agent code ever
calls approve/reject/revise/open_training_preview. No network, LLM, or
hosted-agent access is used anywhere in this file.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "workshop"))

import main  # noqa: E402
from approval_repository import ApprovalRepository  # noqa: E402

# Fields that must never appear in an applicant-facing message: raw
# rulebook rate/plan tables and reviewer-only case/audit fields.
_FORBIDDEN_MESSAGE_SUBSTRINGS = (
    "baseCents",
    "planAddOnCents",
    "WORKSHOP_AUTHORS_ONLY",
    "reviewerId",
    "actorId",
    "auditEvent",
    "80000",
    "90000",
    "100000",
    "110000",
)


def _stub_model(prompt: str) -> str:
    return "stub-model-response"


class _SpyRepository(ApprovalRepository):
    """Records create_draft/submit_for_review calls; fails the test
    immediately if agent code ever calls approve/reject/revise/
    open_training_preview -- those belong to a human reviewer only."""

    def __init__(self) -> None:
        super().__init__(":memory:")
        self.create_draft_calls: list[tuple[str, str]] = []
        self.submit_calls: list[tuple[str, str]] = []

    def create_draft(self, case_id: str, preparer_id: str):
        self.create_draft_calls.append((case_id, preparer_id))
        return super().create_draft(case_id, preparer_id)

    def submit_for_review(self, case_id: str, actor_id: str):
        self.submit_calls.append((case_id, actor_id))
        return super().submit_for_review(case_id, actor_id)

    def approve(self, *args: Any, **kwargs: Any):
        raise AssertionError("Agent code must never call approve() on the ApprovalRepository")

    def reject(self, *args: Any, **kwargs: Any):
        raise AssertionError("Agent code must never call reject() on the ApprovalRepository")

    def revise(self, *args: Any, **kwargs: Any):
        raise AssertionError("Agent code must never call revise() on the ApprovalRepository")

    def open_training_preview(self, *args: Any, **kwargs: Any):
        raise AssertionError("Agent code must never call open_training_preview() on the ApprovalRepository")


def _assert_message_is_bounded(applicant_message: dict[str, str]) -> None:
    assert set(applicant_message) == {"en-CA", "fr-CA"}
    combined = " ".join(applicant_message.values())
    for forbidden in _FORBIDDEN_MESSAGE_SUBSTRINGS:
        assert forbidden not in combined, f"applicant message leaked {forbidden!r}: {combined!r}"


def _run(case_id: str) -> tuple[dict[str, Any], _SpyRepository]:
    repository = _SpyRepository()
    final_state = main.run_case(case_id, repository=repository, model=_stub_model)
    return final_state, repository


def _assert_repository_never_decided(repository: _SpyRepository) -> None:
    assert repository.create_draft_calls, "composition must call create_draft"
    assert repository.submit_calls, "composition must call submit_for_review"


def test_ready_case_matches_exact_expected_amount():
    # CASE-SYN-001: COMPACT + TRAINING_EXTENDED = 80000 + 20000 cents.
    final_state, repository = _run("CASE-SYN-001")

    calculation = final_state["calculation"]
    assert calculation["status"] == "READY"
    assert calculation["amountCents"] == 100000
    assert final_state.get("issue_code") is None
    assert final_state["workflow_state"] == "PENDING_REVIEW"

    _assert_message_is_bounded(final_state["applicant_message"])
    _assert_repository_never_decided(repository)


def test_unsupported_case_never_invents_an_amount():
    # CASE-SYN-003: vehicleClass UNKNOWN is outside the rulebook's tables.
    final_state, repository = _run("CASE-SYN-003")

    calculation = final_state["calculation"]
    assert calculation["status"] == "UNSUPPORTED"
    assert calculation["amountCents"] is None
    assert final_state["issue_code"] == "UNSUPPORTED_INPUT"
    assert final_state["workflow_state"] == "PENDING_REVIEW"

    _assert_message_is_bounded(final_state["applicant_message"])
    _assert_repository_never_decided(repository)


def test_revision_fixture_case_matches_exact_expected_amount():
    # CASE-SYN-004: SEDAN + TRAINING_EXTENDED = 90000 + 20000 cents. The
    # fixture's own "workflow"/"expectedCalculation" test envelope records a
    # prior APPROVE+REVISE history, but get_application never returns that
    # envelope (only fixtureId/input), and this test's repository starts
    # empty, so the agent creates a brand-new DRAFT here.
    final_state, repository = _run("CASE-SYN-004")

    calculation = final_state["calculation"]
    assert calculation["status"] == "READY"
    assert calculation["amountCents"] == 110000
    assert final_state.get("issue_code") is None

    _assert_message_is_bounded(final_state["applicant_message"])
    _assert_repository_never_decided(repository)


def test_invalid_case_reference_never_reaches_the_calculator():
    final_state, repository = _run("NOT-A-CASE-ID")

    assert final_state.get("intake_valid") is False
    assert final_state.get("issue_code") == "INVALID_CASE_ID"
    assert "calculation" not in final_state or final_state["calculation"] is None

    _assert_message_is_bounded(final_state["applicant_message"])
    assert not repository.create_draft_calls
    assert not repository.submit_calls
