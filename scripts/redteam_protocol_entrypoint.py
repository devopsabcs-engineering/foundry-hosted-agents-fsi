"""Protocol-only entry point for a separately reviewed deterministic quote shadow.

This file is added to, never substituted for, the original immutable package.
Zero model tokens are accurate only for the pinned network-free default graph.
They exclude the red-team service's own model usage and all platform charges.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, AsyncIterable, AsyncIterator, Mapping

from azure.ai.agentserver.core.models import Response, ResponseStreamEvent
from azure.ai.agentserver.core.models import projects as project_models
from azure.ai.agentserver.langgraph._context import LanggraphRunContext

from response_bridge import QuotePreparationResponseConverter

SUPPORTED_GRAPH_SHA256 = "bd25b1e5c627802521ff178fa5bfea20e42d3a3d1063b1fe9357ed48c76a83ee"


def validate_runtime(graph_path: Path, environment: Mapping[str, str]) -> None:
    digest = hashlib.sha256(graph_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if digest != SUPPORTED_GRAPH_SHA256:
        raise ValueError("Zero-model-token protocol requires the reviewed deterministic graph")
    if environment.get("CASE_STORE_DB_PATH") != ":memory:" or any(
        name.startswith("COSMOS_") and value for name, value in environment.items()
    ):
        raise ValueError("Protocol correction requires private in-memory storage without Cosmos")


def model_usage() -> project_models.ResponseUsage:
    return project_models.ResponseUsage({
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
        "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
        "output_tokens_details": {"reasoning_tokens": 0},
    })


class DeterministicQuoteProtocolConverter(QuotePreparationResponseConverter):
    async def convert_response_non_stream(
        self, output: Any, context: LanggraphRunContext,
    ) -> Response:
        message = output.get("applicant_message") if isinstance(output, dict) else None
        if (
            not isinstance(message, dict) or set(message) != {"en-CA", "fr-CA"}
            or not all(isinstance(value, str) and value.strip() for value in message.values())
        ):
            raise ValueError("Protocol response requires a nonempty bounded bilingual message")
        response = (await super().convert_response_non_stream(output, context)).as_dict()
        response["output"][0]["content"][0]["text"] = json.dumps(message, ensure_ascii=False)
        response["status"] = "completed"
        response["usage"] = model_usage().as_dict()
        return Response(response)

    async def convert_response_stream(
        self, output: AsyncIterator[Any], context: LanggraphRunContext,
    ) -> AsyncIterable[ResponseStreamEvent]:
        async for event in super().convert_response_stream(output, context):
            if isinstance(event, project_models.ResponseCompletedEvent):
                event.response.usage = model_usage()
            yield event


def serve() -> None:
    from azure.ai.agentserver.langgraph import LangGraphAdapter

    import graph
    from case_telemetry import HostedTracing

    validate_runtime(Path(graph.__file__), os.environ)

    class ProtocolAdapter(HostedTracing, LangGraphAdapter):
        """Preserve the original payload-free telemetry pipeline."""

    adapter = ProtocolAdapter(
        graph.build_graph(model=graph.default_model),
        converter=DeterministicQuoteProtocolConverter(),
    )
    adapter.run(port=8088)


if __name__ == "__main__":
    serve()
