"""Backend-agnostic contract tests for the quote-preparation case store.

One suite, parameterised over every `CaseStore` implementation, so the SQLite
store and the Cosmos store are held to the same state machine rather than to
two drifting sets of assertions.

Backends:

* `sqlite` -- `SqliteCaseStore(":memory:")`.
* `cosmos-fake` -- the real `CosmosCaseStore` driven against an in-process
  container double. The double is only worth having because it enforces ETag
  preconditions for real: `replace_item` compares the supplied ETag against the
  stored one and raises `CosmosAccessConditionFailedError` on a mismatch,
  exactly as the service does. A double that ignored the precondition would
  make every concurrency assertion below vacuous.
* `cosmos-live` -- the same class against a real account, used only when
  `COSMOS_ENDPOINT` is set and reachable with the ambient Entra credential.
  Skipped with an explicit reason otherwise. The Cosmos DB emulator is not a
  usable target here: it authenticates with a well-known account key, and this
  store accepts Entra credentials only.

No network, LLM, or hosted-agent access is used by the default backends.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "workshop"))

import pytest  # noqa: E402
from azure.cosmos.exceptions import (  # noqa: E402
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from case_store import (  # noqa: E402
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
    CalculationSnapshot,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidTransitionError,
    SelfApprovalError,
)
from cosmos_case_store import CosmosCaseStore  # noqa: E402
from sqlite_case_store import SqliteCaseStore  # noqa: E402

PREPARER = "MOCK-CONTROLLER-001"
REVIEWER = "MOCK-REVIEWER-001"
OTHER_REVIEWER = "MOCK-REVIEWER-002"

READY_CALCULATION = CalculationSnapshot(
    status="READY",
    amount_cents=100000,
    currency="CAD",
    period="TRAINING_YEAR",
    rule_ids=("RULE-SYN-BASE", "RULE-SYN-PLAN", "RULE-SYN-REVIEW"),
    issues=(),
    rulebook_version="training-1",
)

UNSUPPORTED_CALCULATION = CalculationSnapshot(
    status="UNSUPPORTED",
    amount_cents=None,
    currency="CAD",
    period="TRAINING_YEAR",
    rule_ids=(),
    issues=("UNSUPPORTED_INPUT",),
    rulebook_version="training-1",
)


class FakeCosmosContainer:
    """In-process stand-in for a Cosmos container that enforces ETags.

    Only the four operations `CosmosCaseStore` uses are implemented.
    `query_items` ignores the query text and filters on the `@state` parameter,
    because the store issues exactly one query shape; the point of this double
    is the concurrency contract, not a SQL engine.
    """

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._etag_counter = 0
        self.replace_calls = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f'"etag-{self._etag_counter}"'

    def create_item(self, body: dict[str, Any]) -> dict[str, Any]:
        if body["id"] in self._items:
            raise CosmosResourceExistsError()
        stored = deepcopy(body)
        stored["_etag"] = self._next_etag()
        self._items[stored["id"]] = stored
        return deepcopy(stored)

    def read_item(self, item: str, partition_key: str) -> dict[str, Any]:
        if item not in self._items:
            raise CosmosResourceNotFoundError()
        return deepcopy(self._items[item])

    def replace_item(
        self,
        item: str,
        body: dict[str, Any],
        etag: str | None = None,
        match_condition: Any = None,
    ) -> dict[str, Any]:
        self.replace_calls += 1
        if item not in self._items:
            raise CosmosResourceNotFoundError()
        if etag is not None and self._items[item]["_etag"] != etag:
            raise CosmosAccessConditionFailedError()
        stored = deepcopy(body)
        stored["_etag"] = self._next_etag()
        self._items[item] = stored
        return deepcopy(stored)

    def query_items(
        self, query: str, parameters: list[dict[str, Any]], enable_cross_partition_query: bool = False
    ):
        wanted = {parameter["name"]: parameter["value"] for parameter in parameters}["@state"]
        matching = [item for item in self._items.values() if item["state"] == wanted]
        matching.sort(key=lambda item: (item["updatedAt"], item["caseId"]), reverse=True)
        return (deepcopy(item) for item in matching)

    def simulate_concurrent_write(self, case_id: str) -> None:
        """Advance the stored ETag as another replica would, without changing
        the document, so any in-flight caller's precondition now fails."""
        self._items[case_id]["_etag"] = self._next_etag()


