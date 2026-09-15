"""Tests for scripts/assert_bicep_idempotent.py.

Encodes the live evidence recorded against `rg-desjardins-quote-preparation`:
ten pre-existing `Modify` entries plus three `NoChange`, and the reviewer-app
template adding `Create` entries on top of that identical set. Also proves the
assertion actually catches a template that would delete or newly rewrite a
deployed resource, rather than reporting a false pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import assert_bicep_idempotent  # noqa: E402

RG = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-desjardins-quote-preparation"

# Ten Modify plus three NoChange: the shape a what-if reports against the
# already-deployed staging group, with or without this feature's changes.
BASELINE_CHANGES = (
    [{"resourceId": f"{RG}/providers/Microsoft.App/containerApps/mcp-{index}", "changeType": "Modify"} for index in range(10)]
    + [{"resourceId": f"{RG}/providers/Microsoft.Insights/components/ai-{index}", "changeType": "NoChange"} for index in range(3)]
)

REVIEWER_ADDITIONS = [
    {"resourceId": f"{RG}/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-quote", "changeType": "Create"},
    {"resourceId": f"{RG}/providers/Microsoft.App/containerApps/reviewer-staging", "changeType": "Create"},
]


def _write(path: Path, changes: list[dict[str, str]]) -> Path:
    path.write_text(json.dumps({"changes": changes, "status": "Succeeded"}), encoding="utf-8")
    return path


def test_load_changes_accepts_a_bare_change_list(tmp_path):
    path = tmp_path / "bare.json"
    path.write_text(json.dumps(BASELINE_CHANGES), encoding="utf-8")

    changes = assert_bicep_idempotent.load_changes(path)

    assert len(changes) == 13


def test_load_changes_rejects_a_payload_without_changes(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"status": "Succeeded"}), encoding="utf-8")

    try:
        assert_bicep_idempotent.load_changes(path)
    except ValueError as exc:
        assert "changes" in str(exc)
    else:
        raise AssertionError("expected a ValueError for a payload with no changes array")


def test_summarise_counts_the_recorded_baseline_shape(tmp_path):
    changes = assert_bicep_idempotent.load_changes(_write(tmp_path / "baseline.json", BASELINE_CHANGES))

    assert assert_bicep_idempotent.summarise(changes) == {"Modify": 10, "NoChange": 3}


def test_reviewer_template_is_the_baseline_plus_create_entries_only(tmp_path):
    baseline = _write(tmp_path / "baseline.json", BASELINE_CHANGES)
    candidate = _write(tmp_path / "candidate.json", BASELINE_CHANGES + REVIEWER_ADDITIONS)

    exit_code = assert_bicep_idempotent.main(["--candidate", str(candidate), "--baseline", str(baseline)])

    assert exit_code == 0


def test_a_newly_modified_pre_existing_resource_fails_the_differential(tmp_path):
    baseline = _write(tmp_path / "baseline.json", BASELINE_CHANGES)
    drifted = [dict(change) for change in BASELINE_CHANGES]
    drifted[-1]["changeType"] = "Modify"  # A NoChange resource the candidate now rewrites.
    candidate = _write(tmp_path / "candidate.json", drifted + REVIEWER_ADDITIONS)

    exit_code = assert_bicep_idempotent.main(["--candidate", str(candidate), "--baseline", str(baseline)])

    assert exit_code == 1


def test_a_dropped_baseline_resource_fails_the_differential(tmp_path):
    baseline = _write(tmp_path / "baseline.json", BASELINE_CHANGES)
    candidate = _write(tmp_path / "candidate.json", BASELINE_CHANGES[1:])

    exit_code = assert_bicep_idempotent.main(["--candidate", str(candidate), "--baseline", str(baseline)])

    assert exit_code == 1


def test_a_delete_fails_even_without_a_baseline(tmp_path):
    candidate = _write(
        tmp_path / "candidate.json",
        BASELINE_CHANGES + [{"resourceId": f"{RG}/providers/Microsoft.App/containerApps/web-chat", "changeType": "Delete"}],
    )

    exit_code = assert_bicep_idempotent.main(["--candidate", str(candidate)])

    assert exit_code == 1


def test_the_recorded_live_shape_passes_the_single_template_mode(tmp_path):
    candidate = _write(tmp_path / "candidate.json", BASELINE_CHANGES + REVIEWER_ADDITIONS)

    exit_code = assert_bicep_idempotent.main(["--candidate", str(candidate)])

    assert exit_code == 0
