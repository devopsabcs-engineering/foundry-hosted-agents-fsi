"""Score misses are advisory in release CI; missing or errored evidence is not."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from judge_gate import METRICS, validate_completion, validate_results  # noqa: E402


@pytest.fixture
def evidence():
    return (
        {"status": "completed", "result_counts": {"total": 1, "errored": 0, "skipped": 0}},
        [{"id": "item-1", "status": "completed", "results": [
            {"name": metric, "score": 1, "passed": False} for metric in METRICS
        ]}],
    )


def test_complete_low_scores_remain_distinct_from_strict_quality_failure(evidence):
    run, items = evidence
    assert validate_completion(run, items, 1) == dict.fromkeys(METRICS, 0.0)
    with pytest.raises(ValueError, match="Quality threshold"):
        validate_results(run, items, 1)


@pytest.mark.parametrize("mutation", [
    "failed-run", "errored-run", "skipped-run", "missing-item", "duplicate-item",
    "errored-item", "missing-metric", "errored-metric", "unscored-metric",
])
def test_advisory_validation_never_accepts_incomplete_or_errored_evidence(evidence, mutation):
    run, items = deepcopy(evidence)
    if mutation == "failed-run":
        run["status"] = "failed"
    elif mutation == "errored-run":
        run["result_counts"]["errored"] = 1
    elif mutation == "skipped-run":
        run["result_counts"]["skipped"] = 1
    elif mutation == "missing-item":
        items.clear()
    elif mutation == "duplicate-item":
        items.append(deepcopy(items[0]))
    elif mutation == "errored-item":
        items[0]["error"] = {"code": "failed"}
    elif mutation == "missing-metric":
        items[0]["results"].pop()
    elif mutation == "errored-metric":
        items[0]["results"][0]["status"] = "error"
    else:
        items[0]["results"][0]["score"] = None
    with pytest.raises(ValueError):
        validate_completion(run, items, 1)