def _live_cosmos_skip_reason() -> str | None:
    endpoint = os.environ.get("COSMOS_ENDPOINT", "").strip()
    if not endpoint:
        return "COSMOS_ENDPOINT is not set; no live Cosmos account to test against"
    try:
        store = CosmosCaseStore(endpoint)
        store.list_cases_by_state(STATE_DRAFT, limit=1)
    except Exception as exc:  # noqa: BLE001 - any failure means "not testable here"
        return f"COSMOS_ENDPOINT {endpoint!r} unreachable or unauthorized: {exc!r}"
    return None


LIVE_COSMOS_SKIP_REASON = _live_cosmos_skip_reason()


@pytest.fixture(params=["sqlite", "cosmos-fake", "cosmos-live"])
def store(request):
    """Yield one case-store implementation, skipping backends that are unavailable."""
    if request.param == "sqlite":
        instance = SqliteCaseStore(":memory:")
    elif request.param == "cosmos-fake":
        instance = CosmosCaseStore(container=FakeCosmosContainer())
    else:
        if LIVE_COSMOS_SKIP_REASON is not None:
            pytest.skip(LIVE_COSMOS_SKIP_REASON)
        instance = CosmosCaseStore(os.environ["COSMOS_ENDPOINT"].strip())
    yield instance
    instance.close()


@pytest.fixture()
def case_id() -> str:
    """A per-test case id, so a shared live container never cross-contaminates."""
    return f"CASE-SYN-T{uuid.uuid4().hex[:12].upper()}"


def _submitted(store, case_id: str, calculation=READY_CALCULATION) -> str:
    store.create_draft(case_id, PREPARER)
    store.submit_for_review_with_calculation(case_id, PREPARER, calculation=calculation)
    return case_id


def _commands(store, case_id: str) -> list[str]:
    return [event.command for event in store.get_audit_trail(case_id)]


def test_draft_to_pending_review_to_approved_happy_path(store, case_id):
    _submitted(store, case_id)

    record = store.approve(case_id, REVIEWER)

    assert record.state == STATE_APPROVED
    assert record.reviewer_id == REVIEWER
    assert record.approved_at is not None

    audit = store.get_audit_trail(case_id)
    assert [event.command for event in audit] == ["CREATE_DRAFT", "SUBMIT", "APPROVE"]
    assert [event.sequence for event in audit] == [1, 2, 3]
    assert audit[0].from_state is None and audit[0].to_state == STATE_DRAFT
    assert audit[1].from_state == STATE_DRAFT and audit[1].to_state == STATE_PENDING_REVIEW
    assert audit[2].from_state == STATE_PENDING_REVIEW and audit[2].to_state == STATE_APPROVED
    assert audit[2].actor_id == REVIEWER


def test_draft_to_pending_review_to_rejected(store, case_id):
    _submitted(store, case_id)

    record = store.reject(case_id, REVIEWER)

    assert record.state == STATE_REJECTED
    assert record.reviewer_id == REVIEWER
    assert record.approved_at is None
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT", "REJECT"]


def test_submitting_persists_the_calculation_onto_the_case(store, case_id):
    _submitted(store, case_id)

    record = store.get_case(case_id)

    assert record.calculation_status == "READY"
    assert record.amount_cents == 100000
    assert record.currency == "CAD"
    assert record.period == "TRAINING_YEAR"
    assert record.rule_ids == ("RULE-SYN-BASE", "RULE-SYN-PLAN", "RULE-SYN-REVIEW")
    assert record.issues == ()
    assert record.rulebook_version == "training-1"


def test_a_case_with_no_amount_still_reaches_pending_review(store, case_id):
    """CASE-SYN-003 style: an UNSUPPORTED calculation is submitted for review
    with no amount at all, and the queue must surface it rather than assume a
    number exists."""
    _submitted(store, case_id, calculation=UNSUPPORTED_CALCULATION)

    record = store.get_case(case_id)

    assert record.state == STATE_PENDING_REVIEW
    assert record.amount_cents is None
    assert record.calculation_status == "UNSUPPORTED"
    assert record.issues == ("UNSUPPORTED_INPUT",)

    queued = [item for item in store.list_cases_by_state(STATE_PENDING_REVIEW) if item.case_id == case_id]
    assert len(queued) == 1
    assert queued[0].amount_cents is None


def test_plain_submit_records_no_calculation(store, case_id):
    store.create_draft(case_id, PREPARER)

    record = store.submit_for_review(case_id, PREPARER)

    assert record.state == STATE_PENDING_REVIEW
    assert record.amount_cents is None
    assert record.calculation_status is None
    assert record.rule_ids == ()


