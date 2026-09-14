"""Unit and concurrency tests for the SQLite-backed ApprovalRepository.

Covers the DRAFT -> PENDING_REVIEW -> APPROVED/REJECTED happy paths with
audit-trail assertions, the revision-invalidation rule, self-approval
rejection, idempotent replay of approve/reject, and a concurrency test that
exercises the double-approval race guard. No network or LLM access is used
anywhere in this file.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

# apps/workshop is not installed as a package; add it directly to sys.path so
# these tests run with a plain `pytest` invocation, matching test_calculator.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from approval_repository import (  # noqa: E402
    ApprovalRepository,
    CaseNotFoundError,
    InvalidTransitionError,
    SelfApprovalError,
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
)

import pytest  # noqa: E402

PREPARER = "MOCK-CONTROLLER-001"
REVIEWER = "MOCK-REVIEWER-001"
OTHER_REVIEWER = "MOCK-REVIEWER-002"


@pytest.fixture()
def repo():
    repository = ApprovalRepository(":memory:")
    yield repository
    repository.close()


def _submitted_case(repo: ApprovalRepository, case_id: str = "CASE-SYN-TEST-001") -> str:
    repo.create_draft(case_id, PREPARER)
    repo.submit_for_review(case_id, PREPARER)
    return case_id


def test_draft_to_pending_review_to_approved_happy_path(repo):
    case_id = _submitted_case(repo)

    record = repo.approve(case_id, REVIEWER)

    assert record.state == STATE_APPROVED
    assert record.reviewer_id == REVIEWER
    assert record.approved_at is not None

    audit = repo.get_audit_trail(case_id)
    assert [event.command for event in audit] == ["CREATE_DRAFT", "SUBMIT", "APPROVE"]
    assert audit[0].from_state is None and audit[0].to_state == STATE_DRAFT
    assert audit[1].from_state == STATE_DRAFT and audit[1].to_state == STATE_PENDING_REVIEW
    assert audit[2].from_state == STATE_PENDING_REVIEW and audit[2].to_state == STATE_APPROVED
    assert audit[2].actor_id == REVIEWER
    assert [event.sequence for event in audit] == [1, 2, 3]


def test_draft_to_pending_review_to_rejected(repo):
    case_id = _submitted_case(repo)

    record = repo.reject(case_id, REVIEWER)

    assert record.state == STATE_REJECTED
    assert record.reviewer_id == REVIEWER
    assert record.approved_at is None

    audit = repo.get_audit_trail(case_id)
    assert [event.command for event in audit] == ["CREATE_DRAFT", "SUBMIT", "REJECT"]
    assert audit[2].to_state == STATE_REJECTED


def test_self_approval_is_rejected(repo):
    case_id = _submitted_case(repo)

    with pytest.raises(SelfApprovalError):
        repo.approve(case_id, PREPARER)

    with pytest.raises(SelfApprovalError):
        repo.reject(case_id, PREPARER)

    # The rejected attempts must not have changed state or recorded an event.
    record = repo.get_case(case_id)
    assert record.state == STATE_PENDING_REVIEW
    assert [event.command for event in repo.get_audit_trail(case_id)] == ["CREATE_DRAFT", "SUBMIT"]


def test_revising_an_approved_case_resets_to_draft_and_clears_reviewer(repo):
    case_id = _submitted_case(repo)
    repo.approve(case_id, REVIEWER)

    record = repo.revise(case_id, PREPARER)

    assert record.state == STATE_DRAFT
    assert record.reviewer_id is None
    assert record.approved_at is None
    assert record.revision == 2

    audit = repo.get_audit_trail(case_id)
    assert audit[-1].command == "REVISE"
    assert audit[-1].from_state == STATE_APPROVED
    assert audit[-1].to_state == STATE_DRAFT
    assert audit[-1].revision == 2

    # A revised case cannot open a training preview until re-approved.
    with pytest.raises(InvalidTransitionError):
        repo.open_training_preview(case_id, PREPARER)


def test_open_training_preview_only_permitted_when_approved(repo):
    case_id = _submitted_case(repo)

    with pytest.raises(InvalidTransitionError):
        repo.open_training_preview(case_id, PREPARER)

    repo.approve(case_id, REVIEWER)
    record = repo.open_training_preview(case_id, PREPARER)

    assert record.state == STATE_APPROVED
    assert repo.get_audit_trail(case_id)[-1].command == "OPEN_PREVIEW"


def test_idempotent_repeated_approve_calls_do_not_double_record(repo):
    case_id = _submitted_case(repo)

    first = repo.approve(case_id, REVIEWER)
    second = repo.approve(case_id, REVIEWER)
    third = repo.approve(case_id, REVIEWER)

    assert first == second == third
    audit = repo.get_audit_trail(case_id)
    assert [event.command for event in audit] == ["CREATE_DRAFT", "SUBMIT", "APPROVE"]


def test_idempotent_repeated_reject_calls_do_not_double_record(repo):
    case_id = _submitted_case(repo)

    first = repo.reject(case_id, REVIEWER)
    second = repo.reject(case_id, REVIEWER)

    assert first == second
    audit = repo.get_audit_trail(case_id)
    assert [event.command for event in audit] == ["CREATE_DRAFT", "SUBMIT", "REJECT"]


def test_a_different_reviewer_cannot_override_an_existing_decision(repo):
    case_id = _submitted_case(repo)
    repo.approve(case_id, REVIEWER)

    with pytest.raises(InvalidTransitionError):
        repo.approve(case_id, OTHER_REVIEWER)

    with pytest.raises(InvalidTransitionError):
        repo.reject(case_id, OTHER_REVIEWER)

    record = repo.get_case(case_id)
    assert record.state == STATE_APPROVED
    assert record.reviewer_id == REVIEWER


def test_unknown_case_id_raises_case_not_found_error(repo):
    with pytest.raises(CaseNotFoundError):
        repo.get_case("CASE-SYN-DOES-NOT-EXIST")


def test_concurrent_approve_calls_by_different_reviewers_yield_exactly_one_winner(repo):
    """Fires two approve() calls from separate threads with different
    reviewer ids against the same PENDING_REVIEW case.

    Approach taken and why: ApprovalRepository serializes every read/write
    through a single sqlite3.Connection guarded by a threading.Lock, so this
    test exercises the real lock plus the UPDATE ... WHERE state=/revision=
    guard that would still apply even without the Python-level lock (for
    example, if a future revision relaxed locking to allow multiple
    connections in WAL mode). True OS-level thread races on the SQLite file
    are not reproducible reliably in this environment, so this test proves
    the outcome that matters: exactly one thread transitions the case and
    exactly one APPROVE audit event is recorded, while the losing thread
    receives an explicit InvalidTransitionError rather than silently
    overwriting the winner or leaving duplicate audit rows.
    """
    case_id = _submitted_case(repo)

    results: dict[str, object] = {}
    barrier = threading.Barrier(2)

    def _approve(reviewer_id: str, key: str) -> None:
        barrier.wait()
        try:
            results[key] = repo.approve(case_id, reviewer_id)
        except InvalidTransitionError as exc:
            results[key] = exc

    thread_a = threading.Thread(target=_approve, args=(REVIEWER, "a"))
    thread_b = threading.Thread(target=_approve, args=(OTHER_REVIEWER, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    outcomes = [results["a"], results["b"]]
    winners = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    losers = [outcome for outcome in outcomes if isinstance(outcome, InvalidTransitionError)]

    assert len(winners) == 1
    assert len(losers) == 1
    assert winners[0].state == STATE_APPROVED
    assert winners[0].reviewer_id in (REVIEWER, OTHER_REVIEWER)

    record = repo.get_case(case_id)
    assert record.state == STATE_APPROVED
    assert record.reviewer_id == winners[0].reviewer_id

    audit = repo.get_audit_trail(case_id)
    approve_events = [event for event in audit if event.command == "APPROVE"]
    assert len(approve_events) == 1
