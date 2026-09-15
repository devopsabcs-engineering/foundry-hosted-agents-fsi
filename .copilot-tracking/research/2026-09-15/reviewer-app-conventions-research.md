<!-- markdownlint-disable-file -->
# Reviewer App Conventions Research

**Date**: 2026-09-15
**Status**: Complete
**Scope**: Existing FastAPI + SPA conventions in `apps/web-chat/`, the full `ApprovalRepository` API surface, agent toolbox/test conventions, dependency management, and containerization — as a template for a **second, reviewer-facing web app** that lists `PENDING_REVIEW` cases with premium amounts and lets a reviewer approve/reject/revise.

**Research mode**: Read-only. No files were modified.

---

## Research Questions

1. What is the complete public API surface, SQLite schema, and state-machine semantics of `ApprovalRepository`? What would a Cosmos DB port need to preserve?
2. How is the FastAPI app structured (`create_app()`, DI, middleware, error handling, static mounting, testability seams)?
3. What exactly does `auth.py` validate, and what changes for an app-role check instead of a group-membership check?
4. What is the frontend stack, build tooling, MSAL flow, SSE consumption, styling, and i18n handling?
5. What are the test conventions (framework, fixtures, conftest, TestClient, auth stubbing, sys.path handling)?
6. Where are all requirements files, and is `azure-cosmos` present anywhere?
7. What does the web-chat Dockerfile do?
8. Which files are templates vs. must-be-new for the reviewer app, and what semantic traps exist?

---

## File Inventory (verified on disk)

### apps/web-chat/ (excluding node_modules, frontend/dist)

| Path | Lines |
|---|---|
| apps/web-chat/.dockerignore | 14 |
| apps/web-chat/app.py | 296 |
| apps/web-chat/auth.py | 55 |
| apps/web-chat/Dockerfile | 20 |
| apps/web-chat/requirements.txt | 7 |
| apps/web-chat/tests/test_app.py | 168 |
| apps/web-chat/tests/test_auth.py | 61 |
| apps/web-chat/frontend/index.html | 10 |
| apps/web-chat/frontend/package.json | 24 |
| apps/web-chat/frontend/package-lock.json | (lockfile, present) |
| apps/web-chat/frontend/vite.config.js | 6 |
| apps/web-chat/frontend/src/main.jsx | 220 |
| apps/web-chat/frontend/src/request.js | 4 |
| apps/web-chat/frontend/src/samples.js | 20 |
| apps/web-chat/frontend/src/stream.js | 29 |
| apps/web-chat/frontend/src/style.css | 10 (minified, very long lines) |
| apps/web-chat/frontend/tests/request.test.js | 10 |
| apps/web-chat/frontend/tests/samples.test.js | 19 |
| apps/web-chat/frontend/tests/stream.test.js | 24 |

Notably **absent**: `pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini`, `conftest.py`, `tsconfig.json`, `.env` (in app dir), `requirements-dev.txt`.

### Other relevant source

| Path | Lines |
|---|---|
| src/quote-preparation-agent/approval_repository.py | 354 |
| apps/workshop/approval_repository.py | 354 (**byte-identical**, SHA256 `16546DA2…4AA1`) |
| src/quote-preparation-agent/toolbox.py | 194 |
| src/quote-preparation-agent/graph.py | 254 |
| src/quote-preparation-agent/main.py | 87 |
| src/quote-preparation-agent/tests/test_graph.py | 147 |
| src/quote-preparation-agent/tests/test_toolbox.py | 59 |
| apps/workshop/tests/test_approval_repository.py | 294 |
| apps/workshop/calculator.py | 88 |
| infra/web-chat.bicep | 141 |
| scripts/setup-web-chat-identity.ps1 | ~113 |
| data/synthetic/quote-contract.schema.json | (JSON Schema draft-07) |

---

## 1. Approval Repository — Full API Surface

Source: `src/quote-preparation-agent/approval_repository.py` (354 lines). **Identical copy** at `apps/workshop/approval_repository.py` — verified by SHA256 hash. The vendored duplication is deliberate (see toolbox.py lines 64-73): the hosted agent container ships only `src/quote-preparation-agent/`.

### 1.1 Module-level constants

approval_repository.py lines 55-65:

```python
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
```

### 1.2 Exception hierarchy (lines 68-86)

| Line | Class | Base | Raised when |
|---|---|---|---|
| 68 | `ApprovalRepositoryError` | `Exception` | (base class only) |
| 72 | `CaseNotFoundError` | `ApprovalRepositoryError` | case id has no row |
| 76 | `CaseAlreadyExistsError` | `ApprovalRepositoryError` | `create_draft` on an existing id |
| 80 | `InvalidTransitionError` | `ApprovalRepositoryError` | command not permitted from current state; also the losing-writer conflict |
| 84 | `SelfApprovalError` | `ApprovalRepositoryError` | `reviewer_id == preparer_id` on approve/reject |

**Trap**: `SelfApprovalError` is *not* a subclass of `InvalidTransitionError`. An HTTP layer that maps only `InvalidTransitionError` → 409 will let `SelfApprovalError` escape as a 500. It needs its own mapping (403 is the semantically correct code).

### 1.3 Data classes (lines 88-113)

```python
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
```

Both are `frozen=True` dataclasses → value equality. This is load-bearing: `test_idempotent_repeated_approve_calls_do_not_double_record` asserts `first == second == third` (test_approval_repository.py lines 131-141).

### 1.4 Complete public method signatures

| Line | Signature | Returns | Raises |
|---|---|---|---|
| 122 | `__init__(self, db_path: str = ":memory:") -> None` | — | — |
| 127 | `close(self) -> None` | `None` | — |
| 167 | `create_draft(self, case_id: str, preparer_id: str) -> CaseRecord` | new DRAFT @ rev 1 | `CaseAlreadyExistsError` |
| 190 | `submit_for_review(self, case_id: str, actor_id: str) -> CaseRecord` | PENDING_REVIEW | `CaseNotFoundError`, `InvalidTransitionError` |
| 209 | `approve(self, case_id: str, reviewer_id: str) -> CaseRecord` | APPROVED | `CaseNotFoundError`, `SelfApprovalError`, `InvalidTransitionError` |
| 214 | `reject(self, case_id: str, reviewer_id: str) -> CaseRecord` | REJECTED | `CaseNotFoundError`, `SelfApprovalError`, `InvalidTransitionError` |
| 262 | `revise(self, case_id: str, actor_id: str) -> CaseRecord` | DRAFT @ rev+1 | `CaseNotFoundError` |
| 282 | `open_training_preview(self, case_id: str, actor_id: str) -> CaseRecord` | unchanged record | `CaseNotFoundError`, `InvalidTransitionError` |
| 298 | `get_case(self, case_id: str) -> CaseRecord` | `CaseRecord` | `CaseNotFoundError` |
| 302 | `get_audit_trail(self, case_id: str) -> list[AuditEvent]` | list (empty if no events) | — (no `CaseNotFoundError`) |

Private: `_init_schema` (130), `_now` (164, `@staticmethod`), `_decide` (219), `_get_locked` (315), `_append_audit` (329).

### 1.5 **CRITICAL: there is NO list/query method**

> **There is no method to list or query multiple cases.** Every read method (`get_case`, `get_audit_trail`) takes a single `case_id`. There is **no** `list_cases()`, `list_pending()`, `find_by_state()`, or any pending-review-queue accessor anywhere in the 354-line file. The only `SELECT` statements are the existence probe at line 170, the single-row fetch at lines 317-324, the per-case audit fetch at lines 304-312, the `MAX(sequence)` at lines 338-340, and `SELECT changes()` at line 243.

**This is the single largest gap for the reviewer app.** A pending-review queue endpoint requires a brand-new repository method, e.g. `list_by_state(state: str) -> list[CaseRecord]`.

### 1.6 **CRITICAL: the premium amount is NOT stored**

> **The premium amount / calculation is persisted nowhere in the repository.** The `cases` table has no `amount_cents`, `currency`, `period`, `rule_ids`, `status`, or `issues` column. The calculation travels alongside the case as a separate in-memory `calculation` dict in the LangGraph state (graph.py lines 246-253) and is discarded when the graph run ends.

Confirming evidence:

- `cases` CREATE TABLE (approval_repository.py lines 133-144) — eight columns, none monetary.
- graph.py `composition_node` (lines 213-254): `calculation = toolbox.calculate_quote(...)` (line 232) is placed only into the returned state dict (line 248), never passed to `create_draft`/`submit_for_review` (lines 238-240).
- The class docstring makes this explicit (approval_repository.py lines 35-44): *"that calculation result travels alongside the case in a separate `calculation` dict and is never written to the `cases.state` column."*

**Implication for the reviewer app**: to show premium amounts in a pending-review list, the team must either (a) add persisted calculation columns/fields, or (b) recompute on read by re-fetching the application + rulebook and re-running `calculate_quote`. Option (b) is deterministic (calculator.py is pure, no I/O — lines 38-88) but will **silently change the displayed amount if the rulebook version changes between submission and review**. The rulebook has a `version` field and the calculator accepts `expected_rulebook_version` (calculator.py lines 41, 59-60) returning `EVIDENCE_UNAVAILABLE` / `RULE_VERSION_MISMATCH` — but nothing records which version a given case was calculated against.

### 1.7 Complete SQLite schema (verbatim)

approval_repository.py lines 130-161:

```python
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
```

Notes:

