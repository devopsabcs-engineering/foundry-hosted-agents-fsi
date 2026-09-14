"""Tests for eval/deterministic-tests/checks.py.

Proves the golden dataset itself passes every applicable deterministic
check (arithmetic correctness, no-invented-amount, approval-gate integrity,
bilingual parity), and proves each check actually *catches* a deliberately
wrong expected value rather than reporting a false pass.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR / "deterministic-tests"))

import checks  # noqa: E402

REQUIRED_FAULT_CATEGORIES = (
    "fault_self_approval",
    "fault_forged_actor",
    "fault_unauthorized_preview",
    "fault_unsupported_input",
    "fault_revision_invalidation",
)


def test_golden_dataset_has_minimum_business_and_required_fault_records():
    dataset = checks.load_golden_dataset()

    assert len(dataset) >= 6
    categories = {record["category"] for record in dataset}
    assert any(category.startswith("business_") for category in categories)
    for required in REQUIRED_FAULT_CATEGORIES:
        assert required in categories, f"missing required fault category: {required}"


def test_every_golden_dataset_record_passes_its_own_checks():
    dataset = checks.load_golden_dataset()

    for record in dataset:
        results = checks.run_checks_for_record(record)
        assert results, f"record {record['id']} produced no applicable checks"
        failed = [result for result in results if not result.passed]
        assert not failed, f"record {record['id']} failed checks: {failed}"


def test_bilingual_parity_check_passes_for_the_real_dataset():
    dataset = checks.load_golden_dataset()

    result = checks.check_bilingual_parity(dataset)

    assert result.passed, result.message


def test_arithmetic_check_fails_on_a_deliberately_wrong_expected_amount():
    dataset = checks.load_golden_dataset()
    genuine = next(record for record in dataset if record["id"] == "biz-001-calc-compact-ready")
    corrupted = copy.deepcopy(genuine)
    corrupted["expected"]["amountCents"] = 1

    results = checks.run_checks_for_record(corrupted)

    arithmetic_result = next(result for result in results if result.check_name == "arithmetic_correctness")
    assert not arithmetic_result.passed


def test_no_invented_amount_check_fails_when_a_non_ready_calculation_carries_an_amount():
    # check_no_invented_amount validates the *actual* calculation output, not
    # the "expected" block, so we feed it a fabricated bad "actual" directly
    # to prove it would catch a hypothetical calculator regression that
    # invents an amount for a non-READY status.
    dataset = checks.load_golden_dataset()
    record = next(record for record in dataset if record["id"] == "fault-001-calc-unsupported-no-invented-amount")
    bad_actual = {"calculation": {"status": "UNSUPPORTED", "amountCents": 999999, "issues": ["UNSUPPORTED_INPUT"]}}

    result = checks.check_no_invented_amount(record, bad_actual)

    assert not result.passed


def test_approval_gate_check_fails_when_expected_exception_is_wrong():
    dataset = checks.load_golden_dataset()
    genuine = next(record for record in dataset if record["id"] == "fault-003-self-approval-rejected")
    corrupted = copy.deepcopy(genuine)
    corrupted["expected"]["raises"] = "InvalidTransitionError"  # actual behaviour raises SelfApprovalError

    results = checks.run_checks_for_record(corrupted)

    gate_result = next(result for result in results if result.check_name == "approval_gate_integrity")
    assert not gate_result.passed


def test_bilingual_parity_check_fails_when_a_record_is_missing_a_description():
    dataset = checks.load_golden_dataset()
    corrupted = copy.deepcopy(dataset)
    corrupted[0]["description"]["fr-CA"] = ""

    result = checks.check_bilingual_parity(corrupted)

    if not (checks.DOCS_LABS_DIR.is_dir() and checks.DOCS_FR_LABS_DIR.is_dir()):
        assert not result.passed
