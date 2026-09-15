"""Tests for eval/run_judge_evaluation.py.

Proves `criteria()` produces the three correctly-shaped testing criteria,
proves `agent_instructions()` correctly extracts the real
`AGENT_TASK_INSTRUCTIONS` constant from `src/quote-preparation-agent/graph.py`
via AST parsing (against the real file, not mocked), proves
`_extract_response_text()` correctly selects the bilingual `applicant_message`
locale out of a Responses-protocol `output` list, and proves `main()` reads
the converted dataset's `data` list and drives `capture()`/`evaluate()`
(both stubbed here -- they require a real deployed hosted agent endpoint
and Azure AI Evaluation SDK credentials, which are exercised in the real
`azd`-deployed environment, not in this offline unit test).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

import run_judge_evaluation as rje  # noqa: E402


def test_criteria_produces_three_entries_with_expected_data_mapping():
    entries = rje.criteria("gpt-4o-mini")

    assert [entry["name"] for entry in entries] == ["coherence", "groundedness", "task_adherence"]
    for entry in entries:
        assert entry["type"] == "azure_ai_evaluator"
        assert entry["evaluator_name"] == f"builtin.{entry['name']}"
        assert entry["initialization_parameters"] == {"deployment_name": "gpt-4o-mini"}
        assert entry["data_mapping"]["context"] == "{{item.context}}"

    coherence, groundedness, task_adherence = entries
    assert coherence["data_mapping"]["query"] == "{{item.query}}"
    assert coherence["data_mapping"]["response"] == "{{item.response}}"
    assert groundedness["data_mapping"]["query"] == "{{item.query}}"
    assert groundedness["data_mapping"]["response"] == "{{item.response}}"
    assert task_adherence["data_mapping"]["query"] == "{{item.task_query}}"
    assert task_adherence["data_mapping"]["response"] == "{{item.output_items}}"


def test_agent_instructions_extracts_the_real_constant_from_graph_py():
    instructions = rje.agent_instructions()

    assert isinstance(instructions, str)
    assert instructions.strip()
    assert "quote-preparation composition stage" in instructions


def test_extract_response_text_selects_requested_locale():
    output_items = [
        {"content": [{"text": {"en-CA": "English text", "fr-CA": "Texte francais"}}]},
    ]
    assert rje._extract_response_text(output_items, locale="en-CA") == "English text"
    assert rje._extract_response_text(output_items, locale="fr-CA") == "Texte francais"


def test_extract_response_text_falls_back_when_locale_missing():
    output_items = [{"content": [{"text": {"fr-CA": "Texte francais"}}]}]
    assert rje._extract_response_text(output_items, locale="en-CA") == "Texte francais"


def test_extract_response_text_returns_empty_string_for_no_output():
    assert rje._extract_response_text([]) == ""


def test_normalize_output_items_flattens_bilingual_text_to_selected_locale():
    output_items = [{"content": [{"text": {"en-CA": "English", "fr-CA": "Francais"}, "type": "output_text"}]}]
    normalized = rje._normalize_output_items(output_items, locale="en-CA")
    assert normalized[0]["content"][0]["text"] == "English"
    # original is untouched
    assert isinstance(output_items[0]["content"][0]["text"], dict)


def test_main_reads_dataset_and_drives_capture_and_evaluate(tmp_path, monkeypatch):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps({"name": "d", "evaluators": [], "data": [{"id": "r1", "query": "q", "context": "c"}]}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    captured_call = {}
    evaluate_call = {}

    def fake_capture(records, args):
        captured_call["records"] = records
        captured_call["args"] = args
        return [{**records[0], "response": "r", "output_items": []}]

    def fake_evaluate(captured, args):
        evaluate_call["captured"] = captured
        evaluate_call["args"] = args

    monkeypatch.setattr(rje, "capture", fake_capture)
    monkeypatch.setattr(rje, "evaluate", fake_evaluate)

    exit_code = rje.main(
        [
            "--endpoint", "https://example.services.ai.azure.com/api/projects/proj",
            "--agent", "quote-preparation-agent",
            "--version", "1",
            "--deployment", "gpt-4o-mini",
            "--dataset", str(dataset_path),
            "--output-dir", str(output_dir),
        ]
    )

    assert exit_code == 0
    assert captured_call["records"] == [{"id": "r1", "query": "q", "context": "c"}]
    assert evaluate_call["captured"] == [{"id": "r1", "query": "q", "context": "c", "response": "r", "output_items": []}]
    assert output_dir.is_dir()