- No index on `cases.state` — a pending-review scan is a full table scan today (fine at workshop scale).
- No `UNIQUE (case_id, sequence)` constraint on `audit_events` — sequence uniqueness is enforced only procedurally by `_append_audit` under the lock.
- `FOREIGN KEY` is declared but SQLite does **not** enforce foreign keys unless `PRAGMA foreign_keys = ON` is set; it is never set. The constraint is documentation only.
- All timestamps are TEXT ISO-8601 UTC strings from `_now()` (lines 163-165): `datetime.now(timezone.utc).isoformat()`.

### 1.8 Concurrency model

`__init__` (lines 122-125):

```python
    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()
```

Single `sqlite3.Connection`, `check_same_thread=False`, guarded by one `threading.Lock`. Every public method opens `with self._lock:` and then a nested `with self._conn:` transaction.

**Trap**: `threading.Lock` is **not** async-aware and **not** multi-process-aware. In a FastAPI app this repository must be called from a thread pool (`await asyncio.to_thread(...)` or a sync `def` path operation, which FastAPI automatically runs in a threadpool). Calling it directly from an `async def` handler will block the event loop for the duration of the SQLite I/O. Additionally, with `--workers > 1` or multiple Container App replicas, the Python lock provides no protection across processes — only the SQL guard (below) does.

### 1.9 State-transition rules

```text
(none) --CREATE_DRAFT--> DRAFT --SUBMIT--> PENDING_REVIEW --APPROVE--> APPROVED
                                                          --REJECT --> REJECTED

any state --REVISE--> DRAFT (revision+1, reviewer_id=NULL, approved_at=NULL)
APPROVED  --OPEN_PREVIEW--> APPROVED (audit-only, no state/revision change)
```

- `create_draft`: only when the id does not exist. Always `state=DRAFT`, `revision=1`, `reviewer_id=NULL`, `approved_at=NULL`.
- `submit_for_review` (lines 190-207): **strictly** `state == STATE_DRAFT`, else `InvalidTransitionError`. Does not change `revision`.
- `approve`/`reject`: delegate to `_decide`.
- `revise` (lines 262-280): permitted **from any state including DRAFT and REJECTED** — there is no guard at all. It also **reassigns `preparer_id = actor_id`**.
- `open_training_preview` (lines 282-296): only from `APPROVED`; appends an audit event with `from_state == to_state == APPROVED`; returns the record fetched **before** the append (line 296 returns `record`, not a refetched row) — harmless since nothing changed.

### 1.10 `_decide` — self-approval, idempotency, and the concurrency guard (verbatim)

approval_repository.py lines 219-260:

```python
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
```

**Order of checks is semantically load-bearing** (this exact ordering must be preserved in any port):

1. `CaseNotFoundError` (from `_get_locked`).
2. **Self-approval** — checked *before* idempotency and *before* the state check. A preparer replaying their own approve gets `SelfApprovalError`, not an idempotent no-op.
3. **Idempotent replay** — `state == target_state AND reviewer_id == reviewer_id` → return existing record, **append no audit event**.
4. **State guard** — anything not `PENDING_REVIEW` → `InvalidTransitionError`. This is what rejects (a) a different reviewer overriding an existing decision, (b) the opposite action by the same reviewer, (c) an approve on a DRAFT case never submitted, (d) a stale command after a `revise`.
5. **Compare-and-swap** — `UPDATE … WHERE case_id=? AND state='PENDING_REVIEW' AND revision=?` followed by `SELECT changes()`; zero rows → `InvalidTransitionError`.

### 1.11 Revision-invalidation logic (verbatim)

approval_repository.py lines 262-280:

```python
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
```

**Traps**:

- `revise` **overwrites `preparer_id` with `actor_id`**. If a reviewer revises a case, that reviewer becomes the preparer of the new revision and is then permanently barred from approving it (self-approval rule). This is arguably intentional but is a real UX consequence for a reviewer app that offers a "request revision" action.
- `revise`'s UPDATE has **no `WHERE state=… AND revision=…` guard** — unlike `_decide`. It relies entirely on the Python `threading.Lock`. A multi-replica deployment or an async port that relaxes the lock loses all protection against concurrent double-revise (which would skip revision numbers or lose an audit sequence).
- `revise` is permitted from `DRAFT` → produces `from_state == "DRAFT"`, `to_state == "DRAFT"`, revision+1. No guard prevents this.

### 1.12 Audit-trail append logic (verbatim)

approval_repository.py lines 329-354:

```python
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
```

Sequence is a **per-case** read-modify-write `MAX(sequence)+1` — correct only because the caller holds the lock and the enclosing transaction.

`get_audit_trail` (lines 302-313):

```python
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
```

`_get_locked` (lines 315-327):

```python
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
```

**Trap**: both `CaseRecord(*row)` and `AuditEvent(*row)` are **positional** constructions. The `SELECT` column order is coupled to the dataclass field order. Adding a field to either dataclass without updating every `SELECT` silently corrupts data.

### 1.13 State-machine scope note (from the module docstring, lines 25-44)

The canonical contract enum has **six** states (`data/synthetic/quote-contract.schema.json` line 24):

```json
"state": { "enum": ["INCOMPLETE", "UNSUPPORTED", "DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"] },
```

Only **four** are implementable as `CaseRecord.state`. `INCOMPLETE` and `UNSUPPORTED` are calculator-only statuses (calculator.py lines 19-22) and are **never** written to `cases.state`. `composition_node` calls `create_draft()`/`submit_for_review()` unconditionally regardless of calculation status (graph.py lines 236-245).

> **Trap for the reviewer app**: a case in `PENDING_REVIEW` may have an `INCOMPLETE` or `UNSUPPORTED` calculation with `amountCents: None`. The premium column in the pending-review list **must handle a null amount**. Fixture `CASE-SYN-005` (missing plan) and `CASE-SYN-003` (unsupported) are exactly these cases, and `test_unsupported_case_never_invents_an_amount` (test_graph.py lines 103-115) asserts `amountCents is None` while `workflow_state == "PENDING_REVIEW"`.

### 1.14 What a Cosmos DB port must preserve semantically

| # | Semantic | SQLite mechanism | Cosmos equivalent / risk |
|---|---|---|---|
| 1 | Atomic compare-and-swap on decide | `UPDATE … WHERE state=? AND revision=?` + `SELECT changes()` | Use an **ETag / `if_match`** precondition on `replace_item`. Catch `CosmosAccessConditionFailedError` (412) and raise `InvalidTransitionError("… already decided by another reviewer")`. A naive read-modify-write **silently loses the guard**. |
| 2 | Case + audit written in one transaction | `with self._conn:` wrapping UPDATE + INSERT | Cosmos transactional batch requires **same partition key**. Either co-locate `cases` and `audit_events` under `partitionKey = /caseId`, or embed the audit array inside the case document. Cross-container/cross-partition = non-atomic; a crash between writes leaves a decided case with no audit row. |
| 3 | Per-case audit sequence = `MAX(sequence)+1` | read-modify-write under a process lock | With embedded audit array + ETag, `len(audit)+1` is safe. With a separate container, a concurrent append can **duplicate a sequence number** — there is no unique constraint today, so nothing would detect it. |
| 4 | Self-approval check ordering | checked **first**, before idempotency | Must remain first; moving it after the idempotency check changes behaviour for a preparer replay. |
| 5 | Idempotent replay appends no audit event | early `return record` | Must short-circuit **before** any write. An "upsert then append" implementation grows the audit trail on every replay. |
| 6 | `revise` clears `reviewer_id`/`approved_at` and **reassigns `preparer_id`** | single UPDATE | Preserve all four field mutations together. |
| 7 | `revise` has **no** optimistic guard | Python lock only | In Cosmos there is no Python lock across replicas — **add** an ETag precondition to `revise` or accept lost updates. This is a genuine behaviour gap, not a port artifact. |
| 8 | Timestamps are ISO-8601 UTC strings | `datetime.now(timezone.utc).isoformat()` | Keep the string format; do not switch to Cosmos `_ts` epoch seconds — `approved_at` is compared to `None` and surfaced as a string. |
| 9 | Value equality of returned records | `@dataclass(frozen=True)` | Keep the dataclasses as the boundary type; do not return raw Cosmos dicts (they carry `_rid`/`_etag`/`_ts` which break `==`). |
| 10 | `get_audit_trail` returns `[]` (not an error) for an unknown case | no existence check | Preserve — callers rely on it. |
| 11 | `close()` exists and is called by test fixtures | `self._conn.close()` | Keep a no-op or client-close `close()` so existing fixtures still work. |
| 12 | `db_path=":memory:"` default for tests | in-memory SQLite | Cosmos has no in-memory mode. Either keep an in-memory/fake implementation behind the same interface for tests, or require the Cosmos emulator. **This decision drives the whole test strategy for the reviewer app.** |

Additional Cosmos considerations: partition key choice (`/caseId` gives per-case transactional batches but no efficient cross-partition "list all PENDING_REVIEW"; `/state` gives a cheap queue query but rewrites the partition key on every transition, which Cosmos forbids in-place — requires delete+create). A common resolution is `/caseId` partitioning plus a cross-partition query filtered on `state` with an appropriate index.

---

## 2. FastAPI App Structure

Source: `apps/web-chat/app.py` (296 lines).

### 2.1 Imports and settings

Lines 1-18: stdlib, then `httpx`, `azure.identity.aio.DefaultAzureCredential`, `fastapi` (`Depends`, `FastAPI`, `Header`, `HTTPException`, `Request`), `fastapi.responses` (`JSONResponse`, `StreamingResponse`), `fastapi.staticfiles.StaticFiles`, `httpx_sse.aconnect_sse`, `pydantic` (`BaseModel`, `ConfigDict`, `Field`), then `from auth import Identity, PilotAuth`.

