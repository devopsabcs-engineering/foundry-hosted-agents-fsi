"""SQLite-backed ApprovalRepository implementing the quote-preparation
employee-approval state machine.

State machine: DRAFT -> PENDING_REVIEW -> APPROVED | REJECTED. Revising a
case (any state) creates a new revision, resets state to DRAFT, and clears
the prior reviewer/approval — a new revision always requires fresh review
(revision-invalidation rule). open_training_preview is only permitted while
a case is APPROVED.

Actor authorization: the reviewerId passed to approve/reject must never
equal the preparerId of the current revision (SelfApprovalError). Only a
distinct human "employee reviewer" actor may decide a case.

Idempotency: replaying approve/reject with the same reviewerId against a
case already in that terminal state (APPROVED/REJECTED) is a no-op that
returns the existing CaseRecord without appending another audit event or
raising an error. A decide call that disagrees with an existing decision
(different reviewerId, or the opposite action) raises InvalidTransitionError
instead of silently overwriting history.

Concurrency: all reads and writes go through a single sqlite3.Connection
guarded by a threading.Lock, so concurrent approve/reject calls on the same
case are fully serialized. The state-changing UPDATE additionally carries a
WHERE state=... AND revision=... guard and checks changes() before
recording the audit event, so a losing writer is rejected explicitly rather
than silently overwriting the winner's decision even if the lock were ever
relaxed to allow multiple connections.

State-machine scope note (review finding F-01): the quote-contract
schema's canonical state enum and the research state-machine diagram
(.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-
workshop-research.md, lines 229-231) list six states -- INCOMPLETE, DRAFT,
UNSUPPORTED, PENDING_REVIEW, APPROVED, REJECTED -- but only the latter four
are implemented as CaseRecord.state values here. INCOMPLETE/UNSUPPORTED are
calculator-only gate results (apps/workshop/calculator.py's
STATUS_INCOMPLETE/STATUS_UNSUPPORTED, lines 19-26/63-84):
src/quote-preparation-agent/graph.py's composition_node calls
create_draft()/submit_for_review() unconditionally, regardless of the
calculator's status, so a persisted case always moves DRAFT ->
PENDING_REVIEW even when its calculation is INCOMPLETE or UNSUPPORTED --
that calculation result travels alongside the case in a separate
`calculation` dict and is never written to the `cases.state` column. No
code path in this repository, the agent, or the MCP services ever assigns
"INCOMPLETE" or "UNSUPPORTED" to a CaseRecord.state; they are unreachable
here by design, not by omission.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

STATE_DRAFT = "DRAFT"
STATE_PENDING_REVIEW = "PENDING_REVIEW"
STATE_APPROVED = "APPROVED"
STATE_REJECTED = "REJECTED"

COMMAND_CREATE_DRAFT = "CREATE_DRAFT"
COMMAND_SUBMIT = "SUBMIT"
COMMAND_APPROVE = "APPROVE"
COMMAND_REJECT = "REJECT"
COMMAND_REVISE = "REVISE"
COMMAND_OPEN_PREVIEW = "OPEN_PREVIEW"


class ApprovalRepositoryError(Exception):
    """Base class for all ApprovalRepository errors."""


class CaseNotFoundError(ApprovalRepositoryError):
    """Raised when a case id has no row in the repository."""


class CaseAlreadyExistsError(ApprovalRepositoryError):
    """Raised when create_draft is called with a case id already present."""


class InvalidTransitionError(ApprovalRepositoryError):
    """Raised when a command is not permitted from the case's current state."""


class SelfApprovalError(ApprovalRepositoryError):
    """Raised when the reviewerId passed to approve/reject equals the preparerId."""


@dataclass(frozen=True)
class CaseRecord:
    """A snapshot of one case row."""

    case_id: str
    state: str
    revision: int
    preparer_id: str
    reviewer_id: str | None
    created_at: str
    updated_at: str
    approved_at: str | None


@dataclass(frozen=True)
class AuditEvent:
    """One append-only audit-trail row for a case."""

    sequence: int
    command: str
    from_state: str | None
    to_state: str
    revision: int
    actor_id: str
    at: str


