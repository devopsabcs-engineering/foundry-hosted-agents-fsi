"""Unit tests for the pure deterministic calculator.

Covers every synthetic fixture in data/synthetic/fixtures/, plus targeted
boundary cases for missing input, unsupported input, and unavailable
evidence. No network, LLM, or database access is used anywhere in this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# apps/workshop is not installed as a package; add it directly to sys.path so
# these tests run with a plain `pytest` invocation, regardless of whether the
# apps/ or apps/workshop/ directories are treated as packages by the runner.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculator import calculate_quote  # noqa: E402

import pytest  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "data" / "synthetic" / "fixtures"


def _load_fixtures() -> list[tuple[str, dict]]:
    return sorted(
        (
            (path.name, json.loads(path.read_text(encoding="utf-8")))
            for path in FIXTURES_DIR.glob("*.json")
        ),
        key=lambda item: item[0],
    )


FIXTURES = _load_fixtures()


def test_fixtures_directory_is_not_empty():
    assert FIXTURES, "expected at least one fixture in data/synthetic/fixtures/"


@pytest.mark.parametrize("name,fixture", FIXTURES, ids=[name for name, _ in FIXTURES])
def test_calculator_matches_expected_calculation_for_every_fixture(name, fixture):
    result = calculate_quote(fixture["input"], fixture["rulebook"])
    assert result == fixture["expectedCalculation"], f"mismatch for fixture {name}"


def test_case_syn_001_computes_to_exactly_100000_cents():
    fixture = next(fixture for _, fixture in FIXTURES if fixture["fixtureId"] == "CASE-SYN-001")
    result = calculate_quote(fixture["input"], fixture["rulebook"])
    assert result["status"] == "READY"
    assert result["amountCents"] == 100000
    assert result["currency"] == "CAD"
    assert result["period"] == "TRAINING_YEAR"


def test_unsupported_fixture_returns_issue_code_not_amount():
    fixture = next(
        fixture
        for _, fixture in FIXTURES
        if fixture["expectedCalculation"]["status"] == "UNSUPPORTED"
    )
    result = calculate_quote(fixture["input"], fixture["rulebook"])
    assert result["amountCents"] is None
    assert "UNSUPPORTED_INPUT" in result["issues"]


def test_missing_plan_fixture_returns_incomplete_with_issue_code_not_amount():
    fixture = next(
        fixture
        for _, fixture in FIXTURES
        if "MISSING_PLAN" in fixture["expectedCalculation"]["issues"]
    )
    result = calculate_quote(fixture["input"], fixture["rulebook"])
    assert result["status"] == "INCOMPLETE"
    assert result["amountCents"] is None
    assert "MISSING_PLAN" in result["issues"]


def test_revision_invalidation_fixture_is_no_longer_approved():
    fixture = next(fixture for _, fixture in FIXTURES if fixture["fixtureId"] == "CASE-SYN-004")
    assert fixture["workflow"]["state"] == "DRAFT"
    assert fixture["workflow"]["approvedRevision"] is None
    result = calculate_quote(fixture["input"], fixture["rulebook"])
    assert result["status"] == "READY"
    assert result["amountCents"] == 110000


def test_missing_evidence_never_invents_an_amount():
    result = calculate_quote(
        {"jurisdiction": "ON", "vehicleClass": "COMPACT", "plan": "TRAINING_BASIC"},
        rulebook=None,
    )
    assert result["status"] == "EVIDENCE_UNAVAILABLE"
    assert result["amountCents"] is None
    assert result["issues"] == ["EVIDENCE_UNAVAILABLE"]