**Note**: `from auth import …` is a **flat, non-package import**. It works only because `apps/web-chat` is on `sys.path` (CI sets `PYTHONPATH: apps/web-chat` — web-chat-build.yml line 33; the Dockerfile relies on WORKDIR `/app` being the script dir).

Lines 24-48, `Settings` — a `@dataclass(frozen=True)` with a `from_env()` classmethod:

```python
@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    pilot_group_id: str
    agent_endpoint: str
    managed_identity_client_id: str | None = None
    session_ttl: int = 3600
    max_sessions: int = 128
    max_turns: int = 20

    @classmethod
    def from_env(cls):
        endpoint = os.environ["AGENT_ENDPOINT"]
        parsed = httpx.URL(endpoint)
        if parsed.scheme != "https" or not parsed.host.endswith(".services.ai.azure.com"):
            raise ValueError("AGENT_ENDPOINT must be a Foundry HTTPS endpoint")
        return cls(
            tenant_id=str(uuid.UUID(os.environ["ENTRA_TENANT_ID"])),
            client_id=str(uuid.UUID(os.environ["ENTRA_CLIENT_ID"])),
            pilot_group_id=str(uuid.UUID(os.environ["PILOT_GROUP_ID"])),
            agent_endpoint=endpoint,
            managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID"),
        )
```

Conventions worth copying: frozen dataclass (not pydantic `BaseSettings`), `os.environ[...]` (fail-fast KeyError on missing), `uuid.UUID(...)` round-trip as **input validation and normalization**, explicit scheme/host allowlist for the upstream URL.

### 2.2 `create_app()` factory — the testability seam

Line 159:

```python
def create_app(settings=None, verifier=None, upstream=None):
    settings = settings or Settings.from_env()
    verifier = verifier or PilotAuth(settings.tenant_id, settings.client_id, settings.pilot_group_id)
    store = SessionStore(settings)
    slots = asyncio.Semaphore(4)
```

**Three injectable seams, all defaulting to production implementations**:

| Parameter | Default | Injected in tests as |
|---|---|---|
| `settings` | `Settings.from_env()` | `SETTINGS` literal (test_app.py line 11) |
| `verifier` | `PilotAuth(...)` | `TestAuth()` duck-typed stub (test_app.py lines 14-18) |
| `upstream` | `FoundryClient(settings)` built in lifespan | `FakeAgent()` (test_app.py lines 21-30) |

This pattern is **directly reusable** for the reviewer app — substitute `repository` for `upstream`.

### 2.3 Lifespan and app construction (lines 165-173)

```python
    @asynccontextmanager
    async def lifespan(application):
        application.state.upstream = upstream or FoundryClient(settings)
        yield
        if upstream is None:
            await application.state.upstream.close()

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.store = store
```

Key conventions:

- The real upstream client is constructed **inside** `lifespan`, not at import — so tests that inject a fake never construct a `DefaultAzureCredential`.
- The injected object is **not** closed on shutdown (`if upstream is None`) — the injector owns its lifecycle.
- `docs_url=None, redoc_url=None, openapi_url=None` — **OpenAPI/Swagger is fully disabled**. The reviewer app should match this unless there is an explicit reason not to.
- Shared mutable state hangs off `application.state.*` so tests can reach it (`app.state.store` in the `client` fixture).

### 2.4 Dependency injection for auth (lines 175-176)

```python
    async def identity(authorization: str | None = Header(default=None)):
        return await verifier.authorize(authorization)
```

A closure over `verifier`, used as `owner: Identity = Depends(identity)`. There is **no** `app.dependency_overrides` usage anywhere — auth is swapped by constructor injection instead. The dependency reads the raw `Authorization` header via `Header(default=None)` rather than `fastapi.security` helpers.

### 2.5 Middleware (lines 178-193)

```python
    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.headers.get("content-length", "").isdigit():
            if int(request.headers["content-length"]) > 40000:
                return JSONResponse({"detail": "Request too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' https://login.microsoftonline.com; "
            "frame-src https://login.microsoftonline.com; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self' https://login.microsoftonline.com"
        )
        return response
```

One single `@application.middleware("http")` doing body-size rejection (413) plus five security headers. No CORS middleware — the SPA is served same-origin from the same app. The CSP allowlists `login.microsoftonline.com` only, for MSAL redirect.

### 2.6 Routes, status codes, response models

| Line | Method + path | Status | Auth | Response |
|---|---|---|---|---|
| 195-197 | `GET /healthz` | 200 | none | `{"status": "ok"}` |
| 199-202 | `GET /api/config` | 200 | **none** | `{tenantId, clientId, scope, environment}` |
| 204-206 | `GET /api/me` | 200 | `Depends(identity)` | `{"objectId": …}` |
| 208-210 | `POST /api/conversations` | **201** | `Depends(identity)` | `{"id": …}` |
| 212-217 | `DELETE /api/conversations/{identifier}` | **204** | `Depends(identity)` | (empty) |
| 219-291 | `POST /api/conversations/{identifier}/messages` | 200 | `Depends(identity)` | `text/event-stream` |

- **No `response_model=` is used anywhere.** Handlers return plain dicts. Only the *request* body is a pydantic model.
- Path params are typed `uuid.UUID` → FastAPI auto-422 on a malformed id (asserted in test_app.py line 137).
- `status_code=201` / `status_code=204` are set on the decorator.
- `GET /api/config` is deliberately unauthenticated (the SPA needs it before it can sign in) and is asserted to contain no secrets (test_app.py lines 130-136).

### 2.7 Request model (lines 89-91)

```python
class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=8000)
```

`extra="forbid"` is load-bearing — `test_multiturn_history_is_owned_by_server` asserts that sending an extra `history` key yields 422 (test_app.py line 78). `str_strip_whitespace=True` + `min_length=1` rejects whitespace-only input.

### 2.8 Error handling

- **No custom exception handlers and no `@app.exception_handler` anywhere.** Everything is raised as `fastapi.HTTPException(status, "message")` with a **positional** status code and a human-readable, non-leaking message.
- Domain-layer errors are converted at the raise site, not centrally: `SessionStore.create` raises `HTTPException(429, …)` directly (lines 71, 73); `SessionStore.get` raises `HTTPException(404, …)` (lines 81, 85).
- Upstream failures inside the SSE generator are caught in two tiers (lines 274-281): known exceptions (`httpx.HTTPError`, `ValueError`, `TimeoutError`) → one generic message; bare `Exception` → a different generic message. **Neither includes the original exception text** — `test_failed_response_does_not_poison_history` asserts `"secret upstream" not in response.text` (test_app.py line 91).
- Observability is one `logger.warning` line with a request id, an outcome label, and a duration (lines 288-289) — never the payload.

**Convention to copy for the reviewer app**: map `ApprovalRepositoryError` subclasses to HTTP status codes at the route boundary, with generic client-facing text and the detail only in logs. Suggested mapping: `CaseNotFoundError` → 404, `SelfApprovalError` → 403, `InvalidTransitionError` → 409, `CaseAlreadyExistsError` → 409.

### 2.9 Static file mounting (lines 293-296)

```python
    dist = Path(__file__).parent / "frontend" / "dist"
    if dist.exists():
        application.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return application
```

Mounted **last**, at `/`, with `html=True` (SPA fallback to `index.html`). Guarded by `dist.exists()` so tests and local API-only runs work without a built frontend. Because it is mounted after every `/api/*` route, API routes win.

---

## 3. Auth Module

Source: `apps/web-chat/auth.py` (55 lines) — reproduced in full in section 3.1.

### 3.1 Full source with line numbers

| Lines | Content |
|---|---|
| 9-12 | `@dataclass(frozen=True) class Identity: tenant_id: str; object_id: str` |
| 15-24 | `PilotAuth.__init__(tenant_id, client_id, group_id)` — stores all three, derives `self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"`, constructs `PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys", timeout=10)` |
| 26-50 | `verify(token) -> Identity` (synchronous) |
| 52-55 | `authorize(authorization) -> Identity` (async wrapper) |

```python
    def verify(self, token: str) -> Identity:
        try:
            key = self.keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid"]},
                leeway=30,
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, "A valid access token is required.") from exc
        if claims.get("tid") != self.tenant_id or claims.get("azp") != self.client_id:
            raise HTTPException(403, "This application is not authorized.")
        if "Chat.Access" not in claims.get("scp", "").split():
            raise HTTPException(403, "Chat permission is required.")
        if self.group_id not in claims.get("groups", []):
            raise HTTPException(403, "Pilot membership is required. Contact the pilot administrator.")
        if not isinstance(claims["oid"], str) or not claims["oid"]:
            raise HTTPException(401, "A user identity is required.")
        return Identity(claims["tid"], claims["oid"])

    async def authorize(self, authorization: str | None) -> Identity:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 32768:
            raise HTTPException(401, "Sign in to continue.")
        return await asyncio.to_thread(self.verify, authorization[7:])
```

### 3.2 JWKS caching

Delegated entirely to `PyJWKClient` (line 21). `PyJWKClient` caches keys internally by default. The client is constructed **once per `PilotAuth` instance** (i.e. once per app), so key material is fetched lazily on first token and reused. `timeout=10` bounds the fetch. There is no explicit TTL/refresh logic in this repo.

### 3.3 Validated claims

| Claim | How validated | Failure |
|---|---|---|
| signature | `algorithms=["RS256"]` + JWKS key | 401 |
| `exp`, `iat`, `nbf` | `options={"require": [...]}` + PyJWT default verification, `leeway=30` | 401 |
| `aud` | `audience=self.client_id` (PyJWT) | 401 |
| `iss` | `issuer=self.issuer` (PyJWT) | 401 |
| `tid` | required + explicit `!= self.tenant_id` | 403 |
| `azp` | explicit `!= self.client_id` | 403 |
| `scp` | `"Chat.Access" not in claims.get("scp", "").split()` | 403 |
| `groups` | `self.group_id not in claims.get("groups", [])` | 403 |
| `oid` | required + `isinstance(str)` + non-empty | 401 |

