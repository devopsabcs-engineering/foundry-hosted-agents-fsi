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

Streaming emits the final bounded bilingual map as JSON text with native
Responses text events. Intermediate workflow state is never streamed.
The existing non-streaming map contract is preserved.
"""

from __future__ import annotations

import json
import time
import uuid
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
        if "preparationId" in payload or "revision" in payload:
            if set(payload) != {"caseId", "revision", "preparationId"}:
                raise ValueError("Revision requests accept only the trusted case reference and request capability")
            revision, preparation_id = payload["revision"], payload["preparationId"]
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise ValueError("Invalid preparation revision")
            if not isinstance(preparation_id, str) or str(uuid.UUID(preparation_id)) != preparation_id:
                raise ValueError("Invalid preparation request capability")
            initial_state.update(
                preparation_id=preparation_id, preparation_revision=revision,
                preparation_response_id=context.agent_run.response_id,
            )
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
        """Emit one completed bilingual message, not incremental workflow state."""
        agent_run_context = context.agent_run
        final_state: Any = None
        async for state in output:
            final_state = state
        applicant_message = final_state.get("applicant_message") if isinstance(final_state, dict) else None
        if (
            not isinstance(applicant_message, dict)
            or set(applicant_message) != {"en-CA", "fr-CA"}
            or not all(isinstance(text, str) and text.strip() for text in applicant_message.values())
        ):
            raise ValueError("Streaming requires a nonempty bilingual applicant message")
        text = json.dumps(applicant_message, ensure_ascii=False)

        agent_id = agent_run_context.get_agent_id_object()
        conversation = agent_run_context.get_conversation_object()
        message_id = agent_run_context.id_generator.generate_message_id()
        created_at = int(time.time())
        part = project_models.ItemContent(
            {"text": text, "type": project_models.ItemContentType.OUTPUT_TEXT, "annotations": []}
        )
        item = project_models.ResponsesAssistantMessageItemResource(
            content=[part],
            id=message_id,
            status="completed",
        )

        def _response(
            status: str, response_output: list[project_models.ResponsesAssistantMessageItemResource]
        ) -> project_models.Response:
            return project_models.Response(
                {
                    "object": "response",
                    "agent_id": agent_id,
                    "conversation": conversation,
                    "id": agent_run_context.response_id,
                    "status": status,
                    "created_at": created_at,
                    "output": response_output,
                }
            )

        yield project_models.ResponseCreatedEvent(response=_response("in_progress", []), sequence_number=0)
        yield project_models.ResponseInProgressEvent(response=_response("in_progress", []), sequence_number=1)
        yield project_models.ResponseOutputItemAddedEvent(
            output_index=0, sequence_number=2,
            item=project_models.ResponsesAssistantMessageItemResource(
                content=[], id=message_id, status="in_progress",
            ),
        )
        yield project_models.ResponseContentPartAddedEvent(
            item_id=message_id, output_index=0, content_index=0, sequence_number=3,
            part=project_models.ItemContent(
                {"text": "", "type": project_models.ItemContentType.OUTPUT_TEXT, "annotations": []}
            ),
        )
        yield project_models.ResponseTextDeltaEvent(
            item_id=message_id, output_index=0, content_index=0, sequence_number=4, delta=text,
        )
        yield project_models.ResponseTextDoneEvent(
            item_id=message_id, output_index=0, content_index=0, sequence_number=5, text=text,
        )
        yield project_models.ResponseContentPartDoneEvent(
            item_id=message_id, output_index=0, content_index=0, sequence_number=6, part=part,
        )
        yield project_models.ResponseOutputItemDoneEvent(output_index=0, sequence_number=7, item=item)
        yield project_models.ResponseCompletedEvent(response=_response("completed", [item]), sequence_number=8)
