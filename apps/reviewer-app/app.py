"""Reviewer-facing approval surface for quote-preparation cases.

Structure mirrors `apps/web-chat/app.py`: a frozen `Settings` dataclass with
`from_env`, a `create_app(settings, verifier, store)` factory that takes every
external dependency as an injection seam, the same `security_headers`
middleware, and the same conditional static mount of `frontend/dist`.

This app talks to the case store directly and deliberately does not import
`toolbox.py`. `toolbox.py` refuses to expose `approve`, `reject`, and `revise`
to the agent on purpose, and `tests/test_toolbox.py` asserts that structurally.

Unlike the applicant surface, this one renders the calculated premium. The
amount is legitimately absent for cases whose calculation came back
UNSUPPORTED or INCOMPLETE and which still reached PENDING_REVIEW, so every
response models `amountCents` as nullable rather than defaulting it to zero.
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from auth import Identity, ReviewerAuth


def _agent_source_dir() -> Path | None:
    """Locate `src/quote-preparation-agent` in a source checkout.

    The container image copies the store modules next to this file, so they
    import directly and this returns None. Appending rather than inserting
    keeps the flat container copies authoritative and leaves the `sys.path`
    ordering that the agent test modules establish untouched.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src" / "quote-preparation-agent"
        if candidate.is_dir():
            return candidate
    return None


_AGENT_DIR = _agent_source_dir()
if _AGENT_DIR is not None and str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

from case_store import (  # noqa: E402
    STATE_PENDING_REVIEW,
    ApprovalRepositoryError,
    AuditRecord,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    CaseRecord,
    CaseStore,
    InvalidTransitionError,
    SelfApprovalError,
    build_case_store,
)

logger = logging.getLogger("reviewer_app")


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    reviewer_role: str = "Reviewer"
    reviewer_scope: str = "Review.Access"
    environment: str = "staging"
    queue_limit: int = 100

    @classmethod
    def from_env(cls):
        # The role is an appRole *value* string, never a GUID, so unlike the
        # web-chat group id it must not be passed through uuid.UUID().
        role = os.environ.get("REVIEWER_ROLE", "Reviewer").strip()
        scope = os.environ.get("REVIEWER_SCOPE", "Review.Access").strip()
        if not role or not scope:
            raise ValueError("REVIEWER_ROLE and REVIEWER_SCOPE must be non-empty")
        return cls(
            tenant_id=str(uuid.UUID(os.environ["ENTRA_TENANT_ID"])),
            client_id=str(uuid.UUID(os.environ["REVIEWER_CLIENT_ID"])),
            reviewer_role=role,
            reviewer_scope=scope,
            environment=os.environ.get("ENVIRONMENT", "staging").strip() or "staging",
        )


CASE_ID = PathParam(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._\-]+$")