class ApprovalRepository:
    """SQLite-backed store for quote-preparation case approval state.

    db_path defaults to ":memory:" (a private in-memory database, suitable
    for tests). Pass a file path to persist cases across process restarts.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    preparer_id TEXT NOT NULL,
                    reviewer_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES cases (case_id)
                )
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_draft(self, case_id: str, preparer_id: str) -> CaseRecord:
        """Create a new case row in state DRAFT at revision 1."""
        with self._lock:
            existing = self._conn.execute(
                "SELECT 1 FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if existing is not None:
                raise CaseAlreadyExistsError(f"Case {case_id!r} already exists")

            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO cases
                        (case_id, state, revision, preparer_id, reviewer_id,
                         created_at, updated_at, approved_at)
                    VALUES (?, ?, 1, ?, NULL, ?, ?, NULL)
                    """,
                    (case_id, STATE_DRAFT, preparer_id, now, now),
                )
                self._append_audit(case_id, COMMAND_CREATE_DRAFT, None, STATE_DRAFT, 1, preparer_id, now)
            return self._get_locked(case_id)

    def submit_for_review(self, case_id: str, actor_id: str) -> CaseRecord:
        """Transition DRAFT -> PENDING_REVIEW."""
        with self._lock:
            record = self._get_locked(case_id)
            if record.state != STATE_DRAFT:
                raise InvalidTransitionError(
                    f"Cannot submit case {case_id!r} for review from state {record.state!r}"
                )
            now = self._now()
            with self._conn:
                self._conn.execute(
                    "UPDATE cases SET state = ?, updated_at = ? WHERE case_id = ?",
                    (STATE_PENDING_REVIEW, now, case_id),
                )
                self._append_audit(
                    case_id, COMMAND_SUBMIT, STATE_DRAFT, STATE_PENDING_REVIEW, record.revision, actor_id, now
                )
            return self._get_locked(case_id)

    def approve(self, case_id: str, reviewer_id: str) -> CaseRecord:
        """Transition PENDING_REVIEW -> APPROVED. See class docstring for
        the self-approval and idempotency rules enforced here."""
        return self._decide(case_id, reviewer_id, approve=True)

    def reject(self, case_id: str, reviewer_id: str) -> CaseRecord:
        """Transition PENDING_REVIEW -> REJECTED. See class docstring for
        the self-approval and idempotency rules enforced here."""
        return self._decide(case_id, reviewer_id, approve=False)

    def _decide(self, case_id: str, reviewer_id: str, *, approve: bool) -> CaseRecord:
        command = COMMAND_APPROVE if approve else COMMAND_REJECT
        target_state = STATE_APPROVED if approve else STATE_REJECTED

        with self._lock:
            record = self._get_locked(case_id)

            if reviewer_id == record.preparer_id:
                raise SelfApprovalError(
                    f"Reviewer {reviewer_id!r} cannot {command.lower()} case {case_id!r}: "
                    "reviewer is also the preparer of the current revision"
                )

            if record.state == target_state and record.reviewer_id == reviewer_id:
                # Idempotent replay of an already-applied decision: no-op.
                return record

            if record.state != STATE_PENDING_REVIEW:
                raise InvalidTransitionError(
                    f"Cannot {command.lower()} case {case_id!r} in state {record.state!r}"
                )

            now = self._now()
            approved_at = now if approve else None
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE cases
                    SET state = ?, reviewer_id = ?, updated_at = ?, approved_at = ?
                    WHERE case_id = ? AND state = ? AND revision = ?
                    """,
                    (target_state, reviewer_id, now, approved_at, case_id, STATE_PENDING_REVIEW, record.revision),
                )
                changed = self._conn.execute("SELECT changes()").fetchone()[0]
                if changed == 0:
                    raise InvalidTransitionError(
                        f"Case {case_id!r} was already decided by another reviewer"
                    )
                self._append_audit(
                    case_id, command, STATE_PENDING_REVIEW, target_state, record.revision, reviewer_id, now
                )
            return self._get_locked(case_id)

    def revise(self, case_id: str, actor_id: str) -> CaseRecord:
        """Create a new revision from any state. Resets state to DRAFT and
        clears reviewerId/approved_at (revision-invalidation rule)."""
        with self._lock:
            record = self._get_locked(case_id)
            new_revision = record.revision + 1
            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE cases
                    SET state = ?, revision = ?, preparer_id = ?, reviewer_id = NULL,
                        updated_at = ?, approved_at = NULL
                    WHERE case_id = ?
                    """,
                    (STATE_DRAFT, new_revision, actor_id, now, case_id),
                )
                self._append_audit(case_id, COMMAND_REVISE, record.state, STATE_DRAFT, new_revision, actor_id, now)
            return self._get_locked(case_id)

    def open_training_preview(self, case_id: str, actor_id: str) -> CaseRecord:
        """Record a training-preview audit event. Only permitted while
        state == APPROVED; does not itself change state or revision."""
        with self._lock:
            record = self._get_locked(case_id)
            if record.state != STATE_APPROVED:
                raise InvalidTransitionError(
                    f"Cannot open training preview for case {case_id!r} in state {record.state!r}"
                )
            now = self._now()
            with self._conn:
                self._append_audit(
                    case_id, COMMAND_OPEN_PREVIEW, STATE_APPROVED, STATE_APPROVED, record.revision, actor_id, now
                )
            return record

    def get_case(self, case_id: str) -> CaseRecord:
        with self._lock:
            return self._get_locked(case_id)

    def get_audit_trail(self, case_id: str) -> list[AuditEvent]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT sequence, command, from_state, to_state, revision, actor_id, at
                FROM audit_events
                WHERE case_id = ?
                ORDER BY sequence
                """,
                (case_id,),
            ).fetchall()
            return [AuditEvent(*row) for row in rows]

    def _get_locked(self, case_id: str) -> CaseRecord:
        """Fetch a CaseRecord. Caller must already hold self._lock."""
        row = self._conn.execute(
            """
            SELECT case_id, state, revision, preparer_id, reviewer_id, created_at, updated_at, approved_at
            FROM cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()
        if row is None:
            raise CaseNotFoundError(f"Case {case_id!r} not found")
        return CaseRecord(*row)

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
        """Insert the next append-only audit row. Caller must already hold
        self._lock and an open transaction (self._conn)."""
        next_sequence = (
            self._conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM audit_events WHERE case_id = ?", (case_id,)
            ).fetchone()[0]
            + 1
        )
        self._conn.execute(
            """
            INSERT INTO audit_events
                (case_id, sequence, command, from_state, to_state, revision, actor_id, at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (case_id, next_sequence, command, from_state, to_state, revision, actor_id, at),
        )