### 3.4 Error responses

Three distinct status codes, all with fixed, non-leaking messages:

- **503** `"Sign-in verification is temporarily unavailable."` — JWKS endpoint unreachable (`PyJWKClientConnectionError`). Caught **before** the generic `PyJWTError` branch, because `PyJWKClientConnectionError` is a `PyJWTError` subclass; reversing the order would mask outages as 401s.
- **401** `"A valid access token is required."` / `"A user identity is required."` / `"Sign in to continue."`
- **403** `"This application is not authorized."` / `"Chat permission is required."` / `"Pilot membership is required. Contact the pilot administrator."`

### 3.5 Fail-closed on group overage

`claims.get("groups", [])` returns `[]` when the `groups` claim is absent. In Entra, when a user is in too many groups, Entra **omits** `groups` and emits `_claim_names`/`_claim_sources` pointing at the Graph endpoint instead. This implementation therefore **denies** rather than falling back to a Graph call. This is asserted explicitly:

```python
def test_group_overage_fails_closed(auth_fixture):
    auth, key, claims = auth_fixture
    del claims["groups"]
    claims["_claim_names"] = {"groups": "src1"}
    with pytest.raises(HTTPException, match="Pilot membership"):
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))
```

(test_auth.py lines 45-51)

### 3.6 Async handling

`authorize` (lines 52-55) does cheap header shape checks synchronously — presence, `Bearer ` prefix, and a **32 768-byte length cap** (DoS guard) — then offloads the CPU-bound/blocking `verify` to `asyncio.to_thread`. This keeps the event loop free during the (potentially network-bound, definitely CPU-bound RSA) verification.

### 3.7 **What changes for an app-role check instead of a group check**

The change is small and localized — **one line plus a constructor parameter**:

```python
# current (line 46)
if self.group_id not in claims.get("groups", []):
    raise HTTPException(403, "Pilot membership is required. Contact the pilot administrator.")

# app-role equivalent
if self.required_role not in claims.get("roles", []):
    raise HTTPException(403, "Reviewer role is required. Contact the pilot administrator.")
```

Supporting facts and consequences:

1. **The `roles` claim is a JSON array of `appRole.value` strings**, not GUIDs — unlike `groups`, which contains object GUIDs. So the constructor parameter becomes a role *name* (e.g. `"Reviewer.Decide"`), not a `uuid.UUID`. That means `Settings.from_env()`'s `str(uuid.UUID(os.environ["PILOT_GROUP_ID"]))` normalization (app.py line 44) does **not** apply and must be replaced with plain string validation.
2. **The app registration already has an `appRoles` block** — `scripts/setup-web-chat-identity.ps1` lines 73-80 define role `Pilot.User` with `id = 'b7d4e912-3f6a-4c88-9e21-5a0d8f4b6c33'` (line 12), `allowedMemberTypes = @('User')`, and the pilot group is already assigned to it via `appRoleAssignedTo` (lines 90-95). `appRoleAssignmentRequired = $true` is set on the service principal (lines 86, 89). So the reviewer app can add a second `appRole` (e.g. `Reviewer.Decide`) to the same or a new app registration and reuse the whole script shape.
3. **`groupMembershipClaims = 'SecurityGroup'` (line 56) can be dropped** for a role-only app — that is what emits the `groups` claim at all. Removing it also removes the group-overage failure mode entirely (roles are never subject to the overage truncation that groups are), so `test_group_overage_fails_closed` has no role-based analogue; the equivalent negative test is simply an absent/empty `roles` claim.
4. **Fail-closed semantics are preserved for free**: `claims.get("roles", [])` on a token with no `roles` claim yields `[]` → 403. Same shape as today.
5. **The `scp` check stays** — scope (delegated permission) and role are orthogonal. A reviewer app would likely use a different scope value (e.g. `Review.Access`) alongside the role, requiring a corresponding change at auth.py line 44 and in `/api/config`'s scope string (app.py line 202).
6. **Both can be enforced together** if desired (role AND group) — they are independent `if` blocks.
7. The `verify` verification `options={"require": [...]}` list does **not** include `"roles"`. It should not — `require` triggers a 401 for a missing claim, whereas the desired behaviour for a missing role is a 403 with the reviewer-specific message. Keep the role check as an explicit post-decode `if`, matching the existing group check.

---

## 4. Frontend

### 4.1 Framework, tooling, package manager

`apps/web-chat/frontend/package.json` (24 lines), verbatim:

```json
{
  "name": "foundry-quote-preparation-web-chat",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vite build",
    "test": "node --test tests/*.test.js"
  },
  "dependencies": {
    "@azure/msal-browser": "^4.0.0",
    "@fontsource-variable/dm-sans": "^5.0.0",
    "@fontsource-variable/newsreader": "^5.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "eventsource-parser": "^3.0.0",
    "lucide-react": "^0.468.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-markdown": "^10.0.0",
    "remark-gfm": "^4.0.0",
    "vite": "^7.0.0"
  }
}
```

- **React 19**, **Vite 7**, `"type": "module"`, **JSX not TypeScript** — there is **no `tsconfig.json`** and no TypeScript dependency anywhere. Source files are `.jsx` / `.js`.
- **Package manager: npm**, lockfile `apps/web-chat/frontend/package-lock.json` (present, committed). CI uses `npm ci` when the lock exists, else `npm install` (web-chat-build.yml lines 36-42).
- **No `devDependencies` block** — everything (including `vite` and `@vitejs/plugin-react`) is a runtime `dependency`. Unusual but consistent; copy it as-is to avoid churn.
- **Test runner is the Node built-in test runner** (`node --test`), not Vitest/Jest. No test framework dependency at all.

Exact scripts: `dev` → `vite --host 127.0.0.1`; `build` → `vite build`; `test` → `node --test tests/*.test.js`.

### 4.2 Build config

`vite.config.js` (6 lines), verbatim:

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
});
```

Dev proxy forwards `/api` to the local uvicorn on 8000. Default output dir (`dist/`).

`index.html` (10 lines) — single `<div id="root">` + `<script type="module" src="/src/main.jsx">`, `<html lang="en">`, theme colour `#184c40`.

### 4.3 Directory layout

```
frontend/
  .gitignore
  index.html
  package.json
  package-lock.json
  vite.config.js
  src/
    main.jsx      (220 lines — all components + bootstrap in one file)
    request.js    (4 lines — idempotency-key helper)
    samples.js    (20 lines — demo prompt catalogue)
    stream.js     (29 lines — SSE consumer)
    style.css     (10 lines, minified)
  tests/
    request.test.js
    samples.test.js
    stream.test.js
```

**No component directory, no router, no state-management library.** One `main.jsx` holding `ToolButton`, `CopyAnswer`, `Chat`, and `start()`.

### 4.4 MSAL configuration and token acquisition

Bootstrap (main.jsx lines 194-211):

```javascript
async function start() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Configuration is unavailable.');
  const config = await response.json();
  const auth = new PublicClientApplication({
    auth: { clientId: config.clientId, authority: `https://login.microsoftonline.com/${config.tenantId}`, redirectUri: window.location.origin },
    cache: { cacheLocation: 'sessionStorage' },
  });
  await auth.initialize();
  const result = await auth.handleRedirectPromise();
  const account = result?.account ?? auth.getAllAccounts()[0] ?? null;
  if (account) auth.setActiveAccount(account);
  createRoot(document.getElementById('root')).render(<Chat auth={auth} config={config} initialAccount={account} />);
}

start().catch(() => {
  createRoot(document.getElementById('root')).render(<div className="startup-error" role="alert">The quote workspace could not load. Refresh to try again.</div>);
});
```

Key points:

- MSAL config comes **from the server** (`GET /api/config`), never hard-coded or from a `.env` — so tenant/client IDs are deployment config, not build config.
- `cacheLocation: 'sessionStorage'` (not localStorage) — token cache dies with the tab.
- **Redirect flow**, not popup: `loginRedirect` / `logoutRedirect` / `handleRedirectPromise`.
- `redirectUri: window.location.origin`.

Token acquisition + attachment (main.jsx lines 39-64):

```javascript
  async function token() {
    try {
      return (await auth.acquireTokenSilent({ account, scopes: [config.scope] })).accessToken;
    } catch (failure) {
      if (failure instanceof InteractionRequiredAuthError) {
        throw new Error('Your sign-in needs attention. Sign out and sign in again.');
      }
      throw failure;
    }
  }

  async function api(path, options = {}) {
    const accessToken = await token();
    const response = await fetch(path, { ...options, headers: {
      ...options.headers,
      'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`,
    } });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status}).`);
    }
    return response;
  }
```

- `acquireTokenSilent` only — **no automatic interactive fallback**. `InteractionRequiredAuthError` is converted to a user-facing "sign out and sign in again" message. This is a deliberate simplification.
- `scopes: [config.scope]` where the server returns `api://{clientId}/Chat.Access` (app.py line 202).
- A single `api()` wrapper attaches the bearer token and normalizes errors by reading FastAPI's `{"detail": "..."}` body. **This maps exactly onto the `HTTPException(status, "message")` convention in section 2.8** — the two halves are designed together.
- Sign-in (lines 80-86) uses `loginRedirect({ scopes: [config.scope], prompt: 'select_account' })`.
- Access gate: on mount, `GET /api/me` is called; success → `setAllowed(true)`, failure → the error message is displayed and the UI stays disabled (lines 66-73).

