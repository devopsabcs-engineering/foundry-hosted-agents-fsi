"""LangGraph supervisor + specialist multi-agent graph for quote preparation.

Topology (adapted from the sibling threat-assessment-agent's graph.py):

    START -> supervisor -> {intake, reference_lookup, composition}
             ^__________________|___________________|_____________|
             (each specialist returns control to the supervisor)

`decide_next_step` is the supervisor's routing function. Unlike the
sibling's two independent specialists (evidence/risk) that can be thought
of as running before a shared composer, this domain's three stages are
inherently sequential: reference lookup needs a validated case reference
from intake, and composition needs the records reference lookup fetched.
The supervisor therefore routes intake -> reference_lookup -> composition
in a fixed order, except that an invalid case reference from intake skips
reference_lookup entirely and goes straight to composition (mirroring the
sibling's `safety_blocked` short-circuit in its own `decide_next_step`) so
composition can still produce a bounded rejection message.

The graph is always compiled without a checkpointer: this local/unhosted
phase has no Foundry Responses protocol and no hosted session to persist
across (see state.py).
"""

from __future__ import annotations

import re
from typing import Any, Callable, Literal, Optional

from langgraph.graph import END, START, StateGraph

import toolbox
from state import (
    STAGE_COMPOSITION,
    STAGE_INTAKE,
    STAGE_REFERENCE_LOOKUP,
    QuotePreparationState,
)

CASE_ID_PATTERN = re.compile(r"^CASE-SYN-[0-9]{3}$")
DEFAULT_RULEBOOK_ID = "RULEBOOK-SYN-ON"
DEFAULT_PREPARER_ID = "AGENT-INTAKE"

ISSUE_INVALID_CASE_ID = "INVALID_CASE_ID"
ISSUE_APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
ISSUE_RULEBOOK_NOT_FOUND = "RULEBOOK_NOT_FOUND"

# Eval-metadata only. Not wired into `default_model`, `build_graph`, or any
# executed code path in this phase. Extracted via AST parsing by
# `eval/run_judge_evaluation.py` to give task_adherence judging a real
# instructions text; does not change graph execution or require network
# access. Content is a plain-language restatement of this module's own
# topology description above -- not a live system prompt.
AGENT_TASK_INSTRUCTIONS = """\
You are the quote-preparation composition stage for a training-simulation \
insurance quote workflow. Given a validated case reference, you must:
1. Confirm the case reference matches the required CASE-SYN-### pattern; \
reject any unrecognized reference before any lookup occurs.
2. Look up the application input and the pinned rulebook for the case.
3. Run the calculator against the application input and rulebook to \
produce a bounded calculation result (READY, INCOMPLETE, UNSUPPORTED, or \
EVIDENCE_UNAVAILABLE) -- never invent an amount for a non-READY status.
4. Submit the resulting draft case for human employee review; never \
approve, reject, or revise a case yourself.
5. Compose a bounded, bilingual (en-CA/fr-CA) applicant-facing message \
using only the status template and the rulebook's own notice text -- \
never reveal an amount, raw rulebook fields, or any reviewer-only field.
"""

ModelCallable = Callable[[str], str]


def default_model(prompt: str) -> str:
    """Deterministic, network-free fallback model callable.

    Returns a fixed acknowledgement derived only from `prompt`'s own text
    (no external call), so building the graph with no injected `model`
    never requires network access, credentials, or a live LLM deployment.
    This is the seam the sibling fills with an Azure OpenAI/LangChain chat
    model; tests inject a stub callable here to prove it is swappable
    without ever making a network call in this phase.
    """
    return f"[offline-default-model] {prompt}"


_DEFAULT_NOTICE = {
    "en-CA": "Training simulation only. Not an insurance quote. No delivery.",
    "fr-CA": "Simulation de formation uniquement. Ceci n'est pas une soumission d'assurance. Aucun envoi.",
}

