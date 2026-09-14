"""Deterministic (non-LLM) evaluation checks for the Desjardins quote-preparation workshop.

Adapted from the sibling `foundry-hosted-agents` repository's
`eval/deterministic-tests/checks.py`, but reworked for this workshop's
domain: instead of comparing a golden-dataset record's `expected` block
against a *precomputed* candidate-outputs.jsonl (as the sibling does for
LLM-generated report text), every check here *runs* the record directly
against this repository's real, deterministic code -- the Phase 2
calculator (`calculate_quote`), the Phase 3 `ApprovalRepository` state
machine, or the Phase 5 local LangGraph agent (`main.run_case`) -- because
none of those require an LLM judge to validate. This keeps the gate a
pure code-correctness check with no candidate-output fixture to keep in
sync.

Bilingual EN/FR pairing design choice: this golden dataset is a single
`eval/golden-dataset.jsonl` file where every record carries both an
`en-CA` and `fr-CA` "description" (mirroring how `data/synthetic/fixtures/
*.json` already pairs `notice`/`expectedDisplay` per record, rather than
maintaining a separate `notice`/`expectedDisplay` file), and every
`check_type: "agent"` record additionally asserts the produced
`applicant_message` carries both locale keys. This was chosen over two
separate `golden-dataset-en.jsonl`/`golden-dataset-fr.jsonl` files because
the sibling's own `golden-dataset.jsonl` is also a single file (it has no
French split at all); a single paired-field file keeps every business/
fault scenario's EN and FR expectations impossible to drift apart, per
research acceptance example V19 ("same canonical inputs... only localized
display changes").

Runnable via pytest (`eval/tests/test_checks.py`) or imported by
`eval/evaluation_gate.py` for the standalone CLI gate report.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "eval"
GOLDEN_DATASET_PATH = EVAL_DIR / "golden-dataset.jsonl"
FIXTURES_DIR = REPO_ROOT / "data" / "synthetic" / "fixtures"
DOCS_LABS_DIR = REPO_ROOT / "docs" / "labs"
DOCS_FR_LABS_DIR = REPO_ROOT / "docs" / "fr" / "labs"

APPS_WORKSHOP_DIR = REPO_ROOT / "apps" / "workshop"
AGENT_DIR = REPO_ROOT / "src" / "quote-preparation-agent"

for _dir in (APPS_WORKSHOP_DIR, AGENT_DIR):
    _path = str(_dir)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from approval_repository import ApprovalRepository, ApprovalRepositoryError  # noqa: E402
from calculator import calculate_quote  # noqa: E402

import main as agent_main  # noqa: E402

# Reviewer-only / rulebook-internal fields that must never leak into an
# applicant-facing message (mirrors src/quote-preparation-agent/tests/test_graph.py).
_DEFAULT_FORBIDDEN_MESSAGE_SUBSTRINGS = (
    "baseCents",
    "planAddOnCents",
    "WORKSHOP_AUTHORS_ONLY",
    "reviewerId",
    "actorId",
    "auditEvent",
)


@dataclass
class CheckResult:
    """Outcome of a single deterministic check against one golden-dataset record."""

    check_name: str
    passed: bool
    message: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of dicts, skipping blank lines."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_golden_dataset(path: Path = GOLDEN_DATASET_PATH) -> list[dict[str, Any]]:
    """Load the golden dataset as an ordered list of records."""
    return load_jsonl(path)


_FIXTURES_CACHE: dict[str, dict[str, Any]] | None = None


def _load_fixture(fixture_id: str) -> dict[str, Any]:
    """Load one data/synthetic/fixtures/*.json fixture by its fixtureId."""
    global _FIXTURES_CACHE
    if _FIXTURES_CACHE is None:
        _FIXTURES_CACHE = {}
        for path in sorted(FIXTURES_DIR.glob("*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            _FIXTURES_CACHE[fixture["fixtureId"]] = fixture
    try:
        return _FIXTURES_CACHE[fixture_id]
    except KeyError as exc:
        raise KeyError(f"No fixture found for fixtureId={fixture_id!r}") from exc


# ---------------------------------------------------------------------------
# Record runners: execute the real code under test and return an "actual"
# outcome dict, keyed by the record's own check_type.
# ---------------------------------------------------------------------------


def run_calculator_record(record: dict[str, Any]) -> dict[str, Any]:
    fixture = _load_fixture(record["fixture_id"])
    calculation = calculate_quote(fixture["input"], fixture["rulebook"])
    return {"calculation": calculation}


def run_agent_record(record: dict[str, Any]) -> dict[str, Any]:
    final_state = agent_main.run_case(record["case_id"], repository=ApprovalRepository(":memory:"))
    return {"final_state": final_state}


def _scenario_self_approval(repo: ApprovalRepository, record: dict[str, Any]) -> dict[str, Any]:
    """A preparer must never be able to approve (or reject) their own draft."""
    case_id = record["case_id"]
    preparer_id = record.get("preparer_id", "MOCK-CONTROLLER-001")
    repo.create_draft(case_id, preparer_id)
    repo.submit_for_review(case_id, preparer_id)
    return _attempt_and_snapshot(repo, case_id, lambda: repo.approve(case_id, preparer_id))


def _scenario_forged_actor(repo: ApprovalRepository, record: dict[str, Any]) -> dict[str, Any]:
    """Approving a case that was never submitted for review is an
    out-of-sequence, forged approval attempt bypassing the human-review
    queue entirely."""
    case_id = record["case_id"]
    preparer_id = record.get("preparer_id", "MOCK-CONTROLLER-001")
    reviewer_id = record.get("reviewer_id", "MOCK-REVIEWER-001")
    repo.create_draft(case_id, preparer_id)
    return _attempt_and_snapshot(repo, case_id, lambda: repo.approve(case_id, reviewer_id))


def _scenario_unauthorized_preview(repo: ApprovalRepository, record: dict[str, Any]) -> dict[str, Any]:
    """Opening a training preview before a case is approved must be denied
    by the state gate, regardless of who requests it."""
    case_id = record["case_id"]
    preparer_id = record.get("preparer_id", "MOCK-CONTROLLER-001")
    reviewer_id = record.get("reviewer_id", "MOCK-REVIEWER-001")
    repo.create_draft(case_id, preparer_id)
    repo.submit_for_review(case_id, preparer_id)
    return _attempt_and_snapshot(repo, case_id, lambda: repo.open_training_preview(case_id, reviewer_id))


def _scenario_revision_invalidation(repo: ApprovalRepository, record: dict[str, Any]) -> dict[str, Any]:
    """Revising an approved case must reset it to DRAFT and clear the
    prior approval; a stale preview attempt afterward must then be denied."""
    case_id = record["case_id"]
    preparer_id = record.get("preparer_id", "MOCK-CONTROLLER-001")
    reviewer_id = record.get("reviewer_id", "MOCK-REVIEWER-001")
    repo.create_draft(case_id, preparer_id)
    repo.submit_for_review(case_id, preparer_id)
    repo.approve(case_id, reviewer_id)
    repo.revise(case_id, preparer_id)
    # The stale OPEN_PREVIEW attempt below must not change the post-revise
    # snapshot recorded by _attempt_and_snapshot (it raises before any write).
    return _attempt_and_snapshot(repo, case_id, lambda: repo.open_training_preview(case_id, reviewer_id))


def _attempt_and_snapshot(repo: ApprovalRepository, case_id: str, attempt: Callable[[], Any]) -> dict[str, Any]:
    """Run `attempt`, capture the exception class name (or None), then
    return the case's resulting state snapshot."""
    raised: str | None = None
    try:
        attempt()
    except ApprovalRepositoryError as exc:
        raised = type(exc).__name__
    record = repo.get_case(case_id)
    return {
        "raised": raised,
        "final_state": record.state,
        "reviewer_id": record.reviewer_id,
        "approved_at": record.approved_at,
    }


_APPROVAL_SCENARIOS: dict[str, Callable[[ApprovalRepository, dict[str, Any]], dict[str, Any]]] = {
    "self_approval": _scenario_self_approval,
    "forged_actor": _scenario_forged_actor,
    "unauthorized_preview": _scenario_unauthorized_preview,
    "revision_invalidation": _scenario_revision_invalidation,
}


def run_approval_repository_record(record: dict[str, Any]) -> dict[str, Any]:
    scenario_name = record["scenario"]
    try:
        scenario_fn = _APPROVAL_SCENARIOS[scenario_name]
    except KeyError as exc:
        raise ValueError(f"Unknown approval_repository scenario: {scenario_name!r}") from exc
    repo = ApprovalRepository(":memory:")
    try:
        return scenario_fn(repo, record)
    finally:
        repo.close()


def run_record(record: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one golden-dataset record to its check_type's runner."""
    check_type = record["check_type"]
    if check_type == "calculator":
        return run_calculator_record(record)
    if check_type == "agent":
        return run_agent_record(record)
    if check_type == "approval_repository":
        return run_approval_repository_record(record)
    raise ValueError(f"Unknown check_type: {check_type!r}")


# ---------------------------------------------------------------------------
# Per-record deterministic checks. Each returns None when not applicable to
# the record's check_type (so run_checks_for_record can skip it cleanly).
# ---------------------------------------------------------------------------


def _calculation_from(record: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any] | None:
    if record["check_type"] == "calculator":
        return actual["calculation"]
    if record["check_type"] == "agent":
        return (actual.get("final_state") or {}).get("calculation")
    return None


def check_arithmetic_correctness(record: dict[str, Any], actual: dict[str, Any]) -> CheckResult | None:
    """Calculator/agent output must match the expected status, amount, and
    issue codes exactly -- no partial credit for a close-enough amount."""
    if record["check_type"] not in ("calculator", "agent"):
        return None
    expected = record["expected"]
    expected_status = expected.get("status") or expected.get("calculation_status")
    if expected_status is None:
        return None  # This record has no calculation to compare (e.g. an invalid case reference).

    calculation = _calculation_from(record, actual)
    if calculation is None:
        return CheckResult("arithmetic_correctness", False, "Expected a calculation but none was produced.")

    expected_amount = expected.get("amountCents", expected.get("amount_cents"))
    problems = []
    if calculation["status"] != expected_status:
        problems.append(f"expected status={expected_status!r}, got {calculation['status']!r}")
    if calculation["amountCents"] != expected_amount:
        problems.append(f"expected amountCents={expected_amount!r}, got {calculation['amountCents']!r}")
    expected_issues = expected.get("issues")
    if expected_issues is not None and set(calculation.get("issues", [])) != set(expected_issues):
        problems.append(f"expected issues={expected_issues!r}, got {calculation.get('issues')!r}")

    if problems:
        return CheckResult("arithmetic_correctness", False, "; ".join(problems))
    return CheckResult("arithmetic_correctness", True, "Calculation exactly matches the expected status/amount/issues.")


def check_no_invented_amount(record: dict[str, Any], actual: dict[str, Any]) -> CheckResult | None:
    """A calculation must never carry an amount unless status is READY,
    and a READY calculation must always carry one."""
    if record["check_type"] not in ("calculator", "agent"):
        return None
    calculation = _calculation_from(record, actual)
    if calculation is None:
        return None  # No calculation was produced for this record; nothing to check here.

    if calculation["status"] != "READY" and calculation["amountCents"] is not None:
        return CheckResult(
            "no_invented_amount", False,
            f"status={calculation['status']!r} but amountCents={calculation['amountCents']!r} (must be null)",
        )
    if calculation["status"] == "READY" and calculation["amountCents"] is None:
        return CheckResult("no_invented_amount", False, "status=READY but amountCents is null")
    return CheckResult("no_invented_amount", True, "amountCents is populated only when status is READY.")


def check_agent_output_shape(record: dict[str, Any], actual: dict[str, Any]) -> CheckResult | None:
    """Agent-level checks: issue_code/workflow_state match expectations, and
    the bounded applicant_message carries both locales with no leaked
    rulebook/reviewer-only fields."""
    if record["check_type"] != "agent":
        return None
    expected = record["expected"]
    final_state = actual["final_state"]
    problems = []

    if "issue_code" in expected and final_state.get("issue_code") != expected["issue_code"]:
        problems.append(f"expected issue_code={expected['issue_code']!r}, got {final_state.get('issue_code')!r}")
    if "workflow_state" in expected and final_state.get("workflow_state") != expected["workflow_state"]:
        problems.append(
            f"expected workflow_state={expected['workflow_state']!r}, got {final_state.get('workflow_state')!r}"
        )

    applicant_message = final_state.get("applicant_message") or {}
    expected_locales = expected.get("applicant_message_locales")
    if expected_locales and set(applicant_message) != set(expected_locales):
        problems.append(f"expected applicant_message locales={expected_locales!r}, got {list(applicant_message)!r}")

    forbidden = expected.get("forbidden_substrings", _DEFAULT_FORBIDDEN_MESSAGE_SUBSTRINGS)
    combined = " ".join(applicant_message.values())
    found = [substring for substring in forbidden if substring in combined]
    if found:
        problems.append(f"applicant_message leaked forbidden substring(s): {found}")

    if problems:
        return CheckResult("agent_output_shape", False, "; ".join(problems))
    return CheckResult(
        "agent_output_shape", True, "Agent output shape matches expectations (issue/state/bounded bilingual message)."
    )


def check_approval_gate_integrity(record: dict[str, Any], actual: dict[str, Any]) -> CheckResult | None:
    """Approval-repository scenarios must raise the expected exception (or
    none) and leave the case in the expected state, with reviewer/approval
    fields cleared when the record expects them to be."""
    if record["check_type"] != "approval_repository":
        return None
    expected = record["expected"]
    problems = []

    if actual["raised"] != expected.get("raises"):
        problems.append(f"expected raises={expected.get('raises')!r}, got {actual['raised']!r}")
    if "final_state" in expected and actual["final_state"] != expected["final_state"]:
        problems.append(f"expected final_state={expected['final_state']!r}, got {actual['final_state']!r}")
    if expected.get("reviewer_cleared") and actual["reviewer_id"] is not None:
        problems.append(f"expected reviewer_id to be cleared, but it was {actual['reviewer_id']!r}")
    if expected.get("approved_at_cleared") and actual["approved_at"] is not None:
        problems.append(f"expected approved_at to be cleared, but it was {actual['approved_at']!r}")

    if problems:
        return CheckResult("approval_gate_integrity", False, "; ".join(problems))
    return CheckResult("approval_gate_integrity", True, "Approval-gate state matches expectations.")


ALL_PER_RECORD_CHECKS: tuple[Callable[[dict[str, Any], dict[str, Any]], CheckResult | None], ...] = (
    check_arithmetic_correctness,
    check_no_invented_amount,
    check_agent_output_shape,
    check_approval_gate_integrity,
)


def run_checks_for_record(record: dict[str, Any]) -> list[CheckResult]:
    """Run the record against the real code under test, then apply every
    applicable deterministic check and return the (non-skipped) results."""
    actual = run_record(record)
    results = []
    for check in ALL_PER_RECORD_CHECKS:
        result = check(record, actual)
        if result is not None:
            results.append(result)
    return results


def check_bilingual_parity(dataset: list[dict[str, Any]]) -> CheckResult:
    """Dataset-level (not per-record) bilingual-parity check.

    Preferred check: once Phase 6 has landed, docs/labs/ and docs/fr/labs/
    must contain exactly the same file names. Phase 6 runs in parallel with
    this phase and is not guaranteed to have landed yet, so this check
    falls back to confirming this golden dataset's own paired-EN/FR design:
    every record's "description" must carry non-empty en-CA and fr-CA text
    (see the module docstring for why a single paired-field file was chosen
    over separate EN/FR golden-dataset files).
    """
    if DOCS_LABS_DIR.is_dir() and DOCS_FR_LABS_DIR.is_dir():
        en_names = sorted(path.name for path in DOCS_LABS_DIR.glob("*.md"))
        fr_names = sorted(path.name for path in DOCS_FR_LABS_DIR.glob("*.md"))
        if en_names != fr_names:
            return CheckResult(
                "bilingual_parity", False,
                f"docs/labs and docs/fr/labs file names differ: {en_names!r} != {fr_names!r}",
            )
        return CheckResult(
            "bilingual_parity", True,
            f"docs/labs and docs/fr/labs have matching file names ({len(en_names)} each).",
        )

    missing = [
        record["id"]
        for record in dataset
        if not (record.get("description", {}).get("en-CA") and record.get("description", {}).get("fr-CA"))
    ]
    if missing:
        return CheckResult(
            "bilingual_parity", False,
            f"docs/labs not found yet (Phase 6 pending); golden-dataset record(s) missing a "
            f"bilingual description: {missing}",
        )
    return CheckResult(
        "bilingual_parity", True,
        f"docs/labs not found yet (Phase 6 pending); all {len(dataset)} golden-dataset records "
        "carry paired en-CA/fr-CA descriptions.",
    )


__all__ = [
    "CheckResult",
    "load_jsonl",
    "load_golden_dataset",
    "run_record",
    "run_calculator_record",
    "run_agent_record",
    "run_approval_repository_record",
    "check_arithmetic_correctness",
    "check_no_invented_amount",
    "check_agent_output_shape",
    "check_approval_gate_integrity",
    "check_bilingual_parity",
    "ALL_PER_RECORD_CHECKS",
    "run_checks_for_record",
    "DOCS_LABS_DIR",
    "DOCS_FR_LABS_DIR",
]
