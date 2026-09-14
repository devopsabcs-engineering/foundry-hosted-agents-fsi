"""Deterministic evaluation gate for the Desjardins quote-preparation workshop.

Adapted from the sibling `foundry-hosted-agents` repository's
`eval/evaluation_gate.py`. The sibling's gate validates an *Azure AI
evaluation run's* result payload (LLM-judge scores, fail-closed on
incomplete/errored/unscored items) -- there is no LLM judge in this
workshop's Phase 2-5 slice. This gate instead loads the golden dataset
(eval/golden-dataset.jsonl), runs every record directly against the real
calculator/approval-repository/agent code via `deterministic-tests/checks.py`,
and aggregates the results into a single pass/fail gate summary: quality
judges cannot override an arithmetic or approval-gate failure here because
there are no quality judges in this deterministic gate at all.

Usage:
    python eval/evaluation_gate.py

Exits 0 when every record passes every applicable check and the dataset-
level bilingual-parity check also passes; exits 1 otherwise. Also writes a
machine-readable copy of the report to eval/results.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR / "deterministic-tests"))

from checks import (  # noqa: E402
    check_bilingual_parity,
    load_golden_dataset,
    run_checks_for_record,
)

RESULTS_PATH = EVAL_DIR / "results.json"


def evaluate(dataset: list[dict[str, Any]]) -> dict[str, Any]:
    """Run every deterministic check for every record, plus the one
    dataset-level bilingual-parity check, and return a structured gate
    report (never raises; failures are captured as `passed: False`)."""
    record_reports = []
    overall_passed = True

    for record in dataset:
        results = run_checks_for_record(record)
        passed = all(result.passed for result in results)
        overall_passed = overall_passed and passed
        record_reports.append(
            {
                "id": record["id"],
                "category": record.get("category"),
                "check_type": record.get("check_type"),
                "passed": passed,
                "checks": [
                    {"name": result.check_name, "passed": result.passed, "message": result.message}
                    for result in results
                ],
            }
        )

    bilingual_result = check_bilingual_parity(dataset)
    overall_passed = overall_passed and bilingual_result.passed

    return {
        "dataset_size": len(dataset),
        "records": record_reports,
        "bilingual_parity": {
            "name": bilingual_result.check_name,
            "passed": bilingual_result.passed,
            "message": bilingual_result.message,
        },
        "passed": overall_passed,
    }


def _print_report(report: dict[str, Any]) -> None:
    for record in report["records"]:
        status = "PASS" if record["passed"] else "FAIL"
        print(f"{status} {record['id']} (category={record['category']}, check_type={record['check_type']})")
        for check in record["checks"]:
            marker = "OK  " if check["passed"] else "FAIL"
            print(f"    [{marker}] {check['name']}: {check['message']}")

    bilingual = report["bilingual_parity"]
    marker = "OK  " if bilingual["passed"] else "FAIL"
    print(f"[{marker}] {bilingual['name']}: {bilingual['message']}")

    total = len(report["records"])
    passed = sum(1 for record in report["records"] if record["passed"])
    print(f"\n=== Summary: {passed}/{total} records passed; bilingual_parity={'PASS' if bilingual['passed'] else 'FAIL'} ===")
    print(f"Gate: {'PASS' if report['passed'] else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    dataset = load_golden_dataset()
    report = evaluate(dataset)
    _print_report(report)
    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
