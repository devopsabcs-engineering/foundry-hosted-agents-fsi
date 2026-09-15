"""Entry point for the quote-preparation LangGraph agent (Phase 5).

`run_case` compiles and invokes the graph from graph.py entirely
in-process, against the Phase 4 MCP tool functions (in-process locally, or
over MCP-over-HTTP against the deployed Container Apps -- see toolbox.py)
and the Phase 2/3 calculator and approval repository.

Two entry modes, selected by whether a `case_input` positional argument is
given:

* Local/CLI (`python main.py CASE-SYN-001`): runs one case and prints its
  `applicant_message`, no Azure/Foundry SDK calls.
* Hosted (`python main.py`, no arguments -- exactly how the Foundry hosted
  agent runtime invokes this container's entry point per `azure.yaml`'s
  `codeConfiguration.entryPoint: main.py`): starts a Responses-protocol
  server (`azure-ai-agentserver-langgraph`, see `response_bridge.py`) that
  serves this same graph over the required `/readiness`/`/responses`
  hosted-agent contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_input import parse_case_input  # noqa: E402
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


def serve() -> None:
    """Start the hosted-agent Responses-protocol server (no case_input given).

    Wraps this project's compiled graph with `azure-ai-agentserver-langgraph`
    (see `response_bridge.py` for why a custom converter is required) and
    listens on port 8088, matching the Foundry hosted-agent runtime contract
    (`/readiness`, `/responses`) declared by `azure.yaml`'s
    `protocols: [{protocol: responses, version: 2.0.0}]`.
    """
    from azure.ai.agentserver.langgraph import from_langgraph  # noqa: E402

    from response_bridge import QuotePreparationResponseConverter  # noqa: E402

    graph = build_graph()
    adapter = from_langgraph(graph, converter=QuotePreparationResponseConverter())
    adapter.run(port=8088)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the quote-preparation agent locally against one case, or serve it as a hosted agent."
    )
    parser.add_argument(
        "case_input",
        nargs="?",
        default=None,
        help='Case input: either a bare case ID (e.g. CASE-SYN-001) or a JSON object, e.g. \'{"caseId": "CASE-SYN-001"}\'. Omit to start the hosted-agent server instead.',
    )
    parser.add_argument("--preparer-id", default=None)
    parser.add_argument("--rulebook-id", default=None)
    args = parser.parse_args(argv)

    if args.case_input is None:
        serve()
        return

    payload = parse_case_input(args.case_input)
    case_id = payload.get("caseId") or payload.get("case_id") or ""
    preparer_id = payload.get("preparerId") or args.preparer_id
    rulebook_id = payload.get("rulebookId") or args.rulebook_id

    final_state = run_case(case_id, preparer_id=preparer_id, rulebook_id=rulebook_id)
    print(json.dumps(final_state.get("applicant_message"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