# Bounded, locale-paired applicant-facing templates. None of these ever
# reference an amount, the rulebook's baseCents/planAddOnCents/rules
# tables, or any reviewer-only case field (reviewerId, actorId, audit).
_STATUS_TEMPLATES: dict[str, dict[str, str]] = {
    "READY": {
        "en-CA": "Your request has been submitted for employee review. You will be notified once a decision is made.",
        "fr-CA": "Votre demande a ete soumise pour revision par un employe. Vous serez avise une fois la decision rendue.",
    },
    "INCOMPLETE": {
        "en-CA": "Your request is missing required information and has been submitted for employee review.",
        "fr-CA": "Votre demande est incomplete et a ete soumise pour revision par un employe.",
    },
    "UNSUPPORTED": {
        "en-CA": "Your request uses values outside the current training dataset and has been submitted for employee review.",
        "fr-CA": "Votre demande utilise des valeurs hors du jeu de donnees de formation actuel et a ete soumise pour revision par un employe.",
    },
    "EVIDENCE_UNAVAILABLE": {
        "en-CA": "We could not automatically retrieve the information needed for your request. It has been submitted for employee review.",
        "fr-CA": "Nous n'avons pas pu recuperer automatiquement les renseignements requis pour votre demande. Elle a ete soumise pour revision par un employe.",
    },
    "REJECTED_INTAKE": {
        "en-CA": "We could not process your request because the case reference was invalid. Please contact an employee for assistance.",
        "fr-CA": "Nous n'avons pas pu traiter votre demande, car la reference de dossier etait invalide. Veuillez communiquer avec un employe pour obtenir de l'aide.",
    },
}


def _bounded_message(status: str, notice: dict[str, str] | None) -> dict[str, str]:
    """Assemble the applicant-facing message: a status template plus the
    rulebook's own synthetic/non-binding notice (or a default if the
    rulebook was not available). Never includes an amount or raw rulebook
    fields -- only the status template text and the notice text."""
    template = _STATUS_TEMPLATES.get(status, _STATUS_TEMPLATES["EVIDENCE_UNAVAILABLE"])
    notice = notice or _DEFAULT_NOTICE
    return {locale: f"{template[locale]} {notice[locale]}" for locale in ("en-CA", "fr-CA")}


def _issue_only_calculation(issue_code: str) -> dict[str, Any]:
    """Build a calculation-shaped result for a failure that happens before
    the calculator can run at all (e.g. the application record itself was
    not found), so composition always has a single `calculation` shape to
    reason about instead of a separate error path."""
    return {
        "status": "EVIDENCE_UNAVAILABLE",
        "amountCents": None,
        "currency": None,
        "period": None,
        "ruleIds": [],
        "issues": [issue_code],
    }


def supervisor_node(state: QuotePreparationState) -> dict:
    """Pass-through node; routing decisions live in `decide_next_step`."""
    return {}


def decide_next_step(
    state: QuotePreparationState,
) -> Literal["intake", "reference_lookup", "composition", "__end__"]:
    """Route to the next specialist, or END once composition has completed.

    Reference lookup is only reached once intake has completed and found
    the case reference valid; an invalid case reference routes straight to
    composition so it can produce a bounded rejection message.
    """
    if not state.get("intake_complete"):
        return "intake"
    if state.get("intake_valid") and not state.get("lookup_complete"):
        return "reference_lookup"
    if not state.get("composition_complete"):
        return "composition"
    return END


