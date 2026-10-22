"""Exercise the real original graph with a separate standards-compatible adapter."""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from openai.types.responses import Response as OpenAIResponse

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "src" / "quote-preparation-agent"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(ROOT / "scripts"))

import redteam_protocol_entrypoint as protocol  # noqa: E402
from graph import build_graph  # noqa: E402
from response_bridge import QuotePreparationResponseConverter  # noqa: E402
from sqlite_case_store import SqliteCaseStore  # noqa: E402

MESSAGE = {"en-CA": "Submitted for employee review.", "fr-CA": "Transmis pour revision."}


def context():
    return SimpleNamespace(agent_run=SimpleNamespace(
        response_id="resp-protocol-test", request={},
        id_generator=SimpleNamespace(generate_message_id=lambda: "msg-protocol-test"),
        get_agent_id_object=lambda: None, get_conversation_object=lambda: None,
    ))


def test_missing_usage_reproduces_the_actual_native_callback_failure():
    response = OpenAIResponse.model_construct(id="resp-original", output=[], status="completed")
    assert response.usage is None
    with pytest.raises(AttributeError, match="input_tokens"):
        response.usage.input_tokens


def test_nonstream_response_has_real_zero_model_usage_and_standard_string_content():
    state = {"applicant_message": MESSAGE, "premiumCents": 80000, "reviewerId": "PRIVATE"}
    converted = asyncio.run(protocol.DeterministicQuoteProtocolConverter().convert_response_non_stream(
        state, context(),
    )).as_dict()
    response = OpenAIResponse.model_validate(converted | {
        "model": "deterministic-quote-no-llm", "parallel_tool_calls": False,
        "tool_choice": "none", "tools": [],
    })
    assert response.usage.input_tokens == response.usage.output_tokens == response.usage.total_tokens == 0
    assert response.status == "completed"
    assert json.loads(response.output_text) == MESSAGE
    serialized = json.dumps(converted)
    assert "premiumCents" not in serialized and "80000" not in serialized and "PRIVATE" not in serialized
    assert state["applicant_message"] == MESSAGE


async def states(*values):
    for value in values:
        yield value


def test_stream_preserves_every_original_event_except_terminal_usage():
    async def collect(converter):
        return [event.as_dict() async for event in converter.convert_response_stream(
            states({"applicant_message": MESSAGE}), context(),
        )]

    before = asyncio.run(collect(QuotePreparationResponseConverter()))
    after = asyncio.run(collect(protocol.DeterministicQuoteProtocolConverter()))
    assert len(before) == len(after) == 9
    for original, corrected in zip(before, after):
        original.get("response", {}).pop("created_at", None)
        corrected.get("response", {}).pop("created_at", None)
        if corrected["type"] == "response.completed":
            assert corrected["response"].pop("usage") == protocol.model_usage().as_dict()
        assert corrected == original


@pytest.mark.parametrize("case_id", ["CASE-SYN-001", "CASE-SYN-003", "CASE-SYN-005", "NOT-A-CASE-ID"])
def test_protocol_uses_the_same_graph_and_identical_bounded_bilingual_acknowledgement(case_id):
    store = SqliteCaseStore()
    try:
        state = build_graph(repository=store).invoke({
            "case_id": case_id, "preparer_id": "AGENT-INTAKE", "rulebook_id": "",
            "intake_complete": False, "lookup_complete": False, "composition_complete": False,
        })
        before = asyncio.run(QuotePreparationResponseConverter().convert_response_non_stream(
            state, context(),
        )).as_dict()
        after = asyncio.run(protocol.DeterministicQuoteProtocolConverter().convert_response_non_stream(
            state, context(),
        )).as_dict()
        assert json.loads(after["output"][0]["content"][0]["text"]) == before["output"][0]["content"][0]["text"]
        assert after["usage"]["total_tokens"] == 0
    finally:
        store.close()


@pytest.mark.parametrize("message", [None, "", {}, {"en-CA": "Only English"}, {**MESSAGE, "private": "secret"}])
def test_protocol_rejects_invalid_nonstream_messages_without_success_shaped_fallback(message):
    with pytest.raises(ValueError, match="bounded bilingual"):
        asyncio.run(protocol.DeterministicQuoteProtocolConverter().convert_response_non_stream(
            {"applicant_message": message}, context(),
        ))


def test_runtime_requires_exact_deterministic_graph_and_private_storage(tmp_path):
    protocol.validate_runtime(AGENT / "graph.py", {"CASE_STORE_DB_PATH": ":memory:"})
    changed = tmp_path / "graph.py"
    changed.write_text("def default_model(prompt): return remote_llm(prompt)\n")
    with pytest.raises(ValueError, match="reviewed deterministic"):
        protocol.validate_runtime(changed, {"CASE_STORE_DB_PATH": ":memory:"})
    for environment in ({}, {"CASE_STORE_DB_PATH": "live.db"},
                        {"CASE_STORE_DB_PATH": ":memory:", "COSMOS_ENDPOINT": "live"}):
        with pytest.raises(ValueError, match="private in-memory"):
            protocol.validate_runtime(AGENT / "graph.py", environment)