### 4.5 SSE streaming consumption

`src/stream.js` (29 lines), verbatim:

```javascript
import { createParser } from 'eventsource-parser';

export async function consumeResponse(body, onEvent) {
  let completed = false;
  const parser = createParser({
    onEvent(event) {
      const payload = JSON.parse(event.data);
      if (payload.type === 'error') {
        throw new Error(`${payload.text} Reference: ${payload.requestId}`);
      }
      if (payload.type === 'done') completed = true;
      onEvent(payload);
    },
    onError(error) { throw error; },
  });
  const reader = body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
    parser.feed(decoder.decode());
    if (!completed) throw new Error('The response was interrupted. Try again.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
```

Uses `fetch` + `ReadableStream` + `eventsource-parser`, **not** `EventSource` — because `EventSource` cannot send an `Authorization` header or a POST body. `TextDecoder({stream: true})` handles multi-byte characters split across chunks. Absence of a terminal `done` event is treated as truncation.

Server side: `sse()` (app.py lines 155-157) emits `"data: " + json.dumps(payload, ensure_ascii=True) + "\n\n"`; responses set `media_type="text/event-stream"` with headers `{"X-Accel-Buffering": "no", "X-Request-ID": request_id}`; a `": keepalive\n\n"` comment is emitted every 10 s (app.py lines 262-265).

**This entire SSE stack is chat-specific.** A reviewer app performing list/approve/reject operations needs plain JSON request/response and can drop `stream.js`, `eventsource-parser`, and the keepalive machinery.

### 4.6 Idempotency helper

`src/request.js` (4 lines), verbatim:

```javascript
export function messageRequest(previous, conversation, text) {
  if (previous?.conversation === conversation && previous.text === text) return previous;
  return { conversation, text, key: crypto.randomUUID() };
}
```

Paired with the server's `Idempotency-Key: uuid.UUID` header (app.py line 221) and the `session.completed` replay cache (app.py lines 223-233). **Directly reusable in concept** for the reviewer app — but note the ApprovalRepository's own idempotency (section 1.10, rule 3) already makes a duplicate `approve` a no-op, so an HTTP-level key is belt-and-braces rather than essential.

### 4.7 Styling approach

`src/style.css` — **10 lines of hand-minified CSS** (very long lines, one rule-block per line). Approach:

- CSS custom properties on `:root`: `--green:#184c40`, `--muted:#66736c`, `--border:#dce3df`, `--accent:#b22938`.
- Plain class names (`.workspace`, `.sidebar`, `.composer`, `.tool`) — **no CSS modules, no Tailwind, no CSS-in-JS**.
- Fonts via `@fontsource-variable/dm-sans` and `@fontsource-variable/newsreader`, imported in `main.jsx` (lines 7-8) — **self-hosted**, no Google Fonts CDN (required by the CSP `default-src 'self'`).
- Icons via `lucide-react`.
- Responsive `@media(max-width:760px)` block; `@media(prefers-reduced-motion:reduce)` block disabling animation/transition/scroll-behavior.
- Accessibility: `:focus-visible { outline: 2px solid #be3947; outline-offset: 3px }`; `aria-label` / `role="log"` / `aria-live="polite"` / `role="alert"` / `role="status"` used throughout `main.jsx`.

### 4.8 i18n / bilingual (en-CA / fr-CA) handling

> **The frontend is NOT internationalized.** All UI strings in `main.jsx` are hard-coded English ("New quote", "Sign in with Microsoft", "Preparing quote", "Synthetic training data only…"). `index.html` is `<html lang="en">`. There is no i18n library, no locale switcher, and no message catalogue.

Bilingual content exists only in **two** places:

1. **Server-side unwrapping of the agent's bilingual payload** — `content_text` (app.py lines 94-99):

   ```python
   def content_text(content, locale="en-CA"):
       """The agent emits `content[].text` as a bilingual {"en-CA", "fr-CA"} map."""
       text = content.get("text")
       if isinstance(text, dict):
           text = text.get(locale) or next((value for value in text.values() if isinstance(value, str)), "")
       return text.strip() if isinstance(text, str) else ""
   ```

   The default `locale="en-CA"` is **never overridden** — `FoundryClient.events` calls `content_text(content)` with no locale argument (app.py line 145). So the chat UI always shows en-CA and silently drops fr-CA.

2. **The agent/domain layer**, which is genuinely bilingual — `graph.py` `_STATUS_TEMPLATES` (lines 88-110) pairs `en-CA`/`fr-CA` for every status, `_bounded_message` (lines 113-121) returns `{locale: ... for locale in ("en-CA", "fr-CA")}`, and the contract schema requires both keys (`quote-contract.schema.json`, `localized` definition, lines 25-32). `test_graph.py::_assert_message_is_bounded` asserts `set(applicant_message) == {"en-CA", "fr-CA"}` (line 74).

**Implication**: if the reviewer app must be bilingual, that is **net-new work** — there is no existing pattern to copy on the frontend. The only reusable idea is `content_text`'s locale-selection helper, and the fixtures' `expectedDisplay` localized strings (e.g. `{"en-CA": "Employee approval required", "fr-CA": "Approbation d'un employé requise"}`).

### 4.9 Copy wholesale vs. chat-specific

| Asset | Verdict |
|---|---|
| `package.json` shape, scripts, npm+lock, React 19 + Vite 7 | **Copy wholesale** (drop `eventsource-parser`, `react-markdown`, `remark-gfm` unless rendering markdown) |
| `vite.config.js` | **Copy verbatim** |
| `index.html` | **Copy**, change `<title>` |
| MSAL bootstrap `start()` + `token()` + `api()` (main.jsx 39-64, 194-211) | **Copy wholesale** — this is the highest-value reusable block |
| `style.css` custom properties, focus-visible, reduced-motion, responsive block | **Copy the design tokens and a11y rules**; layout classes need rework for a table/queue UI |
| `request.js` | Copy if an HTTP idempotency key is wanted |
| `stream.js` + SSE consumption | **Chat-specific — drop** |
| `samples.js` + demo-query UI | **Chat-specific — drop** |
| `Chat` component, composer, message list, `CopyAnswer`, markdown rendering | **Chat-specific — rewrite** as a case list + detail + decision actions |
| `node --test tests/*.test.js` convention | **Copy wholesale** |

---

## 5. Test Conventions

### 5.1 Framework and plugins

- **Python: `pytest` only.** Root `requirements.txt` (2 lines): `pytest>=8.0`, `jsonschema>=4.21`.
- **No plugins**: no `pytest-asyncio`, no `pytest-cov`, no `pytest-mock`, no `anyio` plugin, no `httpx` ASGI transport usage.
- **No pytest configuration file exists anywhere in the repo** — verified: no `pytest.ini`, no `pyproject.toml`, no `setup.cfg`, no `tox.ini`.
- **No `conftest.py` exists anywhere in the repo** — verified by a repo-wide recursive search. Fixtures are defined inline in each test module.
- **JavaScript: the Node built-in test runner** (`node:test` + `node:assert/strict`). No Jest/Vitest.

### 5.2 How tests are invoked

`apps/web-chat` backend (web-chat-build.yml lines 31-35):

```yaml
      - name: Install backend test dependencies
        run: python -m pip install -r apps/web-chat/requirements.txt pytest
      - name: Backend authorization and session tests
        env:
          PYTHONPATH: apps/web-chat
        run: python -m pytest apps/web-chat/tests -q --junitxml=web-chat-evidence/backend.xml
```

**`PYTHONPATH: apps/web-chat` is how `from app import ...` and `from auth import ...` resolve.** There is no `sys.path` manipulation inside `apps/web-chat/tests/*`.

Everything else (continuous-validation.yml lines 40-52):

```yaml
      - name: Agent graph unit tests
        run: |
          pytest src/quote-preparation-agent/tests -v --junitxml=evidence/agent.xml
      - name: Deterministic evaluation checks
        run: |
          pytest eval -v --junitxml=evidence/deterministic.xml
      - name: Reporting and contract tests
        run: |
          pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests \
            -v --junitxml=evidence/reporting.xml
```

Every run emits **JUnit XML evidence** consumed by `scripts/ci_results.py`. A reviewer-app workflow should follow the same `--junitxml=` convention.

### 5.3 sys.path / import resolution — the two patterns

This repo has **two distinct** conventions. Both are deliberate; `pyrightconfig.json` documents why:

> "Cross-directory imports here are resolved by each test/module file inserting its target directory into sys.path at runtime… This is intentional: apps/workshop, mcp/application-server, mcp/rulebook-server, and src/quote-preparation-agent are each standalone, unpackaged modules by design (Review finding F-07), not a misconfiguration. Pyright/Pylance cannot see these runtime sys.path insertions statically, so it may report 'reportMissingImports'… these are expected editor-only false positives."

`pyrightconfig.json` therefore sets `"reportMissingImports": "none"`.

**Pattern A — `PYTHONPATH` env var** (used by `apps/web-chat/tests/`): tests contain no path manipulation; CI sets `PYTHONPATH: apps/web-chat`.

**Pattern B — in-file `sys.path.insert`** (used by everything else), e.g. test_graph.py lines 13-20:

```python
import sys
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "workshop"))

import main  # noqa: E402
from approval_repository import ApprovalRepository  # noqa: E402
```

and test_approval_repository.py lines 11-31:

```python
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
```

Conventions: `from __future__ import annotations` first, `Path(__file__).resolve().parents[N]` to derive dirs, `sys.path.insert(0, ...)`, and `# noqa: E402` on every import that follows the insertion. `src/quote-preparation-agent/tests/__init__.py` and `apps/workshop/tests/__init__.py` **do** exist (empty package markers) — but `apps/web-chat/tests/` has **no** `__init__.py`.