def test_self_approval_is_rejected(store, case_id):
    _submitted(store, case_id)

    with pytest.raises(SelfApprovalError):
        store.approve(case_id, PREPARER)
    with pytest.raises(SelfApprovalError):
        store.reject(case_id, PREPARER)

    assert store.get_case(case_id).state == STATE_PENDING_REVIEW
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT"]


def test_self_approval_is_checked_before_the_state_guard(store, case_id):
    """Check ordering is load-bearing: a preparer acting on a case that is no
    longer in PENDING_REVIEW must still be refused as self-approval, not given
    the generic transition error, so the reviewer app can map it to 403."""
    _submitted(store, case_id)
    store.approve(case_id, REVIEWER)
    store.revise(case_id, PREPARER)

    with pytest.raises(SelfApprovalError):
        store.approve(case_id, PREPARER)


def test_idempotent_replay_appends_no_additional_audit_event(store, case_id):
    _submitted(store, case_id)

    first = store.approve(case_id, REVIEWER)
    second = store.approve(case_id, REVIEWER)
    third = store.approve(case_id, REVIEWER)

    assert first == second == third
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT", "APPROVE"]


def test_idempotent_reject_replay_appends_no_additional_audit_event(store, case_id):
    _submitted(store, case_id)

    first = store.reject(case_id, REVIEWER)
    second = store.reject(case_id, REVIEWER)

    assert first == second
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT", "REJECT"]


def test_a_second_reviewer_cannot_override_an_existing_decision(store, case_id):
    _submitted(store, case_id)
    store.approve(case_id, REVIEWER)

    with pytest.raises(InvalidTransitionError):
        store.approve(case_id, OTHER_REVIEWER)
    with pytest.raises(InvalidTransitionError):
        store.reject(case_id, OTHER_REVIEWER)

    record = store.get_case(case_id)
    assert record.state == STATE_APPROVED
    assert record.reviewer_id == REVIEWER


def test_revising_resets_to_draft_and_invalidates_the_prior_review(store, case_id):
    _submitted(store, case_id)
    store.approve(case_id, REVIEWER)

    record = store.revise(case_id, OTHER_REVIEWER)

    assert record.state == STATE_DRAFT
    assert record.revision == 2
    assert record.reviewer_id is None
    assert record.approved_at is None
    assert record.preparer_id == OTHER_REVIEWER

    audit = store.get_audit_trail(case_id)
    assert audit[-1].command == "REVISE"
    assert audit[-1].from_state == STATE_APPROVED
    assert audit[-1].to_state == STATE_DRAFT
    assert audit[-1].revision == 2


def test_a_decision_reason_code_is_persisted_on_the_audit_event(store, case_id):
    _submitted(store, case_id)

    store.reject(case_id, REVIEWER, reason_code="MISSING_PLAN")

    decision = store.get_audit_trail(case_id)[-1]
    assert decision.command == "REJECT"
    assert decision.reason_code == "MISSING_PLAN"


def test_a_revise_reason_code_is_persisted_on_the_audit_event(store, case_id):
    _submitted(store, case_id)

    store.revise(case_id, OTHER_REVIEWER, reason_code="NEEDS_DETAIL")

    decision = store.get_audit_trail(case_id)[-1]
    assert decision.command == "REVISE"
    assert decision.reason_code == "NEEDS_DETAIL"


def test_omitting_the_reason_code_still_works(store, case_id):
    _submitted(store, case_id)

    store.approve(case_id, REVIEWER)

    assert [event.reason_code for event in store.get_audit_trail(case_id)] == [None, None, None]


def test_a_reason_code_does_not_leak_onto_a_later_event(store, case_id):
    """The code belongs to one decision. A subsequent command that carries no
    reason must record none, or the trail attributes a rejection reason to an
    unrelated event."""
    _submitted(store, case_id)
    store.revise(case_id, OTHER_REVIEWER, reason_code="NEEDS_DETAIL")

    store.submit_for_review(case_id, OTHER_REVIEWER)

    trail = store.get_audit_trail(case_id)
    assert (trail[-2].command, trail[-2].reason_code) == ("REVISE", "NEEDS_DETAIL")
    assert (trail[-1].command, trail[-1].reason_code) == ("SUBMIT", None)


@pytest.mark.parametrize(
    "invalid", ["lower_case", "HAS SPACE", "BAD-CODE", "A" * 65, "", 42, "DROP TABLE cases"]
)
def test_an_invalid_reason_code_is_refused_before_any_write(store, case_id, invalid):
    """Arbitrary caller text must not reach storage, and the refusal must
    happen before the state changes."""
    _submitted(store, case_id)

    with pytest.raises(ValueError):
        store.reject(case_id, REVIEWER, reason_code=invalid)

    assert store.get_case(case_id).state == STATE_PENDING_REVIEW
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT"]


