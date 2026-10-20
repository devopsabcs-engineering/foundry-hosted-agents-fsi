"""Graph state schema for the quote-preparation LangGraph agent.

Mirrors the sibling threat-assessment-agent's TypedDict state contract
(../../../foundry-hosted-agents/src/threat-assessment-agent/state.py),
adapted from its evidence/risk/report specialist trio to this domain's
intake/reference-lookup/composition trio.

The native Responses host starts a fresh graph per request. Durable revisions
and audit events live in the shared case store, not a graph checkpointer.
"""

from __future__ import annotations

from typing import Any, Optional

from typing_extensions import NotRequired, TypedDict

STAGE_INTAKE = "INTAKE"
STAGE_REFERENCE_LOOKUP = "REFERENCE_LOOKUP"
STAGE_COMPOSITION = "COMPOSITION"


class QuotePreparationState(TypedDict):
    """State contract shared by the supervisor and specialist nodes."""

    # Inputs, supplied by main.py's run_case() and never modified by a node.
    case_id: str
    preparer_id: str
    rulebook_id: str
    preparation_id: NotRequired[str]
    preparation_revision: NotRequired[int]
    preparation_response_id: NotRequired[str]

    # Intake specialist output: validates/normalizes the case reference.
    stage: NotRequired[str]
    intake_complete: bool
    intake_valid: NotRequired[bool]
    intake_note: NotRequired[str]
    issue_code: NotRequired[Optional[str]]

    # Reference-lookup specialist output: fetches the Phase 4 MCP records.
    lookup_complete: bool
    application_record: NotRequired[Optional[dict[str, Any]]]
    rulebook_record: NotRequired[Optional[dict[str, Any]]]

    # Composition (tool-free) output: calculator result, draft case, and the
    # bounded applicant-facing message. Never carries reviewer-only fields.
    composition_complete: bool
    calculation: NotRequired[Optional[dict[str, Any]]]
    draft_case_id: NotRequired[Optional[str]]
    workflow_state: NotRequired[Optional[str]]
    applicant_message: NotRequired[Optional[dict[str, str]]]
