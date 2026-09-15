"""Pure deterministic calculator for the synthetic quote-preparation contract.

No I/O and no LLM calls. Given confirmed input fields (jurisdiction,
vehicleClass, plan) and a bound rulebook, computes an integer CAD-cent amount
or returns a specific issue code from the quote-contract schema's enum. This
function never invents an amount for a case it cannot resolve from the
rulebook's baseCents/planAddOnCents tables.

All monetary amounts are integer CAD cents. Every rulebook consumed here
carries an explicit "authority": "WORKSHOP_AUTHORS_ONLY" marker and is
synthetic training data, never a real insurance rate table.
"""

from __future__ import annotations

from typing import Any

STATUS_READY = "READY"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_UNSUPPORTED = "UNSUPPORTED"
STATUS_EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"

ISSUE_MISSING_JURISDICTION = "MISSING_JURISDICTION"
ISSUE_MISSING_VEHICLE_CLASS = "MISSING_VEHICLE_CLASS"
ISSUE_MISSING_PLAN = "MISSING_PLAN"
ISSUE_UNSUPPORTED_INPUT = "UNSUPPORTED_INPUT"
ISSUE_EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
ISSUE_RULE_VERSION_MISMATCH = "RULE_VERSION_MISMATCH"

SUPPORTED_JURISDICTION = "ON"
CURRENCY = "CAD"
PERIOD = "TRAINING_YEAR"

# Canonical rule-kind order used to resolve ruleIds, matching every fixture.
_RULE_KIND_ORDER = ("BASE_LOOKUP", "PLAN_LOOKUP", "EMPLOYEE_GATE")


def calculate_quote(
    input_data: dict[str, Any] | None,
    rulebook: dict[str, Any] | None,
    *,
    expected_rulebook_version: str | None = None,
) -> dict[str, Any]:
    """Compute the calculation object for a confirmed quote input.

    Returns a dict shaped like the quote-contract schema's `calculation`
    definition: status, amountCents, currency, period, ruleIds, issues.

    Precedence (matches the platform research): an unavailable rulebook is
    checked before anything else, then missing input fields, then
    out-of-dataset (unsupported) values. A READY result is only returned
    once jurisdiction, vehicleClass and plan all resolve against the bound
    rulebook's tables.
    """
    if rulebook is None:
        return _result(STATUS_EVIDENCE_UNAVAILABLE, issues=[ISSUE_EVIDENCE_UNAVAILABLE])

    if expected_rulebook_version is not None and rulebook.get("version") != expected_rulebook_version:
        return _result(STATUS_EVIDENCE_UNAVAILABLE, issues=[ISSUE_RULE_VERSION_MISMATCH])

    input_data = input_data or {}
    jurisdiction = input_data.get("jurisdiction")
    vehicle_class = input_data.get("vehicleClass")
    plan = input_data.get("plan")

    missing_issues = []
    if jurisdiction is None:
        missing_issues.append(ISSUE_MISSING_JURISDICTION)
    if vehicle_class is None:
        missing_issues.append(ISSUE_MISSING_VEHICLE_CLASS)
    if plan is None:
        missing_issues.append(ISSUE_MISSING_PLAN)
    if missing_issues:
        return _result(STATUS_INCOMPLETE, issues=missing_issues)

    base_cents = rulebook.get("baseCents", {})
    plan_add_on_cents = rulebook.get("planAddOnCents", {})

    if (
        jurisdiction != SUPPORTED_JURISDICTION
        or vehicle_class not in base_cents
        or plan not in plan_add_on_cents
    ):
        return _result(STATUS_UNSUPPORTED, issues=[ISSUE_UNSUPPORTED_INPUT])

    amount_cents = base_cents[vehicle_class] + plan_add_on_cents[plan]
    rule_ids = _resolve_rule_ids(rulebook.get("rules", []))
    return _result(STATUS_READY, amount_cents=amount_cents, rule_ids=rule_ids)


def _resolve_rule_ids(rules: list[dict[str, Any]]) -> list[str]:
    by_kind = {rule.get("kind"): rule.get("id") for rule in rules}
    return [by_kind[kind] for kind in _RULE_KIND_ORDER if kind in by_kind]


def _result(
    status: str,
    *,
    amount_cents: int | None = None,
    rule_ids: list[str] | None = None,
    issues: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "amountCents": amount_cents,
        "currency": CURRENCY,
        "period": PERIOD,
        "ruleIds": rule_ids or [],
        "issues": issues or [],
    }