def test_replaying_a_decision_does_not_append_a_second_reason_code(store, case_id):
    _submitted(store, case_id)
    store.reject(case_id, REVIEWER, reason_code="MISSING_PLAN")

    store.reject(case_id, REVIEWER, reason_code="SOMETHING_ELSE")

    trail = store.get_audit_trail(case_id)
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT", "REJECT"]
    assert trail[-1].reason_code == "MISSING_PLAN"


def test_a_stale_decision_after_a_revision_is_rejected(store, case_id):
    _submitted(store, case_id)
    stale_view = store.get_case(case_id)
    assert stale_view.state == STATE_PENDING_REVIEW and stale_view.revision == 1

    store.revise(case_id, PREPARER)

    with pytest.raises(InvalidTransitionError):
        store.approve(case_id, REVIEWER)

    current = store.get_case(case_id)
    assert current.state == STATE_DRAFT
    assert current.revision == 2


def test_approving_a_case_never_submitted_for_review_is_rejected(store, case_id):
    store.create_draft(case_id, PREPARER)

    with pytest.raises(InvalidTransitionError):
        store.approve(case_id, REVIEWER)

    assert store.get_case(case_id).state == STATE_DRAFT
    assert _commands(store, case_id) == ["CREATE_DRAFT"]


def test_open_training_preview_only_permitted_when_approved(store, case_id):
    _submitted(store, case_id)

    with pytest.raises(InvalidTransitionError):
        store.open_training_preview(case_id, PREPARER)

    store.approve(case_id, REVIEWER)
    record = store.open_training_preview(case_id, PREPARER)

    assert record.state == STATE_APPROVED
    assert _commands(store, case_id)[-1] == "OPEN_PREVIEW"


def test_duplicate_create_draft_raises(store, case_id):
    store.create_draft(case_id, PREPARER)

    with pytest.raises(CaseAlreadyExistsError):
        store.create_draft(case_id, PREPARER)


def test_unknown_case_raises_case_not_found(store):
    with pytest.raises(CaseNotFoundError):
        store.get_case("CASE-SYN-DOES-NOT-EXIST")


def test_audit_trail_of_an_unknown_case_is_empty(store):
    assert store.get_audit_trail("CASE-SYN-DOES-NOT-EXIST") == []


def test_list_cases_by_state_returns_only_that_state(store, case_id):
    pending = _submitted(store, f"{case_id}-A")
    decided = _submitted(store, f"{case_id}-B")
    store.approve(decided, REVIEWER)
    drafted = f"{case_id}-C"
    store.create_draft(drafted, PREPARER)

    queue_ids = {item.case_id for item in store.list_cases_by_state(STATE_PENDING_REVIEW)}
    approved_ids = {item.case_id for item in store.list_cases_by_state(STATE_APPROVED)}
    draft_ids = {item.case_id for item in store.list_cases_by_state(STATE_DRAFT)}

    assert pending in queue_ids
    assert decided not in queue_ids and decided in approved_ids
    assert drafted not in queue_ids and drafted in draft_ids


def test_list_cases_by_state_is_ordered_most_recently_updated_first(store, case_id):
    first = _submitted(store, f"{case_id}-1")
    time.sleep(0.01)  # distinct updated_at, so the assertion never rides on a tiebreak
    second = _submitted(store, f"{case_id}-2")

    ordered = [
        item.case_id
        for item in store.list_cases_by_state(STATE_PENDING_REVIEW)
        if item.case_id in {first, second}
    ]

    assert ordered[0] == second
    assert ordered[1] == first


def test_list_cases_by_state_honours_the_limit(store, case_id):
    for index in range(3):
        _submitted(store, f"{case_id}-{index}")

    assert len(store.list_cases_by_state(STATE_PENDING_REVIEW, limit=2)) == 2


def test_list_cases_by_state_rejects_an_unknown_state(store):
    for invalid in ("PENDING", "INCOMPLETE", "UNSUPPORTED", "", "pending_review"):
        with pytest.raises(ValueError):
            store.list_cases_by_state(invalid)


def test_list_cases_by_state_rejects_a_non_positive_limit(store):
    for invalid in (0, -1, "10", None):
        with pytest.raises(ValueError):
            store.list_cases_by_state(STATE_PENDING_REVIEW, limit=invalid)