def build_graph(
    *,
    repository: Optional["toolbox.ApprovalRepository"] = None,
    model: Optional[ModelCallable] = None,
):
    """Construct and compile the supervisor + specialist StateGraph.

    `repository` defaults to a fresh in-memory ApprovalRepository (suitable
    for a single local run or a test); pass one explicitly to share state
    across calls, or to inject a spy/mock that asserts approve/reject/
    revise are never called. `model` defaults to `default_model` (no
    network call); pass a stub or a real chat-model callable to swap it.
    """
    repository = repository if repository is not None else toolbox.ApprovalRepository()
    model = model or default_model

    def intake_node(state: QuotePreparationState) -> dict:
        """Validate/normalize the applicant-supplied case reference against
        the quote-contract's caseId pattern. Calls no MCP tool."""
        case_id = state.get("case_id") or ""
        valid = bool(CASE_ID_PATTERN.match(case_id))
        note = model(f"Confirm intake for case {case_id!r} (valid={valid}).")
        result: dict[str, Any] = {
            "stage": STAGE_INTAKE,
            "intake_complete": True,
            "intake_valid": valid,
            "intake_note": note,
        }
        if not valid:
            result["issue_code"] = ISSUE_INVALID_CASE_ID
        return result

    def reference_lookup_node(state: QuotePreparationState) -> dict:
        """Fetch the application input and the pinned rulebook via the
        Phase 4 MCP tool wrappers. Read-only; never writes anything."""
        case_id = state["case_id"]
        rulebook_id = state.get("rulebook_id") or DEFAULT_RULEBOOK_ID

        application = toolbox.get_application(case_id)
        rulebook = toolbox.get_rulebook(rulebook_id)

        issue_code = None
        if "error" in application:
            issue_code = ISSUE_APPLICATION_NOT_FOUND
            application = None
        if "error" in rulebook:
            issue_code = issue_code or ISSUE_RULEBOOK_NOT_FOUND
            rulebook = None

        result: dict[str, Any] = {
            "stage": STAGE_REFERENCE_LOOKUP,
            "lookup_complete": True,
            "application_record": application,
            "rulebook_record": rulebook,
        }
        if issue_code:
            result["issue_code"] = issue_code
        return result

    def composition_node(state: QuotePreparationState) -> dict:
        """Tool-free composer: run the calculator, create+submit a DRAFT
        case for human review, and assemble the bounded applicant message.

        Never calls approve/reject/revise on the repository -- only a human
        reviewer, through a separate reviewer-facing surface, may do that.
        """
        case_id = state["case_id"]
        preparer_id = state.get("preparer_id") or DEFAULT_PREPARER_ID

        if not state.get("intake_valid", False):
            message = _bounded_message("REJECTED_INTAKE", None)
            return {"stage": STAGE_COMPOSITION, "composition_complete": True, "applicant_message": message}

        application = state.get("application_record")
        rulebook = state.get("rulebook_record")

        if application is None:
            calculation = _issue_only_calculation(ISSUE_APPLICATION_NOT_FOUND)
        else:
            calculation = toolbox.calculate_quote(application.get("input"), rulebook)

        draft_case_id = None
        workflow_state = None
        try:
            draft = toolbox.create_draft(repository, case_id, preparer_id)
            draft_case_id = draft.case_id
            submitted = toolbox.submit_for_review(repository, case_id, preparer_id)
            workflow_state = submitted.state
        except toolbox.ApprovalRepositoryError:
            # Replayed run against an already-known case: surface the
            # existing state instead of failing the graph.
            try:
                existing = repository.get_case(case_id)
                draft_case_id = existing.case_id
                workflow_state = existing.state
            except toolbox.ApprovalRepositoryError:
                pass

        notice = rulebook.get("notice") if rulebook else None
        message = _bounded_message(calculation["status"], notice)

        result: dict[str, Any] = {
            "stage": STAGE_COMPOSITION,
            "composition_complete": True,
            "calculation": calculation,
            "draft_case_id": draft_case_id,
            "workflow_state": workflow_state,
            "applicant_message": message,
        }
        if calculation["issues"]:
            result["issue_code"] = calculation["issues"][0]
        return result

    workflow = StateGraph(QuotePreparationState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("intake", intake_node)
    workflow.add_node("reference_lookup", reference_lookup_node)
    workflow.add_node("composition", composition_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        decide_next_step,
        {
            "intake": "intake",
            "reference_lookup": "reference_lookup",
            "composition": "composition",
            END: END,
        },
    )
    workflow.add_edge("intake", "supervisor")
    workflow.add_edge("reference_lookup", "supervisor")
    workflow.add_edge("composition", "supervisor")

    return workflow.compile()
