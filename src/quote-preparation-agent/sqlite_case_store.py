"""SQLite case store: `ApprovalRepository` plus the reviewer-facing surface.

This subclasses the existing `ApprovalRepository` instead of forking it so the
state machine — self-approval ordering, idempotent replay, revision
invalidation, and the compare-and-swap on decide — stays defined in exactly one
place. What this class adds is the data the reviewer app needs and the base
class never persisted:

* the calculator result carried onto the case at submission time, written in
  the same transaction as the state change so a case and its amount become
  visible together;
* the decision reason code, recorded on the audit event the decision appends;
* `list_cases_by_state`, the queue query the base class has no equivalent for;
* a lightweight `ALTER TABLE` migration so an existing database file created by
  the base schema opens without error.

The reason code reaches the audit row through a thread-local set for the
duration of one `approve`, `reject`, or `revise` call rather than through an
extra parameter on `_decide` and `revise`. Adding the parameter would mean
re-implementing both method bodies here, which is precisely the duplication
this class exists to avoid; the thread-local keeps the check ordering,
idempotent-replay early return, and compare-and-swap defined once in the base
class. It is per-thread and scoped by `try/finally`, so two reviewers deciding
concurrently cannot see each other's code, and a replay that returns before
any write records nothing.

`submit_for_review_with_calculation` also adds a `WHERE state = ? AND
revision = ?` guard that the base `submit_for_review` does not carry. That is a
deliberate strengthening, not a port artifact.

Known limitation: the inherited `revise` clears `reviewer_id` and `approved_at`
but leaves the persisted calculation in place, so a revised case keeps the last
submitted amount while it sits in DRAFT. A DRAFT case is never in the reviewer
queue, and the next submission overwrites the fields, so the stale value is
never reachable from the reviewer surface.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager

from approval_repository import (
    COMMAND_SUBMIT,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    ApprovalRepository,
    CaseNotFoundError,
    InvalidTransitionError,
)
from case_store import (
    AuditRecord,
    CalculationSnapshot,
    CaseRecord,
    validate_limit,
    validate_reason_code,
    validate_state,
)

_CALCULATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("amount_cents", "INTEGER"),
    ("currency", "TEXT"),
    ("period", "TEXT"),
    ("calculation_status", "TEXT"),
    ("rule_ids", "TEXT"),
    ("issues", "TEXT"),
    ("rulebook_version", "TEXT"),
)

_AUDIT_COLUMNS: tuple[tuple[str, str], ...] = (("reason_code", "TEXT"),)

_CASE_SELECT_COLUMNS = (
    "case_id, state, revision, preparer_id, reviewer_id, created_at, updated_at, "
    "approved_at, amount_cents, currency, period, calculation_status, rule_ids, "
    "issues, rulebook_version"
)


def _encode_sequence(values: tuple[str, ...]) -> str:
    return json.dumps(list(values))


def _decode_sequence(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(json.loads(raw))


class SqliteCaseStore(ApprovalRepository):
    """SQLite-backed `CaseStore`. `db_path` defaults to a private in-memory database."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._pending_reason = threading.local()
        super().__init__(db_path)

    def _init_schema(self) -> None:
        super()._init_schema()
        with self._lock, self._conn:
            self._add_missing_columns("cases", _CALCULATION_COLUMNS)
            self._add_missing_columns("audit_events", _AUDIT_COLUMNS)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cases_state_updated "
                "ON cases (state, updated_at DESC)"
            )

    def _add_missing_columns(
        self, table: str, columns: tuple[tuple[str, str], ...]
    ) -> None:
        existing = {
            row[1] for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column, sql_type in columns:
            if column not in existing:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")

    @contextmanager
    def _reason(self, reason_code: str | None):
        """Make `reason_code` visible to the audit append this call performs."""
        self._pending_reason.code = validate_reason_code(reason_code)
        try:
            yield
        finally:
            self._pending_reason.code = None

    def approve(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Transition PENDING_REVIEW -> APPROVED, recording `reason_code` on the event."""
        with self._reason(reason_code):
            return super().approve(case_id, reviewer_id)

    def reject(
        self, case_id: str, reviewer_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Transition PENDING_REVIEW -> REJECTED, recording `reason_code` on the event."""
        with self._reason(reason_code):
            return super().reject(case_id, reviewer_id)

    def revise(
        self, case_id: str, actor_id: str, *, reason_code: str | None = None
    ) -> CaseRecord:
        """Create a new revision, recording `reason_code` on the REVISE event."""
        with self._reason(reason_code):
            return super().revise(case_id, actor_id)

    def _append_audit(
        self,
        case_id: str,
        command: str,
        from_state: str | None,
        to_state: str,
        revision: int,
        actor_id: str,
        at: str,
    ) -> None:
        """Insert the next append-only row, carrying this call's reason code.

        The row is written once with every column set rather than inserted by
        the base class and then updated, so the trail is never mutated after
        the fact.
        """
        next_sequence = (
            self._conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM audit_events WHERE case_id = ?",
                (case_id,),
            ).fetchone()[0]
            + 1
        )
        self._conn.execute(
            """
            INSERT INTO audit_events
                (case_id, sequence, command, from_state, to_state, revision, actor_id,
                 at, reason_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                next_sequence,
                command,
                from_state,
                to_state,
                revision,
                actor_id,
                at,
                getattr(self._pending_reason, "code", None),
            ),
        )

    def get_audit_trail(self, case_id: str) -> list[AuditRecord]:
        """Return the append-only trail, including each decision's reason code."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT sequence, command, from_state, to_state, revision, actor_id, at,
                       reason_code
                FROM audit_events
                WHERE case_id = ?
                ORDER BY sequence
                """,
                (case_id,),
            ).fetchall()
        return [AuditRecord(*row) for row in rows]

    def submit_for_review_with_calculation(
        self, case_id: str, actor_id: str, *, calculation: CalculationSnapshot
    ) -> CaseRecord:
        """Transition DRAFT -> PENDING_REVIEW and persist `calculation` atomically."""
        with self._lock:
            record = self._get_locked(case_id)
            if record.state != STATE_DRAFT:
                raise InvalidTransitionError(
                    f"Cannot submit case {case_id!r} for review from state {record.state!r}"
                )
            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE cases
                    SET state = ?, updated_at = ?, amount_cents = ?, currency = ?,
                        period = ?, calculation_status = ?, rule_ids = ?, issues = ?,
                        rulebook_version = ?
                    WHERE case_id = ? AND state = ? AND revision = ?
                    """,
                    (
                        STATE_PENDING_REVIEW,
                        now,
                        calculation.amount_cents,
                        calculation.currency,
                        calculation.period,
                        calculation.status,
                        _encode_sequence(calculation.rule_ids),
                        _encode_sequence(calculation.issues),
                        calculation.rulebook_version,
                        case_id,
                        STATE_DRAFT,
                        record.revision,
                    ),
                )
                if self._conn.execute("SELECT changes()").fetchone()[0] == 0:
                    raise InvalidTransitionError(
                        f"Case {case_id!r} was already advanced by another writer"
                    )
                self._append_audit(
                    case_id,
                    COMMAND_SUBMIT,
                    STATE_DRAFT,
                    STATE_PENDING_REVIEW,
                    record.revision,
                    actor_id,
                    now,
                )
            return self._get_locked(case_id)

    def list_cases_by_state(self, state: str, limit: int = 100) -> tuple[CaseRecord, ...]:
        """Return cases in `state`, most recently updated first."""
        state = validate_state(state)
        limit = validate_limit(limit)
        with self._lock:
            rows = self._conn.execute(
                f"""
                SELECT {_CASE_SELECT_COLUMNS}
                FROM cases
                WHERE state = ?
                ORDER BY updated_at DESC, case_id DESC
                LIMIT ?
                """,
                (state, limit),
            ).fetchall()
        return tuple(_record_from_row(row) for row in rows)

    def delete_all_cases(self) -> int:
        """Delete every case and its audit trail. Pilot/training queue resets only.

        Not part of the reviewer approval workflow: the only caller is the
        queue-clearing admin action in `apps/reviewer-app`.
        """
        with self._lock, self._conn:
            count = self._conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
            self._conn.execute("DELETE FROM audit_events")
            self._conn.execute("DELETE FROM cases")
        return count

    def _get_locked(self, case_id: str) -> CaseRecord:
        """Fetch the extended `CaseRecord`. Caller must already hold self._lock."""
        row = self._conn.execute(
            f"""
            SELECT {_CASE_SELECT_COLUMNS}
            FROM cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()
        if row is None:
            raise CaseNotFoundError(f"Case {case_id!r} not found")
        return _record_from_row(row)


def _record_from_row(row: tuple) -> CaseRecord:
    """Build a `CaseRecord` by keyword, so column order is never load-bearing."""
    (
        case_id,
        state,
        revision,
        preparer_id,
        reviewer_id,
        created_at,
        updated_at,
        approved_at,
        amount_cents,
        currency,
        period,
        calculation_status,
        rule_ids,
        issues,
        rulebook_version,
    ) = row
    return CaseRecord(
        case_id=case_id,
        state=state,
        revision=revision,
        preparer_id=preparer_id,
        reviewer_id=reviewer_id,
        created_at=created_at,
        updated_at=updated_at,
        approved_at=approved_at,
        amount_cents=amount_cents,
        currency=currency,
        period=period,
        calculation_status=calculation_status,
        rule_ids=_decode_sequence(rule_ids),
        issues=_decode_sequence(issues),
        rulebook_version=rulebook_version,
    )


__all__ = ["SqliteCaseStore"]
