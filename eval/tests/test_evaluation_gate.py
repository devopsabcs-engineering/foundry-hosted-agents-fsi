"""Tests for eval/evaluation_gate.py.

Proves the gate aggregates deterministic checks into a correct pass/fail
summary for the real golden dataset, and correctly reports a failure --
not a false pass -- when a record is deliberately corrupted.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(EVAL_DIR / "deterministic-tests"))

import checks  # noqa: E402
import evaluation_gate  # noqa: E402


def test_gate_passes_on_the_real_golden_dataset():
    dataset = checks.load_golden_dataset()

    report = evaluation_gate.evaluate(dataset)

    assert report["passed"] is True
    assert report["dataset_size"] == len(dataset)
    assert all(record["passed"] for record in report["records"])
    assert report["bilingual_parity"]["passed"] is True


def test_gate_reports_failure_not_a_false_pass_for_a_corrupted_record():
    dataset = checks.load_golden_dataset()
    corrupted = copy.deepcopy(dataset)
    for record in corrupted:
        if record["id"] == "biz-002-calc-sedan-ready":
            record["expected"]["amountCents"] = 1

    report = evaluation_gate.evaluate(corrupted)

    assert report["passed"] is False
    failing_record = next(record for record in report["records"] if record["id"] == "biz-002-calc-sedan-ready")
    assert failing_record["passed"] is False
    other_records = [record for record in report["records"] if record["id"] != "biz-002-calc-sedan-ready"]
    assert all(record["passed"] for record in other_records)