### 5.4 File and function naming

- Modules: `test_<subject>.py` (`test_app.py`, `test_auth.py`, `test_graph.py`, `test_toolbox.py`, `test_approval_repository.py`).
- Functions: `test_<behaviour_in_a_full_sentence>` — long and descriptive, e.g. `test_users_cannot_read_write_or_delete_other_sessions`, `test_successful_retry_replays_without_reinvocation_or_extra_turn`, `test_a_different_reviewer_cannot_override_an_existing_decision`, `test_unsupported_case_never_invents_an_amount`. Names assert the **guarantee**, not the mechanism.
- Helper functions are `_`-prefixed (`_submitted_case`, `_run`, `_stub_model`, `_assert_message_is_bounded`, `_assert_repository_never_decided`).
- Every test module opens with a docstring stating scope and, where relevant, **"No network, LLM, or hosted-agent access is used anywhere in this file."**
- Module-level constants for actor ids: `PREPARER = "MOCK-CONTROLLER-001"`, `REVIEWER = "MOCK-REVIEWER-001"`, `OTHER_REVIEWER = "MOCK-REVIEWER-002"` (test_approval_repository.py lines 33-35). These match the contract schema's `actorId` pattern `^MOCK-[A-Z0-9-]{1,48}$`.

### 5.5 Fixture patterns

Repository fixture with teardown (test_approval_repository.py lines 38-42):

```python
@pytest.fixture()
def repo():
    repository = ApprovalRepository(":memory:")
    yield repository
    repository.close()
```

Auth fixture returning a **tuple** of collaborators, with the JWKS client monkey-patched via `SimpleNamespace` (test_auth.py lines 12-27):

```python
@pytest.fixture
def auth_fixture():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = PilotAuth("tenant", "client", "pilot")
    auth.keys = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key())
    )
    now = int(time.time())
    claims = {
        "iss": auth.issuer, "aud": "client", "tid": "tenant", "oid": "user",
        "azp": "client", "scp": "Chat.Access", "groups": ["pilot"],
        "iat": now, "nbf": now, "exp": now + 300,
    }
    return auth, private_key, claims
```

**This is the auth-testing pattern to copy**: generate a real RSA key, replace `auth.keys` with a `SimpleNamespace` whose `get_signing_key_from_jwt` returns the public key, build a valid claims dict, then sign real JWTs with `jwt.encode(claims, key, algorithm="RS256")`. Real signature verification runs; only JWKS retrieval is stubbed. `cryptography` comes in transitively via `PyJWT[crypto]`.

Parametrized negative cases (test_auth.py lines 36-44):

```python
@pytest.mark.parametrize("field,value", [
    ("aud", "other"), ("iss", "https://other.example"), ("tid", "other"),
    ("azp", "other"), ("scp", "Other.Scope"), ("groups", []),
    ("groups", ["other"]), ("exp", 1), ("oid", ""),
])
def test_invalid_claims_denied(auth_fixture, field, value):
    auth, key, claims = auth_fixture
    claims[field] = value
    with pytest.raises(HTTPException) as failure:
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))
    assert failure.value.status_code in (401, 403)
```

### 5.6 How the FastAPI app is tested

