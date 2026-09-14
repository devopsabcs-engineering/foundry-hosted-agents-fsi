"""Local entry point for the quote-preparation LangGraph agent (Phase 5).

No Azure/Foundry SDK calls and no hosted-agent deployment code exist in
this module. `run_case` compiles and invokes the graph from graph.py
entirely in-process, against the Phase 4 MCP tool functions and the Phase
2/3 calculator and approval repository (see toolbox.py). Hosted deployment
(a Foundry Responses-protocol host server, matching the sibling's own
main.py) is out of scope until Gates G2/G3/G6 are cleared in a later phase.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph import DEFAULT_PREPARER_ID, DEFAULT_RULEBOOK_ID, ModelCallable, build_graph  # noqa: E402
from toolbox import ApprovalRepository  # noqa: E402


def run_case(
    case_id: str,
    *,
    preparer_id: Optional[str] = None,
    rulebook_id: Optional[str] = None,
    repository: Optional[ApprovalRepository] = None,
    model: Optional[ModelCallable] = None,
) -> dict[str, Any]:
    """Run the full intake -> reference-lookup -> composition graph for one case.

    Returns the compiled graph's final state as a plain dict, including the
    bounded `applicant_message` (never the raw rulebook or reviewer-only
    fields). `repository` and `model` are forwarded to `build_graph` so
    callers (including tests) can inject a spy repository or a stub model.
    """
    graph = build_graph(repository=repository, model=model)
    initial_state = {
        "case_id": case_id,
        "preparer_id": preparer_id or DEFAULT_PREPARER_ID,
        "rulebook_id": rulebook_id or DEFAULT_RULEBOOK_ID,
        "intake_complete": False,
        "lookup_complete": False,
        "composition_complete": False,
    }
    return graph.invoke(initial_state)


def _parse_case_input(raw: str) -> dict[str, Any]:
    """Accept either a bare case ID string or a JSON object with a caseId field."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"caseId": raw}
    if isinstance(payload, str):
        return {"caseId": payload}
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Unsupported case input: {raw!r}")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the quote-preparation agent locally against one case (no Azure/Foundry calls)."
    )
    parser.add_argument(
        "case_input",
        help='Case input: either a bare case ID (e.g. CASE-SYN-001) or a JSON object, e.g. \'{"caseId": "CASE-SYN-001"}\'.',
    )
    parser.add_argument("--preparer-id", default=None)
    parser.add_argument("--rulebook-id", default=None)
    args = parser.parse_args(argv)

    payload = _parse_case_input(args.case_input)
    case_id = payload.get("caseId") or payload.get("case_id") or ""
    preparer_id = payload.get("preparerId") or args.preparer_id
    rulebook_id = payload.get("rulebookId") or args.rulebook_id

    final_state = run_case(case_id, preparer_id=preparer_id, rulebook_id=rulebook_id)
    print(json.dumps(final_state.get("applicant_message"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
