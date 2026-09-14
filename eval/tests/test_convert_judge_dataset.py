"""Tests for eval/convert_judge_dataset.py.

Proves the converter produces the expected `{"name", "evaluators", "data"}`
envelope for both locales against the real `eval/judge-dataset.jsonl`, and
proves it fails closed (raises `ValueError`) when a record is missing the
requested locale's query/context text or when an unsupported locale is
requested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

import convert_judge_dataset as cjd  # noqa: E402

JUDGE_DATASET_PATH = EVAL_DIR / "judge-dataset.jsonl"


def test_load_records_reads_every_line_of_the_real_judge_dataset():
    records = cjd.load_records(JUDGE_DATASET_PATH)

    assert 8 <= len(records) <= 12
    assert all("id" in record for record in records)


@pytest.mark.parametrize("locale", ["en-CA", "fr-CA"])
def test_convert_produces_expected_envelope_shape_for_each_locale(locale):
    records = cjd.load_records(JUDGE_DATASET_PATH)

    envelope = cjd.convert(records, locale)

    assert envelope["name"] == "quote-preparation-agent-judge-dataset"
    assert envelope["evaluators"] == [
        "builtin.coherence",
        "builtin.groundedness",
        "builtin.task_adherence",
    ]
    assert len(envelope["data"]) == len(records)
    for item in envelope["data"]:
        assert set(item) == {"id", "query", "context", "expected"}
        assert isinstance(item["query"], str) and item["query"]
        assert isinstance(item["context"], str) and item["context"]


def test_convert_rejects_unsupported_locale():
    records = cjd.load_records(JUDGE_DATASET_PATH)

    with pytest.raises(ValueError):
        cjd.convert(records, "de-DE")


def test_convert_fails_closed_when_a_record_is_missing_the_requested_locale():
    records = [
        {
            "id": "missing-fr",
            "query": {"en-CA": "Please prepare a quote."},
            "context": {"en-CA": "Please prepare a quote."},
            "expected": {"safety_refusal_text": None, "allow_safety_refusal": False},
        }
    ]

    with pytest.raises(ValueError):
        cjd.convert(records, "fr-CA")


def test_convert_fails_closed_when_context_is_missing_for_the_requested_locale():
    records = [
        {
            "id": "missing-context",
            "query": {"en-CA": "Please prepare a quote.", "fr-CA": "Veuillez preparer une soumission."},
            "context": {"en-CA": "Please prepare a quote."},
            "expected": {"safety_refusal_text": None, "allow_safety_refusal": False},
        }
    ]

    with pytest.raises(ValueError):
        cjd.convert(records, "fr-CA")
