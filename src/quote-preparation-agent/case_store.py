"""Backend-agnostic case-store contract shared by the agent and the reviewer app.

Why this module exists rather than growing `approval_repository.py`:

`toolbox.py` (and both existing agent test modules) put `apps/workshop` ahead
of `src/quote-preparation-agent` on `sys.path`, so `import approval_repository`
resolves to the frozen workshop copy in a local checkout and to the vendored
agent copy inside the hosted container. Adding the reviewer-facing columns to
that module would therefore take effect in one environment and silently not in
the other, and `apps/workshop` is deliberately frozen workshop material. The
concrete stores below instead layer the new surface on top of whichever copy
resolves, so both environments behave identically.

The reviewer app imports `CaseStore` implementations directly. It must never
route decisions through `toolbox.py`, which deliberately refuses to wrap
`approve`, `reject`, and `revise`.

Exception types are re-exported unchanged from `approval_repository`. In
particular `SelfApprovalError` remains a sibling of `InvalidTransitionError`
rather than a subclass, because the HTTP layer maps them to different status
codes (403 versus 409) and a subclass relationship would let self-approval be
swallowed by a single `InvalidTransitionError` handler.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from approval_repository import (  # noqa: F401
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
    ApprovalRepositoryError,
    AuditEvent,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidTransitionError,
    SelfApprovalError,
)

VALID_STATES: frozenset[str] = frozenset(
    {STATE_DRAFT, STATE_PENDING_REVIEW, STATE_APPROVED, STATE_REJECTED}
)

COSMOS_DATABASE_ID = "quote-preparation"
COSMOS_CONTAINER_ID = "cases"
COSMOS_PARTITION_KEY_PATH = "/caseId"

REASON_CODE_MAX_LENGTH = 64
_REASON_CODE_PATTERN = re.compile(r"^[A-Z0-9_]+$")


@dataclass(frozen=True)
class AuditRecord:
    """One append-only audit entry, extending `AuditEvent` with the reason code.

    The first seven fields match `approval_repository.AuditEvent` in name and
    order, so anything already reading an audit trail keeps working. Decision
    reason codes are persisted here rather than on the case itself because the
    trail is append-only: a later revision must not overwrite why an earlier
    revision was rejected.
    """

    sequence: int
    command: str
    from_state: str | None
    to_state: str
    revision: int
    actor_id: str
    at: str
    reason_code: str | None = None


@dataclass(frozen=True)
class CalculationSnapshot:
    """The calculator result carried onto the case at submission time.

    `amount_cents` is nullable on purpose. `composition_node` submits a case
    for review regardless of calculation status, so an INCOMPLETE or
    UNSUPPORTED case legitimately reaches PENDING_REVIEW with no amount and
    the reviewer surface must render that state rather than assume a number.
    """

    status: str
    amount_cents: int | None = None
    currency: str | None = None
    period: str | None = None
    rule_ids: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    rulebook_version: str | None = None

    @classmethod
    def from_calculation(
        cls, calculation: dict[str, Any], *, rulebook_version: str | None = None
    ) -> "CalculationSnapshot":
        """Adapt the calculator's camelCase result dict to a stored snapshot."""
        return cls(
            status=calculation["status"],
            amount_cents=calculation.get("amountCents"),
            currency=calculation.get("currency"),
            period=calculation.get("period"),
            rule_ids=tuple(calculation.get("ruleIds") or ()),
            issues=tuple(calculation.get("issues") or ()),
            rulebook_version=rulebook_version,
        )


@dataclass(frozen=True)
class CaseRecord:
    """A snapshot of one case, including its last submitted calculation.

    The first eight fields match `approval_repository.CaseRecord` in both name
    and order so existing positional construction keeps working; every field
    added for the reviewer surface carries a default.
    """

    case_id: str
    state: str
    revision: int
    preparer_id: str
    reviewer_id: str | None
    created_at: str
    updated_at: str
    approved_at: str | None
    amount_cents: int | None = None
    currency: str | None = None
    period: str | None = None
    calculation_status: str | None = None
    rule_ids: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    rulebook_version: str | None = None


