"""Cosmos DB case store, preserving the SQLite state machine across replicas.

Storage layout: one document per case in database `quote-preparation`,
container `cases`, partitioned on `/caseId`, with the append-only audit trail
embedded as an `auditEvents` array on the case document. Embedding is chosen
over a second container so that a state change and its audit event are written
by a single `replace_item` call and are therefore atomic by construction — a
transactional batch across two documents would work only because they share the
partition key, and would still leave the per-case audit sequence to be computed
from a separate read.

Authentication is Microsoft Entra only, through `DefaultAzureCredential`. The
account is provisioned with local auth disabled and this repository has no Key
Vault convention, so no account-key parameter is accepted anywhere.

Four semantics from the SQLite implementation are preserved deliberately,
because each one fails silently rather than loudly when a port gets it wrong:

1. Compare-and-swap. Every state mutation is a `replace_item` carrying the
   ETag read moments earlier with `MatchConditions.IfNotModified`. A
   precondition failure surfaces as `InvalidTransitionError`, matching the
   SQLite `UPDATE ... WHERE state = ? AND revision = ?` plus `changes()` guard.
   A read-modify-write without the precondition passes every single-threaded
   test and still lets a second reviewer overwrite the first decision.
2. Atomic case plus audit write, via the embedded array described above.
3. Check order on the decision path: self-approval, then idempotent replay,
   then the state guard, then the compare-and-swap. The replay branch returns
   before any write, so replaying a decision appends no duplicate audit event.
   An upsert-shaped port grows the audit trail on every replay.
4. `revise` carries an ETag precondition here even though the SQLite version
   has none. SQLite relies on a process-local `threading.Lock`, which gives
   zero protection across Container App replicas. This is a deliberate
   strengthening of the contract, not a faithful port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import islice
from typing import Any, Iterator

from azure.core import MatchConditions
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosHttpResponseError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from approval_repository import (
    COMMAND_APPROVE,
    COMMAND_CREATE_DRAFT,
    COMMAND_OPEN_PREVIEW,
    COMMAND_REJECT,
    COMMAND_REVISE,
    COMMAND_SUBMIT,
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidTransitionError,
    SelfApprovalError,
)
from case_store import (
    COSMOS_CONTAINER_ID,
    COSMOS_DATABASE_ID,
    AuditRecord,
    CalculationSnapshot,
    CaseRecord,
    validate_limit,
    validate_reason_code,
    validate_state,
)

_PRECONDITION_FAILED = 412


class CosmosCaseStore:
    """Cosmos-backed `CaseStore` with Entra authentication and ETag concurrency.

    `container` is a test seam: pass an object implementing the four container
    operations used here (`create_item`, `read_item`, `replace_item`,
    `query_items`) to exercise this class without a live account. When it is
    omitted a `CosmosClient` is built from `endpoint` and `credential`.

    Client construction is deferred to the first store operation. `CosmosClient.__init__`
    performs a network call to read database account metadata, so building it eagerly
    would make a Cosmos outage fail `build_graph()` and therefore hosted-agent startup,
    rather than failing the one request that actually needs the store.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        *,
        credential: Any | None = None,
        database_id: str = COSMOS_DATABASE_ID,
        container_id: str = COSMOS_CONTAINER_ID,
        container: Any | None = None,
    ) -> None:
        if container is None and not endpoint:
            raise ValueError("endpoint is required when no container is injected")
        self._client: CosmosClient | None = None
        self._container_client: Any | None = container
        self._endpoint = endpoint
        self._credential = credential
        self._database_id = database_id
        self._container_id = container_id

    @property
    def _container(self) -> Any:
        """Return the container client, connecting on first use."""
        if self._container_client is None:
            credential = self._credential
            if credential is None:
                from azure.identity import DefaultAzureCredential

                credential = DefaultAzureCredential()
                self._credential = credential
            self._client = CosmosClient(self._endpoint, credential=credential)
            self._container_client = self._client.get_database_client(
                self._database_id
            ).get_container_client(self._container_id)
        return self._container_client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._container_client = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_draft(self, case_id: str, preparer_id: str) -> CaseRecord:
        """Create a new case document in state DRAFT at revision 1."""
        now = self._now()
        document = {
            "id": case_id,
            "caseId": case_id,
            "state": STATE_DRAFT,
            "revision": 1,
            "preparerId": preparer_id,
            "reviewerId": None,
            "createdAt": now,
            "updatedAt": now,
            "approvedAt": None,
            "amountCents": None,
            "currency": None,
            "period": None,
            "calculationStatus": None,
            "ruleIds": [],
            "issues": [],
            "rulebookVersion": None,
            "auditEvents": [
                _audit_entry(1, COMMAND_CREATE_DRAFT, None, STATE_DRAFT, 1, preparer_id, now)
            ],
        }
        try:
            created = self._container.create_item(body=document)
        except CosmosResourceExistsError as exc:
            raise CaseAlreadyExistsError(f"Case {case_id!r} already exists") from exc
        return _record_from_document(created)

    def submit_for_review(self, case_id: str, actor_id: str) -> CaseRecord:
        """Transition DRAFT -> PENDING_REVIEW without recording a calculation."""
        return self._submit(case_id, actor_id, calculation=None)

    def submit_for_review_with_calculation(
        self, case_id: str, actor_id: str, *, calculation: CalculationSnapshot
    ) -> CaseRecord:
        """Transition DRAFT -> PENDING_REVIEW and persist `calculation` in the same write."""
        return self._submit(case_id, actor_id, calculation=calculation)

    def _submit(
        self, case_id: str, actor_id: str, *, calculation: CalculationSnapshot | None
    ) -> CaseRecord:
        document, etag = self._read(case_id)
        if document["state"] != STATE_DRAFT:
            raise InvalidTransitionError(
                f"Cannot submit case {case_id!r} for review from state {document['state']!r}"
            )
        now = self._now()
        document["state"] = STATE_PENDING_REVIEW
        document["updatedAt"] = now
        if calculation is not None:
            document["amountCents"] = calculation.amount_cents
            document["currency"] = calculation.currency
            document["period"] = calculation.period
            document["calculationStatus"] = calculation.status
            document["ruleIds"] = list(calculation.rule_ids)
            document["issues"] = list(calculation.issues)
            document["rulebookVersion"] = calculation.rulebook_version
        _append_audit(
            document,
            COMMAND_SUBMIT,
            STATE_DRAFT,
            STATE_PENDING_REVIEW,
            document["revision"],
            actor_id,
            now,
        )
        return self._replace(document, etag, conflict="was already advanced by another writer")

    def approve(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Transition PENDING_REVIEW -> APPROVED. See the module docstring for
        the self-approval and idempotency rules enforced here."""
        return self._decide(case_id, reviewer_id, approve=True, reason_code=reason_code)

    def reject(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Transition PENDING_REVIEW -> REJECTED. See the module docstring for
        the self-approval and idempotency rules enforced here."""
        return self._decide(case_id, reviewer_id, approve=False, reason_code=reason_code)

    def _decide(
        self,
        case_id: str,
        reviewer_id: str,
        *,
        approve: bool,
        reason_code: str | None = None,
    ) -> CaseRecord:
        command = COMMAND_APPROVE if approve else COMMAND_REJECT
        target_state = STATE_APPROVED if approve else STATE_REJECTED
        reason_code = validate_reason_code(reason_code)

        document, etag = self._read(case_id)

        if reviewer_id == document["preparerId"]:
            raise SelfApprovalError(
                f"Reviewer {reviewer_id!r} cannot {command.lower()} case {case_id!r}: "
                "reviewer is also the preparer of the current revision"
            )

        if document["state"] == target_state and document["reviewerId"] == reviewer_id:
            # Idempotent replay of an already-applied decision: no-op, no write.
            return _record_from_document(document)

        if document["state"] != STATE_PENDING_REVIEW:
            raise InvalidTransitionError(
                f"Cannot {command.lower()} case {case_id!r} in state {document['state']!r}"
            )

        now = self._now()
        revision = document["revision"]
        document["state"] = target_state
        document["reviewerId"] = reviewer_id
        document["updatedAt"] = now
        document["approvedAt"] = now if approve else None
        _append_audit(
            document,
            command,
            STATE_PENDING_REVIEW,
            target_state,
            revision,
            reviewer_id,
            now,
            reason_code=reason_code,
        )
        return self._replace(document, etag, conflict="was already decided by another reviewer")

    def revise(
        self, case_id: str, actor_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Create a new revision from any state. Resets state to DRAFT, reassigns
        `preparerId` to `actor_id`, and clears reviewerId/approvedAt."""
        reason_code = validate_reason_code(reason_code)
        document, etag = self._read(case_id)
        from_state = document["state"]
        new_revision = document["revision"] + 1
        now = self._now()
        document["state"] = STATE_DRAFT
        document["revision"] = new_revision
        document["preparerId"] = actor_id
        document["reviewerId"] = None
        document["updatedAt"] = now
        document["approvedAt"] = None
        _append_audit(
            document,
            COMMAND_REVISE,
            from_state,
            STATE_DRAFT,
            new_revision,
            actor_id,
            now,
            reason_code=reason_code,
        )
        return self._replace(document, etag, conflict="was already revised by another writer")

    def open_training_preview(self, case_id: str, actor_id: str) -> CaseRecord:
        """Record a training-preview audit event. Only permitted while
        state == APPROVED; does not itself change state or revision."""
        document, etag = self._read(case_id)
        if document["state"] != STATE_APPROVED:
            raise InvalidTransitionError(
                f"Cannot open training preview for case {case_id!r} in state {document['state']!r}"
            )
        now = self._now()
        _append_audit(
            document,
            COMMAND_OPEN_PREVIEW,
            STATE_APPROVED,
            STATE_APPROVED,
            document["revision"],
            actor_id,
            now,
        )
        return self._replace(document, etag, conflict="was changed by another writer")

    def get_case(self, case_id: str) -> CaseRecord:
        document, _ = self._read(case_id)
        return _record_from_document(document)

    def get_audit_trail(self, case_id: str) -> list[AuditRecord]:
        """Return the case's audit events, or an empty list for an unknown case."""
        try:
            document, _ = self._read(case_id)
        except CaseNotFoundError:
            return []
        return _audit_events_from_document(document)

    def list_cases_by_state(self, state: str, limit: int = 100) -> tuple[CaseRecord, ...]:
        """Return cases in `state`, most recently updated first."""
        state = validate_state(state)
        limit = validate_limit(limit)
        # The container is partitioned on /caseId, so this filter-by-state query
        # always spans partitions; without this flag the SDK raises BadRequest
        # instead of fanning the query out.
        results: Iterator[dict[str, Any]] = self._container.query_items(
            query="SELECT * FROM c WHERE c.state = @state ORDER BY c.updatedAt DESC",
            parameters=[{"name": "@state", "value": state}],
            enable_cross_partition_query=True,
        )
        return tuple(_record_from_document(item) for item in islice(results, limit))

    def delete_all_cases(self) -> int:
        """Delete every case document. Pilot/training queue resets only.

        Not part of the reviewer approval workflow: the only caller is the
        queue-clearing admin action in `apps/reviewer-app`. `id` and the
        `/caseId` partition key are the same value on every document (see
        `create_draft`), so each id doubles as its own partition key here.
        """
        ids = [
            item["id"]
            for item in self._container.query_items(
                query="SELECT c.id FROM c",
                enable_cross_partition_query=True,
            )
        ]
        for case_id in ids:
            self._container.delete_item(item=case_id, partition_key=case_id)
        return len(ids)

    def _read(self, case_id: str) -> tuple[dict[str, Any], str]:
        try:
            document = self._container.read_item(item=case_id, partition_key=case_id)
        except CosmosResourceNotFoundError as exc:
            raise CaseNotFoundError(f"Case {case_id!r} not found") from exc
        return document, document["_etag"]

    def _replace(self, document: dict[str, Any], etag: str, *, conflict: str) -> CaseRecord:
        """Replace the case document, failing loudly if it changed since the read."""
        try:
            replaced = self._container.replace_item(
                item=document["id"],
                body=document,
                etag=etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError as exc:
            raise InvalidTransitionError(f"Case {document['id']!r} {conflict}") from exc
        except CosmosHttpResponseError as exc:
            if exc.status_code == _PRECONDITION_FAILED:
                raise InvalidTransitionError(f"Case {document['id']!r} {conflict}") from exc
            raise
        return _record_from_document(replaced)


def _audit_entry(
    sequence: int,
    command: str,
    from_state: str | None,
    to_state: str,
    revision: int,
    actor_id: str,
    at: str,
    reason_code: str | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "command": command,
        "fromState": from_state,
        "toState": to_state,
        "revision": revision,
        "actorId": actor_id,
        "at": at,
        "reasonCode": reason_code,
    }


def _append_audit(
    document: dict[str, Any],
    command: str,
    from_state: str | None,
    to_state: str,
    revision: int,
    actor_id: str,
    at: str,
    *,
    reason_code: str | None = None,
) -> None:
    """Append the next audit entry in place. Safe because the enclosing
    replace_item carries the ETag the array was read under."""
    events = document.setdefault("auditEvents", [])
    events.append(
        _audit_entry(
            len(events) + 1,
            command,
            from_state,
            to_state,
            revision,
            actor_id,
            at,
            reason_code,
        )
    )


def _audit_events_from_document(document: dict[str, Any]) -> list[AuditRecord]:
    return [
        AuditRecord(
            sequence=event["sequence"],
            command=event["command"],
            from_state=event["fromState"],
            to_state=event["toState"],
            revision=event["revision"],
            actor_id=event["actorId"],
            at=event["at"],
            reason_code=event.get("reasonCode"),
        )
        for event in sorted(document.get("auditEvents", []), key=lambda event: event["sequence"])
    ]


def _record_from_document(document: dict[str, Any]) -> CaseRecord:
    return CaseRecord(
        case_id=document["caseId"],
        state=document["state"],
        revision=document["revision"],
        preparer_id=document["preparerId"],
        reviewer_id=document["reviewerId"],
        created_at=document["createdAt"],
        updated_at=document["updatedAt"],
        approved_at=document["approvedAt"],
        amount_cents=document.get("amountCents"),
        currency=document.get("currency"),
        period=document.get("period"),
        calculation_status=document.get("calculationStatus"),
        rule_ids=tuple(document.get("ruleIds") or ()),
        issues=tuple(document.get("issues") or ()),
        rulebook_version=document.get("rulebookVersion"),
    )


__all__ = ["CosmosCaseStore"]
