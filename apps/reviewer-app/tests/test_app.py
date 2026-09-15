"""API tests for the reviewer approval surface.

Auth is faked with a small duck-typed class passed into `create_app`, matching
`apps/web-chat/tests/test_app.py`. The case store is a real `SqliteCaseStore`
rather than a mock, so every assertion below is made against the actual state
machine: self-approval ordering, idempotent replay, and the compare-and-swap.
"""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(REPO_ROOT / "src" / "quote-preparation-agent"))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import Settings, create_app  # noqa: E402
from auth import Identity  # noqa: E402
from case_store import (  # noqa: E402
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
    ApprovalRepositoryError,
    CalculationSnapshot,
)
from sqlite_case_store import SqliteCaseStore  # noqa: E402

SETTINGS = Settings("tenant", "client")
PREPARER = "MOCK-CONTROLLER-001"
REVIEWER = "MOCK-REVIEWER-001"

READY = CalculationSnapshot(
    status="READY",
    amount_cents=142500,
    currency="CAD",
    period="TRAINING_YEAR",
    rule_ids=("RULE-SYN-BASE",),
    issues=(),
    rulebook_version="training-1",
)

UNSUPPORTED = CalculationSnapshot(
    status="UNSUPPORTED",
    amount_cents=None,
    currency="CAD",
    period="TRAINING_YEAR",
    rule_ids=(),
    issues=("UNSUPPORTED_INPUT",),
    rulebook_version="training-1",
)


class FakeAuth:
    """Stands in for `ReviewerAuth`. `norole` models a valid token whose
    `roles` claim does not carry the reviewer role."""

    async def authorize(self, header):
        if header == "Bearer reviewer":
            return Identity("tenant", REVIEWER, "Reviewer")
        if header == "Bearer preparer":
            return Identity("tenant", PREPARER, "Reviewer")
        if header == "Bearer norole":
            raise HTTPException(403, "Reviewer role is required. Contact the pilot administrator.")
        raise HTTPException(401, "Sign in to continue.")


class BrokenStore:
    def list_cases_by_state(self, state, limit=100):
        raise ApprovalRepositoryError("connection string secret-value-do-not-leak")

    def close(self):
        pass


@pytest.fixture
def client():
    store = SqliteCaseStore(":memory:")
    application = create_app(SETTINGS, FakeAuth(), store)
    with TestClient(application) as test_client:
        test_client.headers["Authorization"] = "Bearer reviewer"
        yield test_client, store
    store.close()


def seed(store, case_id, calculation=READY):
    store.create_draft(case_id, PREPARER)
    return store.submit_for_review_with_calculation(case_id, PREPARER, calculation=calculation)


def test_health_and_config_do_not_require_a_token(client):
    test_client, _ = client
    test_client.headers.clear()
    assert test_client.get("/healthz").json() == {"status": "ok"}
    config = test_client.get("/api/config").json()
    assert config["scope"] == "api://client/Review.Access"
    assert config["role"] == "Reviewer"


def test_unauthenticated_requests_are_rejected(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    test_client.headers.clear()
    assert test_client.get("/api/me").status_code == 401
    assert test_client.get("/api/cases").status_code == 401
    assert test_client.get("/api/cases/CASE-SYN-001").status_code == 401
    assert test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1}).status_code == 401
    assert store.get_case("CASE-SYN-001").state == STATE_PENDING_REVIEW


def test_valid_token_without_the_reviewer_role_is_forbidden(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    test_client.headers["Authorization"] = "Bearer norole"
    assert test_client.get("/api/cases").status_code == 403
    denied = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1})
    assert denied.status_code == 403
    # A revoked role must not be reported as self-approval.
    assert "code" not in denied.json()
    assert store.get_case("CASE-SYN-001").state == STATE_PENDING_REVIEW


def test_empty_queue(client):
    test_client, _ = client
    assert test_client.get("/api/cases").json() == {"cases": []}


def test_queue_carries_the_premium_and_tolerates_a_null_amount(client):
    test_client, store = client
    seed(store, "CASE-SYN-001", READY)
    seed(store, "CASE-SYN-003", UNSUPPORTED)
    store.create_draft("CASE-SYN-009", PREPARER)

    cases = {case["caseId"]: case for case in test_client.get("/api/cases").json()["cases"]}

    assert set(cases) == {"CASE-SYN-001", "CASE-SYN-003"}
    assert cases["CASE-SYN-001"]["amountCents"] == 142500
    assert cases["CASE-SYN-001"]["currency"] == "CAD"
    assert cases["CASE-SYN-001"]["calculationStatus"] == "READY"
    assert cases["CASE-SYN-003"]["amountCents"] is None
    assert cases["CASE-SYN-003"]["calculationStatus"] == "UNSUPPORTED"
    assert cases["CASE-SYN-003"]["issues"] == ["UNSUPPORTED_INPUT"]


def test_case_detail_returns_the_audit_trail(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    body = test_client.get("/api/cases/CASE-SYN-001").json()
    assert body["case"]["revision"] == 1
    assert [event["command"] for event in body["auditTrail"]] == ["CREATE_DRAFT", "SUBMIT"]
    assert test_client.get("/api/cases/CASE-SYN-404").status_code == 404


def test_approve_records_the_decision(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    response = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1})
    assert response.status_code == 200
    assert response.json()["case"]["state"] == STATE_APPROVED
    assert response.json()["case"]["reviewerId"] == REVIEWER
    assert store.get_case("CASE-SYN-001").approved_at is not None


