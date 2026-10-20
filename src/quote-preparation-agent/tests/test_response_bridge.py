"""Exercise the serialized native streaming contract without Azure calls."""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from response_bridge import QuotePreparationResponseConverter  # noqa: E402
from approval_repository import ApprovalRepository  # noqa: E402
from graph import build_graph  # noqa: E402
from sqlite_case_store import SqliteCaseStore  # noqa: E402


MESSAGE = {"en-CA": "Submitted for employee review.", "fr-CA": "Transmis pour révision."}


@pytest.mark.parametrize("extra", [
    {"corrections": {"plan": "TRAINING_BASIC"}}, {"preparerId": "FORGED"},
    {"rulebookId": "untrusted"},
])
def test_revision_input_cannot_inject_corrections_or_actor(extra):
    request_context = context()
    request_context.agent_run.request["input"] = json.dumps({
        "caseId": "CASE-SYN-005", "revision": 2, "preparationId": str(uuid.uuid4()), **extra,
    })
    with pytest.raises(ValueError):
        asyncio.run(QuotePreparationResponseConverter().convert_request(request_context))


def test_native_revision_request_runs_real_graph_and_serializes_only_bounded_output():
    store = SqliteCaseStore()
    try:
        graph = build_graph(repository=store)
        graph.invoke({"case_id": "CASE-SYN-005", "preparer_id": "AGENT-INTAKE",
                      "rulebook_id": "", "intake_complete": False,
                      "lookup_complete": False, "composition_complete": False})
        store.revise("CASE-SYN-005", "employee-correcting")
        key = str(uuid.uuid4())
        store.request_preparation("CASE-SYN-005", "employee-correcting", revision=2,
                                  request_id=key, corrections={"plan": "TRAINING_BASIC"})
        request_context = context()
        request_context.agent_run.request["input"] = json.dumps({
            "caseId": "CASE-SYN-005", "revision": 2, "preparationId": key,
        })
        converter = QuotePreparationResponseConverter()
        args = asyncio.run(converter.convert_request(request_context))
        result = graph.invoke(args["input"])
        response = asyncio.run(converter.convert_response_non_stream(result, request_context)).as_dict()
        assert response["object"] == "response"
        assert response["id"] == "resp-test"
        record, trail = store.get_case_with_audit("CASE-SYN-005")
        assert record.revision == 2 and record.state == "PENDING_REVIEW"
        assert record.amount_cents == 80000
        assert record.preparation.response_id == response["id"]
        assert trail[-1].details["responseId"] == response["id"]
        message = response["output"][0]["content"][0]["text"]
        assert set(message) == {"en-CA", "fr-CA"}
        serialized = json.dumps(response)
        for forbidden in (key, "employee-correcting", "80000", "TRAINING_BASIC", "auditTrail"):
            assert forbidden not in serialized
    finally:
        store.close()


def context():
    return SimpleNamespace(agent_run=SimpleNamespace(
        response_id="resp-test",
        request={"metadata": {"test": "bridge"}},
        id_generator=SimpleNamespace(generate_message_id=lambda: "msg-test"),
        get_agent_id_object=lambda: {"name": "quote-preparation-agent", "version": "3"},
        get_conversation_object=lambda: None,
    ))


async def states(*values):
    for value in values:
        yield value


def stream(*values):
    async def collect():
        return [event.as_dict() async for event in
                QuotePreparationResponseConverter().convert_response_stream(states(*values), context())]
    return asyncio.run(collect())


def test_stream_has_complete_ordered_text_events_and_only_terminal_bilingual_message():
    events = stream(
        {"applicant_message": {"en-CA": "INTERMEDIATE", "fr-CA": "INTERMEDIATE"},
         "baseCents": 80000},
        {"applicant_message": MESSAGE, "reviewerId": "PRIVATE", "premiumCents": 100000},
    )
    assert [event["type"] for event in events] == [
        "response.created", "response.in_progress", "response.output_item.added",
        "response.content_part.added", "response.output_text.delta",
        "response.output_text.done", "response.content_part.done",
        "response.output_item.done", "response.completed",
    ]
    assert [event["sequence_number"] for event in events] == list(range(len(events)))
    assert events[2]["item"]["status"] == "in_progress"
    assert events[2]["item"]["content"] == []
    assert events[3]["part"]["text"] == ""
    text = events[4]["delta"]
    assert isinstance(text, str)
    assert json.loads(text) == MESSAGE
    assert events[5]["text"] == text
    assert events[6]["part"]["text"] == text
    item = events[7]["item"]
    assert item["status"] == "completed"
    assert item["role"] == "assistant"
    assert item["content"][0]["text"] == text
    assert events[8]["response"]["output"] == [item]
    assert events[8]["response"]["status"] == "completed"
    for event in events:
        if "response" in event:
            assert event["response"]["id"] == "resp-test"
        if "item_id" in event:
            assert event["item_id"] == item["id"] == "msg-test"
            assert event["output_index"] == event["content_index"] == 0
    serialized = json.dumps(events, ensure_ascii=False)
    for forbidden in ("INTERMEDIATE", "PRIVATE", "baseCents", "premiumCents", "80000", "100000"):
        assert forbidden not in serialized


@pytest.mark.parametrize("value", [
    None, {}, {"applicant_message": ""}, {"applicant_message": "not bilingual"},
    {"applicant_message": {"en-CA": "Only one locale"}},
    {"applicant_message": {"en-CA": "", "fr-CA": "Texte"}},
    {"applicant_message": {"en-CA": "Text", "fr-CA": 7}},
    {"applicant_message": {**MESSAGE, "reviewerId": "PRIVATE"}},
])
def test_stream_rejects_invalid_terminal_message(value):
    with pytest.raises(ValueError, match="bilingual applicant message"):
        stream(value)


def test_empty_state_stream_fails_explicitly():
    with pytest.raises(ValueError, match="bilingual applicant message"):
        stream()


def test_stream_propagates_graph_failure():
    async def broken():
        yield {"applicant_message": MESSAGE}
        raise RuntimeError("graph failed")

    async def collect():
        return [event async for event in
                QuotePreparationResponseConverter().convert_response_stream(broken(), context())]

    with pytest.raises(RuntimeError, match="graph failed"):
        asyncio.run(collect())


def test_non_streaming_bilingual_map_contract_is_unchanged():
    response = asyncio.run(QuotePreparationResponseConverter().convert_response_non_stream(
        {"applicant_message": MESSAGE, "reviewerId": "PRIVATE"}, context()))
    serialized = response.as_dict()
    assert serialized["output"][0]["content"][0]["text"] == MESSAGE
    assert "PRIVATE" not in json.dumps(serialized)


@pytest.mark.parametrize("case_id", [
    "CASE-SYN-001", "CASE-SYN-003", "CASE-SYN-005", "NOT-A-CASE-ID",
])
def test_real_graph_terminal_message_matches_stream_and_non_stream(case_id):
    converter = QuotePreparationResponseConverter()
    request_context = context()
    request_context.agent_run.request["input"] = case_id
    arguments = asyncio.run(converter.convert_request(request_context))
    final = build_graph(repository=ApprovalRepository(":memory:"), model=lambda _: "stub").invoke(arguments["input"])
    events = stream(final)
    text = events[-1]["response"]["output"][0]["content"][0]["text"]
    non_stream = asyncio.run(
        QuotePreparationResponseConverter().convert_response_non_stream(final, context())
    ).as_dict()
    assert json.loads(text) == non_stream["output"][0]["content"][0]["text"]
    for forbidden in ("premiumCents", "reviewerId", "baseCents", "100000", "80000"):
        assert forbidden not in text
