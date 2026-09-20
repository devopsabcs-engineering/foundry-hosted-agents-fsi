"""Delete case documents from the reviewer app's Cosmos DB case store.

The `cases` container has no delete operation on its `CaseStore` interface by
design (see `src/quote-preparation-agent/case_store.py`) -- the approval
workflow only ever creates, submits, and decides cases. Re-running the same
synthetic case (e.g. CASE-SYN-001) against a Cosmos-backed store therefore
hits `CaseAlreadyExistsError` on `create_draft`, because the case document
from the previous run is still there. This script is the operational escape
hatch for that: it talks to the Cosmos container directly, bypassing the
CaseStore abstraction entirely, so it must never be imported by application
code.

Authentication is Microsoft Entra only via `DefaultAzureCredential`, matching
`cosmos_case_store.CosmosCaseStore` -- the account has local auth (keys)
disabled, so no account-key parameter is accepted here either.

Defaults to a dry run that only lists what would be deleted. Pass --yes to
actually delete.

Usage:
    # List what's in the poc (production) case store without deleting anything
    python scripts/wipe_review_cases.py --endpoint https://cosmos-desjardins-quote-preparation-poc.documents.azure.com:443/

    # Actually delete every case in staging
    python scripts/wipe_review_cases.py --endpoint https://cosmos-desjardins-quote-preparation-staging.documents.azure.com:443/ --yes

    # Delete only specific cases (e.g. to re-seed just the ones you changed)
    python scripts/wipe_review_cases.py --endpoint ... --case-id CASE-SYN-001 --case-id CASE-SYN-003 --yes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_AGENT_SRC = REPOSITORY_ROOT / "src" / "quote-preparation-agent"
if str(_AGENT_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_SRC))

from case_store import COSMOS_CONTAINER_ID, COSMOS_DATABASE_ID  # noqa: E402


def _connect(endpoint: str, database: str, container: str):
    from azure.cosmos import CosmosClient
    from azure.identity import DefaultAzureCredential

    client = CosmosClient(endpoint, credential=DefaultAzureCredential())
    return client.get_database_client(database).get_container_client(container)


def _list_case_ids(container, case_ids: list[str] | None) -> list[str]:
    if case_ids:
        return list(case_ids)
    items = container.query_items(
        query="SELECT VALUE c.id FROM c",
        enable_cross_partition_query=True,
    )
    return list(items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Cosmos account endpoint, e.g. https://cosmos-desjardins-quote-preparation-poc.documents.azure.com:443/",
    )
    parser.add_argument("--database", default=COSMOS_DATABASE_ID, help=f"Default: {COSMOS_DATABASE_ID}")
    parser.add_argument("--container", default=COSMOS_CONTAINER_ID, help=f"Default: {COSMOS_CONTAINER_ID}")
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Delete only this case (repeatable). Omit to target every case in the container.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete. Without this flag, only lists what would be deleted.",
    )
    arguments = parser.parse_args(argv)

    container = _connect(arguments.endpoint, arguments.database, arguments.container)
    case_ids = _list_case_ids(container, arguments.case_ids)

    if not case_ids:
        print(f"No matching cases in {arguments.database}/{arguments.container} at {arguments.endpoint}.")
        return 0

    if not arguments.yes:
        print(f"Dry run -- would delete {len(case_ids)} case(s) from {arguments.database}/{arguments.container}:")
        for case_id in case_ids:
            print(f"  {case_id}")
        print("\nRe-run with --yes to actually delete.")
        return 0

    deleted = 0
    for case_id in case_ids:
        # Partition key path is /caseId and every document's id equals its caseId.
        container.delete_item(item=case_id, partition_key=case_id)
        deleted += 1
        print(f"deleted {case_id}")

    print(f"\nDeleted {deleted} case(s) from {arguments.database}/{arguments.container}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