**`fastapi.testclient.TestClient`** (which wraps `httpx` + Starlette's portal). **Not** raw `httpx.AsyncClient(transport=ASGITransport(...))`.

test_app.py lines 1-38:

```python
import json
import time
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import FoundryClient, SessionStore, Settings, create_app
from auth import Identity

SETTINGS = Settings("tenant", "client", "pilot", "https://test.services.ai.azure.com/responses")


class TestAuth:
    async def authorize(self, header):
        if header not in ("Bearer alice", "Bearer bob"):
            raise HTTPException(401, "Sign in")
        return Identity("tenant", header.split()[1])


class FakeAgent:
    def __init__(self):
        self.inputs = []
        self.fail = False

    async def events(self, messages):
        self.inputs.append(messages)
        if self.fail:
            raise ValueError("secret upstream error details")
        yield {"type": "answer", "text": "Assessment complete."}


@pytest.fixture
def client():
    agent = FakeAgent()
    app = create_app(SETTINGS, TestAuth(), agent)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer alice"
        yield client, agent, app.state.store
```

Conventions:

- `Settings` is constructed **positionally** with plain strings — `Settings("tenant", "client", "pilot", "https://test.services.ai.azure.com/responses")`. It bypasses `from_env()` entirely, so no env vars are needed and no UUID validation runs. The endpoint still must end in `.services.ai.azure.com`? **No** — that check lives in `from_env()` only, but the test value satisfies it anyway.
- **`TestClient` is used as a context manager** (`with TestClient(app) as client:`) — this is required to trigger the `lifespan` handler. Tests that assert lifespan behaviour depend on it (`test_real_client_lifespan_with_managed_identity`, lines 41-48).
- The fixture **yields a tuple** `(client, agent, store)` and each test destructures with a shadowing rebind: `client, agent, _ = client`.
- A default `Authorization` header is set on the client so most tests don't repeat it; tests that need a different principal just reassign `client.headers["Authorization"] = "Bearer bob"`.

### 5.7 How auth is stubbed/faked

**Duck typing, not `unittest.mock`, not `app.dependency_overrides`.** `TestAuth` (test_app.py lines 14-18) is a five-line class implementing only `async def authorize(self, header)` — the single method `create_app`'s `identity` dependency calls. It is passed as the `verifier` positional argument. It returns a real `auth.Identity` so downstream ownership comparisons (`session.owner == owner`, which relies on `Identity` being a frozen dataclass) behave correctly.

For `PilotAuth` itself, the JWKS client is replaced with `SimpleNamespace` (section 5.5).

**`unittest.mock` is used nowhere in any of these test files.** The only `pytest` built-in helper used is `monkeypatch`, and only for env vars (test_app.py lines 41-43).

### 5.8 Async test handling

> **There are no `async def` test functions anywhere.** Because there is no `pytest-asyncio` or `anyio` plugin, an `async def test_...` would be collected and skipped with a warning. Async code is exercised **synchronously through `TestClient`**, which runs the ASGI app in its own event loop portal. The stubs (`TestAuth.authorize`, `FakeAgent.events`) are `async`/async-generator but are awaited by the app, not by the test.

**This is a hard constraint for the reviewer app**: either keep the same pattern (sync tests + `TestClient`), or add `pytest-asyncio` to a requirements file (which would be the repo's first test plugin).

### 5.9 Representative test, verbatim

test_app.py lines 111-127 — covers idempotency, streaming assertions, cross-user isolation, and header checks in one:

```python
def test_failed_key_can_retry_and_keys_are_conversation_scoped(client):
    client, agent, store = client
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    agent.fail = True
    client.post(route, json={"text": "Hi"}, headers=headers)
    assert store.sessions[identifier].completed == {}
    agent.fail = False
    assert '"type": "done"' in client.post(route, json={"text": "Hi"}, headers=headers).text
    another = client.post("/api/conversations").json()["id"]
    client.post(f"/api/conversations/{another}/messages", json={"text": "Hi"}, headers=headers)
    assert len(agent.inputs) == 3
    assert len(store.sessions[identifier].messages) == 2
    assert client.post(route, json={"text": "Hi"}, headers={"Idempotency-Key": "invalid"}).status_code == 422
```

Note the SSE-parsing idiom used when event order matters (test_app.py lines 73-74):

```python
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert [event["type"] for event in events] == ["status", "answer", "done"]
```

### 5.10 Spy/stub repository pattern (test_graph.py), verbatim

`src/quote-preparation-agent/tests/test_graph.py` lines 1-100. The spy **subclasses the real repository**, records the permitted calls, delegates via `super()`, and makes the forbidden methods raise `AssertionError`:

```python
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
```

A complementary **structural** guarantee is asserted in test_toolbox.py lines 52-58:

```python
def test_toolbox_never_wraps_approve_reject_or_revise():
    # This is the structural guarantee behind "the agent must never call
    # approve/reject/revise": no such function exists to call.
    for forbidden in ("approve", "reject", "revise", "open_training_preview"):
        assert not hasattr(toolbox, forbidden), f"toolbox must never expose {forbidden!r}"
```

**This is the single most important architectural constraint for the reviewer app**: `toolbox.py`'s module docstring (lines 22-27) states that `approve`, `reject`, `revise`, and `open_training_preview` *"are intentionally never imported or wrapped here: those transitions may only be performed by a human reviewer through a separate reviewer-facing surface, never by agent code."* **The reviewer app IS that separate surface.** The reviewer app must import the repository directly and must **not** route through `toolbox.py`.

---

## 6. Dependency Management

### 6.1 Every requirements file (complete, verbatim)

**`requirements.txt`** (repo root — shared test deps):

```text
pytest>=8.0
jsonschema>=4.21
```

**`apps/web-chat/requirements.txt`**:

```text
fastapi==0.135.1
uvicorn==0.41.0
httpx==0.28.1
httpx-sse==0.4.3
PyJWT[crypto]==2.12.1
azure-identity==1.25.3
aiohttp>=3.13.3,<4
```

**`src/quote-preparation-agent/requirements.txt`**:

```text
azure-ai-agentserver-langgraph==1.0.0b17
langgraph==1.2.11
mcp>=1.6.0,<2
```

**`mcp/application-server/requirements.txt`** and **`mcp/rulebook-server/requirements.txt`**: present (FastMCP server deps; not read in full — not needed for the reviewer app).

### 6.2 Conventions

- The web-chat app uses **exact `==` pins** for everything except `aiohttp` (a range, because it is a transitive constraint).
- Shared test deps live in the **root** `requirements.txt`; app-specific runtime deps live **next to the app**.
- **There is no `requirements-dev.txt` anywhere in the repo.** `pytest` is installed ad-hoc in CI (`pip install -r apps/web-chat/requirements.txt pytest`, web-chat-build.yml line 31) or via the root `requirements.txt`.
- No `pyproject.toml`, no Poetry/uv/PDM, no lockfile for Python. Frontend has `package-lock.json`.
- `pytest` is **not** in `apps/web-chat/requirements.txt` — deliberately, so the container image does not ship the test runner.
- `cryptography` (needed by test_auth.py) arrives transitively via `PyJWT[crypto]`.

### 6.3 **`azure-cosmos` is NOT present anywhere**

> A repo-wide regex search for `azure-cosmos|azure\.cosmos|CosmosClient|cosmosdb|DocumentDB` returned **zero matches**. There is no Cosmos dependency, no Cosmos client code, no Cosmos Bicep resource, and no Cosmos emulator configuration. A Cosmos port is entirely greenfield.

---

## 7. Containerization

`apps/web-chat/Dockerfile` (20 lines), verbatim:

```dockerfile
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/tests/request.test.js frontend/tests/stream.test.js ./tests/
RUN npm test && npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY app.py auth.py ./
COPY --from=frontend /build/dist ./frontend/dist
RUN IDENTITY_ENDPOINT=http://localhost/identity IDENTITY_HEADER=build-check python -c "import asyncio; from app import FoundryClient, Settings; client = FoundryClient(Settings('tenant', 'client', 'group', 'https://test.services.ai.azure.com')); asyncio.run(client.close())"
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
```

Analysis:

- **Two stages.** Stage 1 `node:22-bookworm-slim` builds the SPA; stage 2 `python:3.13-slim-bookworm` runs the API.
- Lockfile-first layer caching: `package.json` + `package-lock.json` copied before sources, then `npm ci`.
- **`npm test` runs inside the image build** — a failing frontend test fails the image build. Note it copies only `request.test.js` and `stream.test.js`, **not** `samples.test.js` (which reads `data/synthetic/fixtures/` four directories up — outside the build context).
- `frontend/dist` is copied from stage 1 into `./frontend/dist`, which is exactly where `create_app()` looks (`Path(__file__).parent / "frontend" / "dist"`).
- Only `app.py` and `auth.py` are copied — **no tests ship in the image**, consistent with `.dockerignore` (which is deny-all `**` plus explicit `!` allowlist entries).
- A **build-time smoke check** (line 17) constructs a `FoundryClient` and closes it, catching import errors and credential-construction failures at build time rather than at first request. `IDENTITY_ENDPOINT`/`IDENTITY_HEADER` are set so `DefaultAzureCredential` picks a managed-identity path without contacting IMDS.
- Runs as **non-root UID 10001**.
- `EXPOSE 8000`, matching `infra/web-chat.bicep` `targetPort: 8000` (line 113) and the `/healthz` liveness/readiness probes on port 8000 (lines 130-133).
- Entrypoint uses the **factory form**: `uvicorn app:create_app --factory`, so `Settings.from_env()` runs at startup inside the container.
- `--workers 1` — **important**: the single-worker choice is what makes the in-process `SessionStore` (and, for the reviewer app, any process-local lock) coherent. `infra/web-chat.bicep` line 135 sets `scale: { minReplicas: 1, maxReplicas: 1 }` for the same reason.

Deployment context (`infra/web-chat.bicep`): Container App with user-assigned managed identity, `AcrPull` on the registry, **Azure AI Developer/Foundry User** role (`53ca6127-db72-4b80-b1b0-d745d6d5456d`) on the Foundry project, digest-pinned image (never a floating tag), env vars `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `PILOT_GROUP_ID`, `AZURE_CLIENT_ID`, `AGENT_ENDPOINT` (lines 123-129). The file is explicitly **AUTHOR-ONLY / NOT DEPLOYED**, gated behind sign-offs G2/G3/G6 (lines 1-18), and is deliberately not wired into `azure.yaml`.

---

## 8. Gaps for the New Reviewer App

### 8.1 Files to use as templates (copy-and-adapt)

| Purpose | Template file | Notes |
|---|---|---|
| App factory, DI, middleware, static mount | apps/web-chat/app.py (lines 159-296) | Replace the `upstream` seam with a `repository` seam |
| Settings dataclass + `from_env()` | apps/web-chat/app.py lines 24-48 | Swap `AGENT_ENDPOINT` for a DB/Cosmos setting; swap `PILOT_GROUP_ID` for a role name |
| JWT auth | apps/web-chat/auth.py (whole file) | One-line change for role-based check (section 3.7) |
| Backend tests | apps/web-chat/tests/test_app.py, test_auth.py | `TestClient` + duck-typed `TestAuth` |
| Repository tests | apps/workshop/tests/test_approval_repository.py | `:memory:` fixture + `close()` teardown; concurrency test at lines 189-246 |
| Spy repository | src/quote-preparation-agent/tests/test_graph.py lines 44-71 | Invert the polarity: the reviewer app **must** call approve/reject/revise |
| Frontend scaffolding | frontend/package.json, vite.config.js, index.html | Copy verbatim, minus SSE/markdown deps |
| MSAL bootstrap + `api()` wrapper | frontend/src/main.jsx lines 39-64, 194-211 | Highest-value reusable block |
| Design tokens / a11y CSS | frontend/src/style.css | Copy `:root` vars, focus-visible, reduced-motion |
| Frontend tests | frontend/tests/request.test.js | `node:test` + `node:assert/strict` |
| Dockerfile | apps/web-chat/Dockerfile | Copy structure verbatim; change the smoke-check line |
| Container App infra | infra/web-chat.bicep | Copy; change `appName`, env vars, drop the Foundry `invokeRole` if the reviewer app never calls the agent |
| Entra app registration | scripts/setup-web-chat-identity.ps1 | Already has an `appRoles` block (lines 73-80) to extend |
| CI workflow | .github/workflows/web-chat-build.yml | Copy; change paths filter and `PYTHONPATH` |
| Dependency pinning | apps/web-chat/requirements.txt | Copy pins; drop `httpx-sse`; add `azure-cosmos` if porting |

### 8.2 What must be newly written

1. **`ApprovalRepository.list_by_state(...)` (or equivalent).** Does not exist. Required for the pending-review queue. Must decide sort order (likely `updated_at` ascending) and paging.
2. **Premium amount surfacing.** Not persisted (section 1.6). Either add persisted calculation fields, or recompute per case on read. Either way this is new code and a new decision.
3. **HTTP → domain-exception mapping.** No exception handlers exist today; domain errors are converted at each raise site. The reviewer app needs a deliberate mapping for four exception classes (§1.2) — and must not forget `SelfApprovalError` is not an `InvalidTransitionError`.
4. **Reviewer identity → `reviewer_id`.** The repository takes an opaque `reviewer_id: str`. The natural source is the JWT `oid` (`Identity.object_id`). But the schema's `actorId` pattern is `^MOCK-[A-Z0-9-]{1,48}$` (quote-contract.schema.json line 124) — a GUID `oid` does **not** match. Decide whether the DB stores the raw `oid` (schema-divergent) or a mapped pseudonym.
5. **A durable persistence path.** Today `ApprovalRepository(":memory:")` is the default and the graph constructs a fresh one per run (graph.py line 176). A reviewer app that reads cases created by the agent needs **shared** storage — that is the actual motivation for Cosmos.
6. **Pending-queue frontend** — table/list view, case detail, decision buttons, confirmation UX, audit-trail display. No existing UI to copy.
7. **Bilingual UI** if required — no existing frontend i18n (section 4.8).
8. **Role definition + assignment** in Entra (a second `appRole`, e.g. `Reviewer.Decide`).

### 8.3 Semantic traps a Cosmos port could silently break

Ranked by likelihood of a silent (non-crashing) regression:

1. **Losing the compare-and-swap.** `UPDATE … WHERE state=? AND revision=?` + `SELECT changes()` → must become an **ETag `if_match` precondition**. A plain read-modify-write compiles, passes single-threaded tests, and silently lets a second reviewer overwrite the first decision. The existing test `test_concurrent_approve_calls_by_different_reviewers_yield_exactly_one_winner` (test_approval_repository.py lines 189-246) is the regression guard — **port it**.
2. **Non-atomic case + audit write.** SQLite wraps both in one transaction. In Cosmos, separate items in separate partitions are two round trips. A failure between them yields a decided case with a missing audit event — invisible until an audit is requested. Mitigation: embed the audit array in the case document, or use a transactional batch with a shared partition key.
3. **Duplicate audit sequence numbers.** `MAX(sequence)+1` under a lock. There is **no unique constraint** on `(case_id, sequence)` today, so nothing detects a duplicate. In Cosmos without an ETag guard, concurrent appends silently produce two events with the same sequence, and `ORDER BY sequence` becomes non-deterministic.
4. **Idempotent replay growing the audit trail.** The early `return record` (approval_repository.py lines 233-235) fires **before** any write. An "upsert" style port appends an event every replay. `test_idempotent_repeated_approve_calls_do_not_double_record` catches this — **port it**.
5. **Self-approval check moved after the idempotency check.** Reordering changes behaviour only for the preparer-replay case, which no test covers today except implicitly. Preserve the exact order in section 1.10.
6. **`revise` losing the `preparer_id` reassignment.** Easy to omit when translating the five-field UPDATE. Consequence: a reviewer who revised a case would still be able to approve it, defeating separation of duties.
7. **`revise` still having no optimistic guard.** This is a pre-existing gap that SQLite's process lock papers over. In a multi-replica Cosmos deployment it becomes a real lost-update window. Consider **adding** an ETag precondition — but note that is a *behaviour change*, not a faithful port.
8. **Positional `CaseRecord(*row)` / `AuditEvent(*row)` construction.** Moving to Cosmos dicts means field-name mapping; a mismatch between document keys and dataclass field order silently swaps values (e.g. `created_at`/`updated_at`). Use keyword construction in the port.
9. **`amountCents` may legitimately be `None`.** `PENDING_REVIEW` cases with `INCOMPLETE`/`UNSUPPORTED` calculations have no amount (section 1.13). A reviewer UI or a Cosmos schema that assumes a number will break on fixtures `CASE-SYN-003` and `CASE-SYN-005`.
10. **`get_audit_trail` returns `[]`, never raises, for unknown cases.** A Cosmos port that adds an existence check changes the contract.
11. **Timestamps are ISO-8601 strings, not epochs.** `approved_at` is compared to `None` and is a display string. Do not substitute Cosmos `_ts`.
12. **`close()` must survive.** Test fixtures call it (test_approval_repository.py line 42).

### 8.4 Contract-schema fields the repository does NOT implement

The synthetic contract (`data/synthetic/quote-contract.schema.json`) models a **richer** workflow than the SQLite implementation. If the reviewer app or a Cosmos port is expected to satisfy the contract, these are all net-new:

| Contract field | Where defined | Implemented in `ApprovalRepository`? |
|---|---|---|
| `workflow.draftId` (`^DRAFT-SYN-[0-9]{3}$`) | schema `workflow` | **No** |
| `workflow.recordVersion` | schema `workflow` | **No** — optimistic concurrency is implicit via `state`+`revision`, never a caller-supplied version |
| `workflow.approvedRevision` | schema `workflow` | **No** — only `approved_at` timestamp |
| `workflow.previewRevision` | schema `workflow` | **No** — `open_training_preview` records an audit event only |
| `event.commandId` (`^CMD-[A-Z0-9-]{1,48}$`) | schema `event` | **No** — no caller-supplied command id |
| `event.actorRole` (`APPLICATION_CONTROLLER` \| `EMPLOYEE_SIMULATION`) | schema `event` | **No** — only `actor_id` |
| `nextCommand.expectedRecordVersion` | schema `command` | **No** |
| `nextCommand.reasonCode` (`REVIEWED` \| `REQUIRES_REVISION` \| `TRAINING_PREVIEW`) | schema `command` | **No** — no reason capture on approve/reject |
| states `INCOMPLETE`, `UNSUPPORTED` | schema `state` enum | **No** (by design — section 1.13) |
| `event.action` `RULES_CHANGED` | schema `event` | **No** |

Two of these are explicitly acknowledged in existing tests as deliberate omissions — `test_duplicate_command_replay_is_idempotent_and_not_a_new_transition` (test_approval_repository.py lines 248-264) and `test_stale_command_against_an_already_advanced_case_is_rejected_as_conflict` (lines 266-283) both document review finding **F-02**: *"ApprovalRepository has no caller-supplied commandId parameter"* and *"no caller-supplied recordVersion parameter."*

**A reviewer app that wants a reason code (`REQUIRES_REVISION` vs `REVIEWED`) on a decision cannot record it today.** That is a schema + repository change, not a UI change.

### 8.5 Naming and placement recommendation

Following existing convention, the new app belongs at `apps/reviewer-web/` (sibling to `apps/web-chat/`) with:

- `apps/reviewer-web/app.py`, `auth.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`
- `apps/reviewer-web/tests/test_app.py`, `test_auth.py` (no `__init__.py`, matching web-chat)
- `apps/reviewer-web/frontend/` mirroring the web-chat frontend layout
- `infra/reviewer-web.bicep` mirroring `infra/web-chat.bicep`
- `.github/workflows/reviewer-web-build.yml` mirroring `web-chat-build.yml`, with `PYTHONPATH: apps/reviewer-web`

The repository module itself should **not** be vendored a third time. Options: (a) import from `apps/workshop` via the existing `sys.path.insert` convention, or (b) if a Cosmos-backed repository is written, place it once (e.g. `apps/workshop/cosmos_approval_repository.py`) implementing the same interface so both `ApprovalRepository` and the Cosmos variant satisfy the same tests.

---

## Evidence Index

| Claim | Evidence |
|---|---|
| No list/query method | src/quote-preparation-agent/approval_repository.py — full read of all 354 lines; only single-case SELECTs at lines 170, 304-312, 317-324, 338-340 |
| Premium not persisted | approval_repository.py lines 133-144 (schema); graph.py lines 232, 246-253; approval_repository.py lines 35-44 (docstring) |
| Two approval_repository copies identical | SHA256 `16546DA26FBF1BD9543BB9B3A73AB518594D36401C5DD8CDE27CAFC34CD74AA1` for both |
| No pytest config / conftest | Repo-wide recursive search for `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `conftest.py` — only `pyrightconfig.json` and `package.json` found |
| No `azure-cosmos` | Repo-wide regex search `azure-cosmos\|azure\.cosmos\|CosmosClient\|cosmosdb\|DocumentDB` → 0 matches |
| `PYTHONPATH: apps/web-chat` | .github/workflows/web-chat-build.yml line 33 |
| `appRoles` already exist | scripts/setup-web-chat-identity.ps1 lines 12, 73-80, 90-95 |
| `groups` fails closed | apps/web-chat/auth.py line 46; apps/web-chat/tests/test_auth.py lines 45-51 |
| Contract has `recordVersion`/`commandId`/`actorRole` | data/synthetic/quote-contract.schema.json `workflow`, `event`, `command` definitions |
| Agent must never decide | src/quote-preparation-agent/toolbox.py lines 22-27; tests/test_toolbox.py lines 52-58; tests/test_graph.py lines 44-71 |
| Container port / workers | apps/web-chat/Dockerfile lines 18-19; infra/web-chat.bicep lines 113, 135 |

---

## Clarifying Questions

1. **Storage decision**: Is Cosmos DB already decided, or is a shared SQLite file (Azure Files volume on the Container App) acceptable for the pilot? The answer changes the entire test strategy — SQLite `:memory:` fixtures work today; Cosmos requires either the emulator in CI or a fake implementation behind the same interface.
2. **Premium amount source**: should the calculation be **persisted** at submission time (new repository/schema fields, requires touching the agent's `composition_node`), or **recomputed on read** in the reviewer app (no agent change, but the amount can drift if the rulebook version changes)?
3. **Reviewer identity format**: store the raw Entra `oid` GUID as `reviewer_id` (diverges from the contract's `^MOCK-[A-Z0-9-]{1,48}$` `actorId` pattern), or map to a pseudonymous `MOCK-REVIEWER-NNN` id?
4. **Reason codes**: does "reject" or "request revision" need to capture a `reasonCode` (`REVIEWED` / `REQUIRES_REVISION` / `TRAINING_PREVIEW`)? The repository has no parameter for it today — adding one changes the `approve`/`reject`/`revise` signatures and the `audit_events` schema.
5. **Revise semantics**: `revise()` reassigns `preparer_id` to the actor, permanently barring that actor from approving the new revision. Is a reviewer-initiated "request revision" supposed to do this, or should the reviewer app call `revise` with the *original preparer's* id?
6. **Auth model**: app role (`roles` claim) only, group membership only, or both? And a new scope value (e.g. `Review.Access`) or reuse `Chat.Access`?
7. **Bilingual requirement**: must the reviewer UI be en-CA/fr-CA? There is no existing frontend i18n pattern — this would be net-new.
8. **Same or separate Entra app registration** as the web-chat pilot? Sharing means one `clientId` with two roles; separating means a second run of `setup-web-chat-identity.ps1`-equivalent and a second SPA redirect URI.
9. **Deployment gating**: `infra/web-chat.bicep` and `azure.yaml` are marked AUTHOR-ONLY behind gates G2/G3/G6. Does the reviewer app's infra inherit the same "author and lint only, never apply" constraint?
10. **Should the existing `ApprovalRepository` be modified in place** (adding `list_by_state`), or should the reviewer app define a new interface? Modifying in place touches the vendored copy in `src/quote-preparation-agent/` that ships to the hosted agent container, which must stay byte-identical.

---

## Recommended Next Research (not completed)

- [ ] Read `mcp/application-server/main.py` and `mcp/rulebook-server/main.py` in full if the reviewer app must re-fetch applications/rulebooks to recompute premiums.
- [ ] Read `apps/workshop/calculator.py` lines 88-end (`_result`, `_resolve_rule_ids` helpers) if recompute-on-read is chosen.
- [ ] Read `eval/deterministic-tests/checks.py` and `eval/evaluation_gate.py` to see whether the reviewer app needs to participate in the deterministic evaluation gate.
- [ ] Read `.github/workflows/hosted-agent-cd.yml` and `deploy-and-evaluate.yml` for the image-build/digest-pinning pipeline the reviewer app would mirror.
- [ ] Read `infra/main.bicep` and `infra/modules/mcp-container-apps.bicep` for the shared Container Apps environment naming conventions if a Cosmos account must be added.
- [ ] Read `src/quote-preparation-agent/state.py` and `response_bridge.py` if the reviewer app needs to understand the agent's persisted state shape.
- [ ] Confirm whether `apps/workshop/tests/test_calculator.py` contains reusable assertions for premium amounts.
- [ ] Investigate Azure Cosmos DB Python SDK (`azure-cosmos`) ETag / `if_match` and transactional-batch APIs to validate the port design in section 1.14.