def test_sqlite_concurrent_approvals_yield_exactly_one_winner():
    """SQLite serializes through one connection under a threading.Lock, so this
    exercises the lock plus the `UPDATE ... WHERE state=/revision=` guard that
    would still apply without it. The outcome that matters: one transition, one
    APPROVE audit event, and an explicit error for the loser."""
    store = SqliteCaseStore(":memory:")
    try:
        case_id = _submitted(store, "CASE-SYN-CONCURRENT-001")
        results: dict[str, object] = {}
        barrier = threading.Barrier(2)

        def _approve(reviewer_id: str, key: str) -> None:
            barrier.wait()
            try:
                results[key] = store.approve(case_id, reviewer_id)
            except InvalidTransitionError as exc:
                results[key] = exc

        threads = [
            threading.Thread(target=_approve, args=(REVIEWER, "a")),
            threading.Thread(target=_approve, args=(OTHER_REVIEWER, "b")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        outcomes = [results["a"], results["b"]]
        winners = [item for item in outcomes if not isinstance(item, Exception)]
        losers = [item for item in outcomes if isinstance(item, InvalidTransitionError)]

        assert len(winners) == 1
        assert len(losers) == 1
        assert store.get_case(case_id).reviewer_id == winners[0].reviewer_id
        assert _commands(store, case_id).count("APPROVE") == 1
    finally:
        store.close()


def test_cosmos_decide_fails_when_the_document_changed_since_the_read():
    """Proves the ETag precondition is actually sent on the decision path. The
    container advances the stored ETag between this caller's read and its
    replace, exactly as a second replica deciding first would."""
    container = FakeCosmosContainer()
    store = CosmosCaseStore(container=container)
    case_id = _submitted(store, "CASE-SYN-ETAG-001")
    original_replace = container.replace_item

    def _replace_after_a_concurrent_write(*args: Any, **kwargs: Any):
        container.simulate_concurrent_write(case_id)
        container.replace_item = original_replace
        return original_replace(*args, **kwargs)

    container.replace_item = _replace_after_a_concurrent_write

    with pytest.raises(InvalidTransitionError):
        store.approve(case_id, REVIEWER)

    assert store.get_case(case_id).state == STATE_PENDING_REVIEW
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT"]


def test_cosmos_revise_carries_an_etag_precondition():
    """`revise` has no optimistic guard in the SQLite implementation, which
    relies on a process-local lock that protects nothing across replicas. The
    Cosmos store adds the precondition; this asserts it."""
    container = FakeCosmosContainer()
    store = CosmosCaseStore(container=container)
    case_id = _submitted(store, "CASE-SYN-ETAG-002")
    original_replace = container.replace_item

    def _replace_after_a_concurrent_write(*args: Any, **kwargs: Any):
        container.simulate_concurrent_write(case_id)
        container.replace_item = original_replace
        return original_replace(*args, **kwargs)

    container.replace_item = _replace_after_a_concurrent_write

    with pytest.raises(InvalidTransitionError):
        store.revise(case_id, OTHER_REVIEWER)

    record = store.get_case(case_id)
    assert record.revision == 1
    assert record.state == STATE_PENDING_REVIEW


def test_cosmos_idempotent_replay_performs_no_write():
    """The replay branch must return before any write. An upsert-shaped port
    would issue a replace and append a duplicate audit event every time."""
    container = FakeCosmosContainer()
    store = CosmosCaseStore(container=container)
    case_id = _submitted(store, "CASE-SYN-REPLAY-001")
    store.approve(case_id, REVIEWER)
    writes_after_first_decision = container.replace_calls

    store.approve(case_id, REVIEWER)
    store.approve(case_id, REVIEWER)

    assert container.replace_calls == writes_after_first_decision
    assert _commands(store, case_id) == ["CREATE_DRAFT", "SUBMIT", "APPROVE"]


def test_cosmos_store_never_accepts_an_account_key():
    """Managed identity only: there is no key parameter to pass by accident."""
    import inspect

    parameters = set(inspect.signature(CosmosCaseStore.__init__).parameters)

    assert not {name for name in parameters if "key" in name.lower()}
    assert "credential" in parameters


def test_cosmos_client_is_not_built_until_the_store_is_used():
    """`CosmosClient.__init__` reads account metadata over the network, so an
    eager build would turn a Cosmos outage into a hosted-agent startup failure."""
    class ExplodingCredential:
        def get_token(self, *scopes, **kwargs):
            raise AssertionError("credential used during construction")

    store = CosmosCaseStore("https://unreachable.invalid:443/", credential=ExplodingCredential())

    assert store._client is None
    assert store._container_client is None

    store.close()