@runtime_checkable
class CaseStore(Protocol):
    """The full public surface both the agent and the reviewer app rely on.

    Bare `ApprovalRepository` satisfies every method here except
    `list_cases_by_state`, `submit_for_review_with_calculation`, and
    `delete_all_cases`; those three are the reviewer-facing additions, and
    `build_case_store` never hands back a store that lacks them.
    """

    def create_draft(self, case_id: str, preparer_id: str) -> CaseRecord: ...

    def submit_for_review(self, case_id: str, actor_id: str) -> CaseRecord: ...

    def submit_for_review_with_calculation(
        self, case_id: str, actor_id: str, *, calculation: CalculationSnapshot
    ) -> CaseRecord: ...

    def approve(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord: ...

    def reject(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord: ...

    def revise(
        self, case_id: str, actor_id: str, *, reason_code: str | None = None
    ) -> CaseRecord: ...

    def open_training_preview(self, case_id: str, actor_id: str) -> CaseRecord: ...

    def get_case(self, case_id: str) -> CaseRecord: ...

    def get_audit_trail(self, case_id: str) -> list[AuditRecord]: ...

    def list_cases_by_state(self, state: str, limit: int = 100) -> tuple[CaseRecord, ...]: ...

    def delete_all_cases(self) -> int: ...

    def close(self) -> None: ...


def validate_state(state: str) -> str:
    """Reject any state outside the four persisted `CaseRecord.state` values.

    `INCOMPLETE` and `UNSUPPORTED` are calculator statuses that never reach
    `cases.state`, so they are rejected here too.
    """
    if state not in VALID_STATES:
        raise ValueError(
            f"Unknown case state {state!r}; expected one of {sorted(VALID_STATES)}"
        )
    return state


def validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError(f"limit must be a positive integer, got {limit!r}")
    return limit


def validate_reason_code(reason_code: str | None) -> str | None:
    """Bound and constrain a decision reason code before it reaches storage.

    The reviewer API applies the same rule at its Pydantic boundary, but the
    stores are also reachable from the agent and from any future caller, so the
    constraint lives with the data rather than with one transport.
    """
    if reason_code is None:
        return None
    if not isinstance(reason_code, str):
        raise ValueError(f"reason_code must be a string, got {type(reason_code).__name__}")
    if len(reason_code) > REASON_CODE_MAX_LENGTH:
        raise ValueError(
            f"reason_code must be at most {REASON_CODE_MAX_LENGTH} characters"
        )
    if not _REASON_CODE_PATTERN.match(reason_code):
        raise ValueError(
            "reason_code must be upper-case letters, digits, or underscores, "
            f"got {reason_code!r}"
        )
    return reason_code


def build_case_store(
    *, db_path: str | None = None, endpoint: str | None = None
) -> CaseStore:
    """Return the Cosmos store when `COSMOS_ENDPOINT` is set, else SQLite.

    Imports are deferred so a SQLite-only run never imports `azure-cosmos`
    and a Cosmos run never pays for the SQLite module.
    """
    endpoint = endpoint if endpoint is not None else os.environ.get("COSMOS_ENDPOINT", "")
    if endpoint.strip():
        from cosmos_case_store import CosmosCaseStore

        return CosmosCaseStore(endpoint.strip())

    from sqlite_case_store import SqliteCaseStore

    return SqliteCaseStore(db_path or os.environ.get("CASE_STORE_DB_PATH", ":memory:"))


__all__ = [
    "COMMAND_APPROVE",
    "COMMAND_CREATE_DRAFT",
    "COMMAND_OPEN_PREVIEW",
    "COMMAND_REJECT",
    "COMMAND_REVISE",
    "COMMAND_SUBMIT",
    "COSMOS_CONTAINER_ID",
    "COSMOS_DATABASE_ID",
    "COSMOS_PARTITION_KEY_PATH",
    "REASON_CODE_MAX_LENGTH",
    "STATE_APPROVED",
    "STATE_DRAFT",
    "STATE_PENDING_REVIEW",
    "STATE_REJECTED",
    "VALID_STATES",
    "ApprovalRepositoryError",
    "AuditEvent",
    "AuditRecord",
    "CalculationSnapshot",
    "CaseAlreadyExistsError",
    "CaseNotFoundError",
    "CaseRecord",
    "CaseStore",
    "InvalidTransitionError",
    "SelfApprovalError",
    "build_case_store",
    "validate_limit",
    "validate_reason_code",
    "validate_state",
]
