"""Seed a local SQLite case store with synthetic cases awaiting review.

The reviewer app renders whatever `list_cases_by_state('PENDING_REVIEW')`
returns. Reaching that state through the agent needs a live model endpoint,
which a workshop attendee working offline does not have, so this script walks
the same two store commands the agent's composition node walks -- `create_draft`
then `submit_for_review_with_calculation` -- against the real deterministic
calculator and the checked-in fixtures.

Every amount therefore comes from `calculate_quote` reading a fixture rulebook,
never from a literal in this file. The UNSUPPORTED and INCOMPLETE fixtures are
seeded alongside the READY ones on purpose: they are the cases that reach
PENDING_REVIEW with no amount at all, and a reviewer needs to see that the
surface renders them rather than assuming a number.

Usage:
    python scripts/seed_review_queue.py --db-path .local/reviewer-cases.db
"""

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPOSITORY_ROOT / "data" / "synthetic" / "fixtures"

for source_dir in (REPOSITORY_ROOT / "src" / "quote-preparation-agent", REPOSITORY_ROOT / "apps" / "workshop"):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from calculator import calculate_quote  # noqa: E402
from case_store import (  # noqa: E402
    CalculationSnapshot,
    CaseAlreadyExistsError,
    build_case_store,
)

PREPARER_ID = "AGENT-INTAKE"


def fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


def seed_case(store, fixture: dict) -> tuple[str, str, int | None]:
    """Create and submit one fixture, returning its id, status, and amount."""
    case_id = fixture["fixtureId"]
    rulebook = fixture.get("rulebook")
    calculation = calculate_quote(
        fixture.get("input"),
        rulebook,
        expected_rulebook_version=(rulebook or {}).get("version"),
    )
    snapshot = CalculationSnapshot.from_calculation(
        calculation, rulebook_version=(rulebook or {}).get("version")
    )
    store.create_draft(case_id, PREPARER_ID)
    record = store.submit_for_review_with_calculation(
        case_id, PREPARER_ID, calculation=snapshot
    )
    return record.case_id, record.calculation_status, record.amount_cents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        required=True,
        help="SQLite file the reviewer app will read via CASE_STORE_DB_PATH",
    )
    arguments = parser.parse_args(argv)

    db_path = Path(arguments.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # endpoint='' forces the SQLite branch even when COSMOS_ENDPOINT happens to
    # be exported in the shell, so seeding can never write to a cloud store.
    store = build_case_store(db_path=str(db_path), endpoint="")
    try:
        for path in fixture_paths():
            fixture = json.loads(path.read_text(encoding="utf-8"))
            try:
                case_id, status, amount_cents = seed_case(store, fixture)
            except CaseAlreadyExistsError:
                print(f"{fixture['fixtureId']}: already seeded, left untouched")
                continue
            amount = "no amount" if amount_cents is None else f"{amount_cents} cents"
            print(f"{case_id}: PENDING_REVIEW, calculation {status}, {amount}")
    finally:
        store.close()

    print(f"\nSeeded {db_path}. Start the reviewer app with CASE_STORE_DB_PATH set to it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
