"""Tests for scripts/ci_results.py.

Covers `junit_totals` against a small constructed JUnit fixture tree,
`deterministic_gate_totals` against a fixture matching the real
`eval/evaluation_gate.py` schema (both a valid and a missing-file case),
a `collect`/`publish_history` round trip proving merge-not-overwrite
semantics on republish, and `render_trends`'s no-judge-data fallback text.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import ci_results  # noqa: E402


def _write_junit(path: Path, cases: list[tuple[str, float, str | None]]) -> None:
    """Write a minimal JUnit XML file.

    Each case is `(name, duration_seconds, outcome)` where outcome is one
    of `None` (passed), `"failure"`, or `"skipped"`.
    """
    suite = ET.Element("testsuite")
    for name, duration, outcome in cases:
        case = ET.SubElement(suite, "testcase", name=name, time=str(duration))
        if outcome == "failure":
            ET.SubElement(case, "failure", message="boom")
        elif outcome == "skipped":
            ET.SubElement(case, "skipped")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="unicode")


def test_junit_totals_returns_none_for_empty_directory(tmp_path):
    assert ci_results.junit_totals(tmp_path) is None


def test_junit_totals_aggregates_counts_and_by_type(tmp_path):
    _write_junit(
        tmp_path / "agent.xml",
        [("test_a", 0.5, None), ("test_b", 0.25, "failure")],
    )
    _write_junit(tmp_path / "deterministic.xml", [("test_c", 0.1, "skipped")])
    _write_junit(tmp_path / "reporting.xml", [("test_d", 0.2, None)])

    totals = ci_results.junit_totals(tmp_path)

    assert totals["tests"] == 4
    assert totals["failed"] == 1
    assert totals["skipped"] == 1
    assert totals["passed"] == 2
    assert totals["seconds"] == 1.05
    assert totals["by_type"] == {
        "Agent graph": 2,
        "Deterministic evaluation": 1,
        "Reporting and contract tests": 1,
    }


def test_deterministic_gate_totals_reads_real_schema(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            {
                "dataset_size": 5,
                "records": [
                    {"id": "a", "passed": True},
                    {"id": "b", "passed": True},
                    {"id": "c", "passed": False},
                    {"id": "d", "passed": True},
                    {"id": "e", "passed": True},
                ],
                "bilingual_parity": {"name": "bilingual_parity", "passed": True, "message": "ok"},
                "passed": False,
            }
        ),
        encoding="utf-8",
    )

    totals = ci_results.deterministic_gate_totals(path)

    assert totals == {
        "dataset_size": 5,
        "passed_records": 4,
        "failed_records": 1,
        "bilingual_parity": True,
        "gate_passed": False,
    }


def test_deterministic_gate_totals_returns_none_when_file_missing(tmp_path):
    assert ci_results.deterministic_gate_totals(tmp_path / "does-not-exist.json") is None


def test_deterministic_gate_totals_returns_none_when_file_malformed(tmp_path):
    path = tmp_path / "results.json"
    path.write_text("{not valid json", encoding="utf-8")

    assert ci_results.deterministic_gate_totals(path) is None


def test_deterministic_gate_totals_returns_none_when_schema_is_wrong_shape(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")

    assert ci_results.deterministic_gate_totals(path) is None


def test_judge_totals_returns_none_when_absent(tmp_path):
    assert ci_results.judge_totals(tmp_path) is None


def _run_payload(run_id: int = 111, attempt: int = 1) -> dict:
    return {
        "id": run_id,
        "run_attempt": attempt,
        "run_number": 42,
        "name": "Continuous Validation",
        "head_sha": "abc123def456abc123def456abc123def456abc",
        "created_at": "2026-09-14T00:00:00Z",
        "conclusion": "success",
        "repository": {"full_name": "devopsabcs-engineering/foundry-hosted-agents-fsi"},
    }


def _jobs_payload() -> dict:
    return {
        "jobs": [
            {"name": "Offline regression tests", "conclusion": "success", "steps": []},
        ]
    }


def test_collect_and_publish_history_merge_on_republish(tmp_path):
    evidence = tmp_path / "evidence"
    offline = evidence / "offline-test-evidence"
    _write_junit(offline / "agent.xml", [("test_a", 0.1, None)])
    (offline / "results.json").write_text(
        json.dumps(
            {
                "dataset_size": 2,
                "records": [{"id": "a", "passed": True}, {"id": "b", "passed": True}],
                "bilingual_parity": {"name": "bilingual_parity", "passed": True, "message": "ok"},
                "passed": True,
            }
        ),
        encoding="utf-8",
    )

    wiki = tmp_path / "wiki"
    run = _run_payload()
    jobs = _jobs_payload()

    first = ci_results.collect(evidence, run, jobs)
    assert first["tests"]["tests"] == 1
    assert first["deterministic_gate"]["dataset_size"] == 2
    assert first["evaluation"] is None

    ci_results.publish_history(first, wiki)
    target = wiki / "trend-history" / "111-1.json"
    assert target.exists()
    saved_first = json.loads(target.read_text(encoding="utf-8"))
    assert saved_first["tests"]["tests"] == 1
    assert saved_first["deterministic_gate"]["dataset_size"] == 2

    # Republish the SAME (run_id, attempt) from a second, partial evidence
    # directory (simulates a later job in the same run publishing before
    # test/gate evidence has landed a second time) -- confirms the
    # previously-collected fields survive rather than being clobbered by
    # the new record's None values.
    empty_evidence = tmp_path / "evidence-empty"
    empty_evidence.mkdir()
    second = ci_results.collect(empty_evidence, run, jobs)
    assert second["tests"] is None
    assert second["deterministic_gate"] is None

    ci_results.publish_history(second, wiki)
    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged["tests"]["tests"] == 1
    assert merged["deterministic_gate"]["dataset_size"] == 2

    trends = (wiki / "Continuous-Test-Trends.md").read_text(encoding="utf-8")
    assert "No comparable evaluation lineage has been collected yet." in trends


def test_render_trends_fallback_when_no_judge_data():
    record = ci_results.collect(
        Path("/nonexistent-evidence-dir"), _run_payload(run_id=222, attempt=1), _jobs_payload()
    )

    trends = ci_results.render_trends([record])

    assert "No comparable evaluation lineage has been collected yet." in trends
    assert "## Deterministic Gate" in trends
    assert "## Evaluation Trends" in trends


def _judge_results_payload(item_outcomes: list[dict[str, bool]]) -> dict:
    """Build a `judge-results.json` fixture matching the real Azure AI
    Evaluation SDK run/item/result shape `judge_totals()`/`validate_results()`
    expect. `item_outcomes` is one dict of `{metric: passed}` per item.
    """
    items = []
    for index, outcomes in enumerate(item_outcomes):
        items.append(
            {
                "id": f"item-{index}",
                "status": "completed",
                "error": None,
                "sample": {},
                "results": [
                    {"name": metric, "score": 1.0 if passed else 0.0, "passed": passed, "status": "completed"}
                    for metric, passed in outcomes.items()
                ],
            }
        )
    return {
        "run": {
            "status": "completed",
            "error": None,
            "result_counts": {"total": len(items), "errored": 0, "skipped": 0},
        },
        "items": items,
    }


def test_render_trends_charts_judge_metrics_when_evidence_is_present(tmp_path):
    """This exercises the plumbing that stays dormant while
    `deploy-and-evaluate.yml`'s LLM-judge step is guarded (`if: false`):
    once real `judge-results.json`/`context.json` evidence exists,
    `render_trends` must chart coherence/groundedness/task_adherence
    rather than falling back to the "no lineage collected" placeholder.
    """
    evidence = tmp_path / "evidence"
    judge_dir = evidence / "evaluation-evidence"
    judge_dir.mkdir(parents=True)
    outcomes = [
        {"coherence": True, "groundedness": True, "task_adherence": False},
        {"coherence": True, "groundedness": False, "task_adherence": True},
        {"coherence": True, "groundedness": True, "task_adherence": True},
        {"coherence": False, "groundedness": True, "task_adherence": True},
    ]
    (judge_dir / "judge-results.json").write_text(
        json.dumps(_judge_results_payload(outcomes)), encoding="utf-8"
    )
    dataset_sha256 = "a" * 64
    evaluator_sha256 = "b" * 64
    (judge_dir / "context.json").write_text(
        json.dumps(
            {
                "environment": "staging",
                "agent_version": "3",
                "dataset_sha256": dataset_sha256,
                "evaluator_sha256": evaluator_sha256,
                "judge_deployment": "gpt-4o-mini",
                "version_after": "3",
            }
        ),
        encoding="utf-8",
    )

    record = ci_results.collect(evidence, _run_payload(run_id=333, attempt=1), _jobs_payload())

    assert record["evaluation"]["judge_rates"] == {
        "coherence": 0.75,
        "groundedness": 0.75,
        "task_adherence": 0.75,
    }

    trends = ci_results.render_trends([record])

    assert "No comparable evaluation lineage has been collected yet." not in trends
    assert f"Full dataset SHA-256: `{dataset_sha256}`." in trends
    for metric in ("coherence", "groundedness", "task_adherence"):
        assert f'title "{metric}"' in trends
        assert "bar [75.0]" in trends
