"""Assert that redeploying `infra/main.bicep` disturbs nothing already deployed.

Reads the JSON emitted by `az deployment group what-if --no-pretty-print` and
fails the run when a redeployment would remove or rewrite something that is
already there. Deterministic `guid()` role-assignment names and fixed resource
names are what let this hold; a template that derived names from a timestamp or
a fresh `newGuid()` would churn on every run and fail here.

Two modes:

* Single template (`--candidate` only). Fails on any `Delete`, and reports the
  `Modify`/`Create`/`NoChange`/`Ignore` breakdown.
* Differential (`--candidate` plus `--baseline`). Fails unless the candidate is
  the baseline plus `Create` entries only. This is the mode that proves a
  *change* to the template is additive: any resource the baseline left alone
  that the candidate now modifies, and any change type that differs from the
  baseline for the same resource, is a regression.

The differential mode exists because a blanket "zero Modify" assertion does not
hold against a live resource group. A what-if against
`rg-desjardins-quote-preparation` reports ten pre-existing `Modify` entries
regardless of this repository's changes -- Azure normalises properties that the
template does not set -- so the meaningful invariant is that the set does not
grow, not that it is empty.

Exit code 0 when the assertion holds, 1 when it does not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# A what-if entry for a resource outside the template's scope. Azure reports
# these for anything the deployment does not manage, so they carry no signal.
IGNORED_CHANGE_TYPES = frozenset({"Ignore", "NoChange", "NoEffect"})

DESTRUCTIVE_CHANGE_TYPES = frozenset({"Delete"})


def load_changes(path: Path) -> dict[str, str]:
    """Return `{resourceId: changeType}` from a what-if JSON payload.

    Accepts either the full `az deployment group what-if --no-pretty-print`
    object or a bare list of change entries.
    """
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    changes = payload.get("changes") if isinstance(payload, dict) else payload
    if not isinstance(changes, list):
        raise ValueError(f"{path.name} carries no what-if 'changes' array")

    resolved: dict[str, str] = {}
    for entry in changes:
        resource_id = entry.get("resourceId") or entry.get("resource_id")
        change_type = entry.get("changeType") or entry.get("change_type")
        if not resource_id or not change_type:
            raise ValueError(f"{path.name} has a change entry missing resourceId/changeType: {entry!r}")
        resolved[resource_id] = change_type
    return resolved


def summarise(changes: dict[str, str]) -> dict[str, int]:
    """Count resources per change type, highest count first."""
    counts: dict[str, int] = {}
    for change_type in changes.values():
        counts[change_type] = counts.get(change_type, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def destructive_changes(changes: dict[str, str]) -> list[str]:
    return sorted(
        resource_id
        for resource_id, change_type in changes.items()
        if change_type in DESTRUCTIVE_CHANGE_TYPES
    )


def regressions_against_baseline(
    baseline: dict[str, str], candidate: dict[str, str]
) -> list[str]:
    """Every way the candidate is not "the baseline plus Create entries"."""
    problems: list[str] = []

    for resource_id, change_type in sorted(candidate.items()):
        if change_type in IGNORED_CHANGE_TYPES:
            continue
        baseline_type = baseline.get(resource_id)
        if baseline_type == change_type:
            continue
        if change_type == "Create" and baseline_type in (None, *IGNORED_CHANGE_TYPES):
            continue  # A resource this template newly introduces.
        problems.append(
            f"{resource_id}: baseline={baseline_type or '<absent>'} candidate={change_type}"
        )

    for resource_id, change_type in sorted(baseline.items()):
        if change_type in IGNORED_CHANGE_TYPES:
            continue
        if resource_id not in candidate:
            problems.append(f"{resource_id}: baseline={change_type} candidate=<absent>")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="what-if JSON for the template under test",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="what-if JSON for the template before the change; enables the differential assertion",
    )
    args = parser.parse_args(argv)

    candidate = load_changes(args.candidate)
    print(f"candidate {args.candidate.name}: {summarise(candidate)}")

    failures: list[str] = []

    destructive = destructive_changes(candidate)
    if destructive:
        failures.append("redeployment would delete already-deployed resources:")
        failures.extend(f"  {resource_id}" for resource_id in destructive)

    if args.baseline is not None:
        baseline = load_changes(args.baseline)
        print(f"baseline  {args.baseline.name}: {summarise(baseline)}")
        problems = regressions_against_baseline(baseline, candidate)
        if problems:
            failures.append("candidate is not the baseline plus Create entries only:")
            failures.extend(f"  {problem}" for problem in problems)

    if failures:
        print("Bicep idempotency: FAIL", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1

    print("Bicep idempotency: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
