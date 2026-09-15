"""Bridge between the Foundry Responses-protocol hosted-agent contract and
this project's case-driven LangGraph state schema.

`azure-ai-agentserver-langgraph`'s `from_langgraph()` ships a default
`ResponseAPIConverter` (see `azure.ai.agentserver.langgraph.models.
response_api_default_converter.ResponseAPIDefaultConverter`) that only
supports "MessagesState"-shaped graphs -- graphs whose state is a list of
chat messages in and out. This project's graph (`graph.py`/`state.py`) is a
single-shot case-processing pipeline keyed by `case_id`/`preparer_id`/
`rulebook_id`, not a chat loop, so `from_langgraph()` raises
`ValueError("converter is required for non-MessagesState graph.")` without
one. This module supplies that converter:

* `convert_request`: extracts the case ID (and optional preparer/rulebook
  IDs) from the incoming Responses-protocol request's plain-text `input`
  (reusing `case_input.parse_case_input`, the same parser the local CLI
  path uses) and builds the graph's initial state dict.
* `convert_response_non_stream`: takes the graph's final state (returned
  by `CompiledStateGraph.ainvoke`, per `LangGraphAdapter.agent_run_non_stream`)
  and wraps its bounded `applicant_message` as a single assistant output-text
  item -- never the raw rulebook or reviewer-only fields, matching
  `main.run_case`'s existing contract.

Streaming is intentionally not implemented: this graph runs to completion
in one shot (no incremental chat turns to stream), so
`convert_response_stream` raises rather than fabricating partial output.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterable, AsyncIterator, Union

from azure.ai.agentserver.core.models import Response, ResponseStreamEvent
from azure.ai.agentserver.core.models import projects as project_models
from azure.ai.agentserver.langgraph._context import LanggraphRunContext  # noqa: WPS436
from azure.ai.agentserver.langgraph.models.response_api_converter import (
    GraphInputArguments,
    ResponseAPIConverter,
)

from case_input import parse_case_input
from graph import DEFAULT_PREPARER_ID, DEFAULT_RULEBOOK_ID


def _extract_input_text(request: dict[str, Any]) -> str:
    """Extract the plain-text user message from a CreateResponse-shaped request payload."""
    raw_input = request.get("input")
    if isinstance(raw_input, str):
        return raw_input
    if isinstance(raw_input, list):
        for item in reversed(raw_input):
            content = item.get("content") if isinstance(item, dict) else None
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for part in content:
                    text = part.get("text") if isinstance(part, dict) else None
                    if text:
                        return text
    raise ValueError(f"Unsupported or empty Responses-protocol input: {raw_input!r}")


class QuotePreparationResponseConverter(ResponseAPIConverter):
    """Maps plain-text case requests to/from this project's case-processing graph state."""

    async def convert_request(self, context: LanggraphRunContext) -> GraphInputArguments:
        text = _extract_input_text(context.agent_run.request)
        payload = parse_case_input(text)
        case_id = payload.get("caseId") or payload.get("case_id") or ""
        initial_state = {
            "case_id": case_id,
            "preparer_id": payload.get("preparerId") or DEFAULT_PREPARER_ID,
            "rulebook_id": payload.get("rulebookId") or DEFAULT_RULEBOOK_ID,
            "intake_complete": False,
            "lookup_complete": False,
            "composition_complete": False,
        }
        return GraphInputArguments(
            input=initial_state,
            config={},
            context=context,
            stream_mode="values",
        )

    async def convert_response_non_stream(
        self, output: Union[dict[str, Any], Any], context: LanggraphRunContext
    ) -> Response:
        agent_run_context = context.agent_run
        applicant_message = output.get("applicant_message") if isinstance(output, dict) else None
        item = project_models.ResponsesAssistantMessageItemResource(
            content=[
                project_models.ItemContent(
                    {
                        "text": applicant_message or "",
                        "type": project_models.ItemContentType.OUTPUT_TEXT,
                        "annotations": [],
                    }
                )
            ],
            id=agent_run_context.id_generator.generate_message_id(),
            status="completed",
        )
        return Response(
            object="response",
            id=agent_run_context.response_id,
            agent=agent_run_context.get_agent_id_object(),
            conversation=agent_run_context.get_conversation_object(),
            metadata=agent_run_context.request.get("metadata"),
            created_at=int(time.time()),
            output=[item],
        )

    async def convert_response_stream(
        self,
        output: AsyncIterator[Union[dict[str, Any], Any]],
        context: LanggraphRunContext,
    ) -> AsyncIterable[ResponseStreamEvent]:
        """Emit a minimal valid event sequence for this graph's one-shot completion.

        This graph has no incremental chat turns to stream (it runs intake ->
        reference-lookup -> composition to completion in a single shot), so
        rather than translating LangGraph's per-superstep state values into
        token-level deltas, this drains the state stream to its final value
        and emits the minimal `created` -> `output_item.added` ->
        `output_item.done` -> `completed` event sequence the Responses
        protocol requires, all carrying the same bounded `applicant_message`
        `convert_response_non_stream` returns.
        """
        agent_run_context = context.agent_run
        final_state: Any = None
        async for state in output:
            final_state = state
        applicant_message = final_state.get("applicant_message") if isinstance(final_state, dict) else None

        agent_id = agent_run_context.get_agent_id_object()
        conversation = agent_run_context.get_conversation_object()

        item = project_models.ResponsesAssistantMessageItemResource(
            content=[
                project_models.ItemContent(
                    {
                        "text": applicant_message or "",
                        "type": project_models.ItemContentType.OUTPUT_TEXT,
                        "annotations": [],
                    }
                )
            ],
            id=agent_run_context.id_generator.generate_message_id(),
            status="completed",
        )

        def _response(status: str, response_output: list) -> Any:
            return project_models.Response(
                {
                    "object": "response",
                    "agent_id": agent_id,
                    "conversation": conversation,
                    "id": agent_run_context.response_id,
                    "status": status,
                    "created_at": int(time.time()),
                    "output": response_output,
                }
            )

        sequence_number = 0
        yield project_models.ResponseCreatedEvent(response=_response("in_progress", []), sequence_number=sequence_number)
        sequence_number += 1
        yield project_models.ResponseOutputItemAddedEvent(output_index=0, sequence_number=sequence_number, item=item)
        sequence_number += 1
        yield project_models.ResponseOutputItemDoneEvent(output_index=0, sequence_number=sequence_number, item=item)
        sequence_number += 1
        yield project_models.ResponseCompletedEvent(response=_response("completed", [item]), sequence_number=sequence_number)
