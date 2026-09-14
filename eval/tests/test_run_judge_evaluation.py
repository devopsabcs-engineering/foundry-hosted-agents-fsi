"""Tests for eval/run_judge_evaluation.py.

Proves `criteria()` produces the three correctly-shaped testing criteria,
proves `agent_instructions()` correctly extracts the real
`AGENT_TASK_INSTRUCTIONS` constant from `src/quote-preparation-agent/graph.py`
via AST parsing (against the real file, not mocked), and proves `main()`'s
guard exits 1 with the author-only message before any conditional import
of `azure.ai.projects` or any other side effect -- so an accidental local
invocation always fails fast and clearly, exactly as
eval/run_judge_evaluation.py's own module docstring and azure.yaml's
gating banner require.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def test_main_guard_exits_1_with_the_author_only_message(capsys):
    exit_code = rje.main(
        [
            "--endpoint", "https://example.services.ai.azure.com",
            "--agent", "quote-preparation-agent",
            "--version", "1",
            "--deployment", "gpt-4o-mini",
            "--dataset", "does-not-exist.json",
            "--output-dir", "does-not-exist-dir",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert rje.AUTHOR_ONLY_MESSAGE in captured.err
    assert "azure.ai.projects" not in sys.modules


def test_capture_raises_the_same_author_only_message():
    with pytest.raises(RuntimeError, match="AUTHOR-ONLY"):
        rje.capture([], None)