class ApproveRequest(BaseModel):
    """`extra="forbid"` is what keeps `reasonCode` off the approve path."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    revision: int = Field(ge=1, le=1_000_000)


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)
    revision: int = Field(ge=1, le=1_000_000)
    reason_code: str | None = Field(
        default=None, alias="reasonCode", min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$"
    )


def case_payload(record: CaseRecord) -> dict:
    return {
        "caseId": record.case_id,
        "state": record.state,
        "revision": record.revision,
        "preparerId": record.preparer_id,
        "reviewerId": record.reviewer_id,
        "createdAt": record.created_at,
        "updatedAt": record.updated_at,
        "approvedAt": record.approved_at,
        "amountCents": record.amount_cents,
        "currency": record.currency,
        "period": record.period,
        "calculationStatus": record.calculation_status,
        "ruleIds": list(record.rule_ids),
        "issues": list(record.issues),
        "rulebookVersion": record.rulebook_version,
    }


def audit_payload(event: AuditRecord) -> dict:
    return {
        "sequence": event.sequence,
        "command": event.command,
        "fromState": event.from_state,
        "toState": event.to_state,
        "revision": event.revision,
        "actorId": event.actor_id,
        "at": event.at,
        "reasonCode": event.reason_code,
    }


def create_app(settings=None, verifier=None, store=None):
    settings = settings or Settings.from_env()
    verifier = verifier or ReviewerAuth(
        settings.tenant_id, settings.client_id, settings.reviewer_role, settings.reviewer_scope
    )

    @asynccontextmanager
    async def lifespan(application):
        application.state.store = store or build_case_store()
        yield
        if store is None:
            await asyncio.to_thread(application.state.store.close)

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    async def identity(authorization: str | None = Header(default=None)):
        return await verifier.authorize(authorization)

    def case_store() -> CaseStore:
        return application.state.store

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.headers.get("content-length", "").isdigit():
            if int(request.headers["content-length"]) > 8000:
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

    # SelfApprovalError is a sibling of InvalidTransitionError, not a subclass.
    # Registering only the latter would let self-approval escape as a 500.
    @application.exception_handler(CaseNotFoundError)
    async def case_not_found(request: Request, exc: CaseNotFoundError):
        return JSONResponse({"detail": "Case not found."}, status_code=404)

    @application.exception_handler(SelfApprovalError)
    async def self_approval(request: Request, exc: SelfApprovalError):
        # `auth.py` also raises 403 for an unauthorized app, a missing scope,
        # and a revoked role. The code is what lets the frontend tell those
        # apart, so it never tells a reviewer whose role was revoked that they
        # authored the case and hide the real remediation.
        return JSONResponse(
            {"detail": "You prepared this case and cannot decide it.", "code": "SELF_APPROVAL"},
            status_code=403,
        )

    @application.exception_handler(InvalidTransitionError)
    async def invalid_transition(request: Request, exc: InvalidTransitionError):
        return JSONResponse(
            {"detail": "This case changed since it was loaded. Reload and try again."},
            status_code=409,
        )

    @application.exception_handler(CaseAlreadyExistsError)
    async def already_exists(request: Request, exc: CaseAlreadyExistsError):
        return JSONResponse({"detail": "This case already exists."}, status_code=409)

    @application.exception_handler(ApprovalRepositoryError)
    async def repository_failure(request: Request, exc: ApprovalRepositoryError):
        logger.warning("case_store_failure type=%s", type(exc).__name__)
        return JSONResponse({"detail": "The case store is unavailable."}, status_code=500)

    @application.get("/healthz")
    async def health():
        return {"status": "ok"}

    @application.get("/api/config")
    async def config():
        return {
            "tenantId": settings.tenant_id,
            "clientId": settings.client_id,
            "scope": f"api://{settings.client_id}/{settings.reviewer_scope}",
            "role": settings.reviewer_role,
            "environment": settings.environment,
        }

    @application.get("/api/me")
    async def me(reviewer: Identity = Depends(identity)):
        return {"objectId": reviewer.object_id, "role": reviewer.role}

    @application.get("/api/cases")
    async def queue(reviewer: Identity = Depends(identity)):
        records = await asyncio.to_thread(
            case_store().list_cases_by_state, STATE_PENDING_REVIEW, settings.queue_limit
        )
        return {"cases": [case_payload(record) for record in records]}

    @application.get("/api/cases/{case_id}")
    async def detail(case_id: str = CASE_ID, reviewer: Identity = Depends(identity)):
        store_ = case_store()
        record = await asyncio.to_thread(store_.get_case, case_id)
        trail = await asyncio.to_thread(store_.get_audit_trail, case_id)
        return {"case": case_payload(record), "auditTrail": [audit_payload(e) for e in trail]}

    async def decide(command, case_id, body, reviewer, request_id):
        """Reject a stale revision before touching the store.

        The store's own compare-and-swap only guards against a writer that
        raced this request. A reviewer acting on a page rendered before an
        earlier decision would otherwise pass that guard and overwrite it, so
        the revision the reviewer actually saw is checked first.
        """
        store_ = case_store()
        current = await asyncio.to_thread(store_.get_case, case_id)
        if current.revision != body.revision:
            raise HTTPException(409, "This case changed since it was loaded. Reload and try again.")
        reason_code = getattr(body, "reason_code", None)
        record = await asyncio.to_thread(
            getattr(store_, command), case_id, reviewer.object_id, reason_code=reason_code
        )
        logger.warning(
            "reviewer_decision command=%s case=%s revision=%s reason=%s request=%s",
            command,
            case_id,
            body.revision,
            reason_code,
            request_id,
        )
        return {"case": case_payload(record)}

    def request_id(idempotency_key: str | None = Header(default=None, max_length=128)):
        return idempotency_key or str(uuid.uuid4())

    @application.post("/api/cases/{case_id}/approve")
    async def approve(
        body: ApproveRequest,
        case_id: str = CASE_ID,
        reviewer: Identity = Depends(identity),
        key: str = Depends(request_id),
    ):
        return await decide("approve", case_id, body, reviewer, key)

    @application.post("/api/cases/{case_id}/reject")
    async def reject(
        body: DecisionRequest,
        case_id: str = CASE_ID,
        reviewer: Identity = Depends(identity),
        key: str = Depends(request_id),
    ):
        return await decide("reject", case_id, body, reviewer, key)

    @application.post("/api/cases/{case_id}/revise")
    async def revise(
        body: DecisionRequest,
        case_id: str = CASE_ID,
        reviewer: Identity = Depends(identity),
        key: str = Depends(request_id),
    ):
        return await decide("revise", case_id, body, reviewer, key)

    dist = Path(__file__).parent / "frontend" / "dist"
    if dist.exists():
        application.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return application