def test_self_approval_is_forbidden(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    test_client.headers["Authorization"] = "Bearer preparer"
    response = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1})
    assert response.status_code == 403
    # The code is what lets the frontend distinguish this from the authorization
    # 403s raised in auth.py, which carry different remediation.
    assert response.json()["code"] == "SELF_APPROVAL"
    assert store.get_case("CASE-SYN-001").state == STATE_PENDING_REVIEW


def test_a_stale_revision_loses_the_compare_and_swap(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    assert test_client.post("/api/cases/CASE-SYN-001/revise", json={"revision": 1}).status_code == 200
    assert store.get_case("CASE-SYN-001").revision == 2

    stale = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1})

    assert stale.status_code == 409
    assert store.get_case("CASE-SYN-001").state == STATE_DRAFT


def test_replaying_a_decision_appends_no_second_audit_event(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    headers = {"Idempotency-Key": "8f1c3a2e-0000-4000-8000-000000000001"}
    first = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1}, headers=headers)
    replay = test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1}, headers=headers)

    assert (first.status_code, replay.status_code) == (200, 200)
    assert first.json() == replay.json()
    commands = [event.command for event in store.get_audit_trail("CASE-SYN-001")]
    assert commands.count("APPROVE") == 1


def test_a_decided_case_cannot_be_flipped_by_another_reviewer(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    assert test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1}).status_code == 200
    conflict = test_client.post("/api/cases/CASE-SYN-001/reject", json={"revision": 1})
    assert conflict.status_code == 409
    assert store.get_case("CASE-SYN-001").state == STATE_APPROVED


def test_reject_accepts_a_reason_code(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    response = test_client.post(
        "/api/cases/CASE-SYN-001/reject", json={"revision": 1, "reasonCode": "MISSING_PLAN"}
    )
    assert response.status_code == 200
    assert response.json()["case"]["state"] == STATE_REJECTED
    assert store.get_case("CASE-SYN-001").reviewer_id == REVIEWER
    assert store.get_audit_trail("CASE-SYN-001")[-1].reason_code == "MISSING_PLAN"


def test_the_reason_code_reaches_the_audit_trail_response(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    test_client.post(
        "/api/cases/CASE-SYN-001/reject", json={"revision": 1, "reasonCode": "MISSING_PLAN"}
    )

    trail = test_client.get("/api/cases/CASE-SYN-001").json()["auditTrail"]

    assert [event["reasonCode"] for event in trail] == [None, None, "MISSING_PLAN"]


def test_a_decision_without_a_reason_code_records_none(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    assert test_client.post("/api/cases/CASE-SYN-001/approve", json={"revision": 1}).status_code == 200

    assert store.get_audit_trail("CASE-SYN-001")[-1].reason_code is None


def test_revise_returns_the_case_to_draft(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    response = test_client.post(
        "/api/cases/CASE-SYN-001/revise", json={"revision": 1, "reasonCode": "NEEDS_DETAIL"}
    )
    assert response.status_code == 200
    assert response.json()["case"]["state"] == STATE_DRAFT
    assert response.json()["case"]["revision"] == 2
    assert test_client.get("/api/cases").json() == {"cases": []}


def test_decisions_on_an_unknown_case_return_404(client):
    test_client, _ = client
    assert test_client.post("/api/cases/CASE-SYN-404/approve", json={"revision": 1}).status_code == 404


@pytest.mark.parametrize("body", [
    {}, {"revision": 0}, {"revision": "one"}, {"revision": 1, "reasonCode": "lower case"},
    {"revision": 1, "reasonCode": ""}, {"revision": 1, "note": "extra"},
])
def test_invalid_decision_bodies_are_rejected(client, body):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    assert test_client.post("/api/cases/CASE-SYN-001/reject", json=body).status_code == 422
    assert store.get_case("CASE-SYN-001").state == STATE_PENDING_REVIEW


def test_approve_does_not_accept_a_reason_code(client):
    test_client, store = client
    seed(store, "CASE-SYN-001")
    response = test_client.post(
        "/api/cases/CASE-SYN-001/approve", json={"revision": 1, "reasonCode": "MISSING_PLAN"}
    )
    assert response.status_code == 422
    assert store.get_case("CASE-SYN-001").state == STATE_PENDING_REVIEW


def test_malformed_case_ids_are_rejected(client):
    test_client, _ = client
    assert test_client.get("/api/cases/not%20a%20case%20id").status_code == 422
    assert test_client.get(f"/api/cases/{'x' * 65}").status_code == 422


def test_oversized_requests_are_refused(client):
    test_client, _ = client
    response = test_client.post(
        "/api/cases/CASE-SYN-001/reject", json={"revision": 1, "reasonCode": "A" * 9000}
    )
    assert response.status_code == 413


def test_security_headers_are_present(client):
    test_client, _ = client
    headers = test_client.get("/healthz").headers
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_store_failures_return_a_generic_500():
    application = create_app(SETTINGS, FakeAuth(), BrokenStore())
    with TestClient(application, raise_server_exceptions=False) as test_client:
        test_client.headers["Authorization"] = "Bearer reviewer"
        response = test_client.get("/api/cases")
    assert response.status_code == 500
    assert response.json() == {"detail": "The case store is unavailable."}
    assert "secret-value-do-not-leak" not in response.text
