"""Restore the deployed agent's Cosmos grant, then verify a live synthetic case."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from run_judge_evaluation import capture


def missing_cosmos_grant(error: RuntimeError, account: str, principal: str) -> bool:
    message = str(error)
    return (
        f"Request blocked by Auth {account} :" in message
        and f"principal [{principal}]" in message
        and "does not have required RBAC permissions" in message
    )


def ensure_access(args) -> None:
    details = json.loads(args.agent_details.read_text(encoding="utf-8"))
    if details.get("name") != args.agent or details.get("status") != "active":
        raise ValueError("Expected the named, active hosted agent's deployment details")
    principal = str(UUID(details["instance_identity"]["principal_id"]))
    endpoint = details["definition"]["environment_variables"]["COSMOS_ENDPOINT"]
    if urlparse(endpoint).hostname != f"{args.cosmos_account}.documents.azure.com":
        raise ValueError("The deployed agent targets a different Cosmos account")

    records = [{"id": "post-deploy-cosmos-smoke", "query": "CASE-SYN-001"}]
    try:
        capture(records, args)
        print(f"Agent {args.agent} already has working Cosmos access ({principal}).", flush=True)
        return
    except RuntimeError as error:
        if not missing_cosmos_grant(error, args.cosmos_account, principal):
            raise
        # The first token request materializes a new Entra agent identity.
        print(f"Live Cosmos authorization confirmed {principal}; restoring its data grant.", flush=True)

    subprocess.run(
        [
            "az", "deployment", "group", "create",
            "--resource-group", args.resource_group,
            "--name", f"agent-cosmos-{principal[:8]}",
            "--template-file", str(Path(__file__).resolve().parents[1] / "infra" / "modules" / "cosmos-rbac.bicep"),
            "--parameters", f"accountName={args.cosmos_account}", f"principalIds={json.dumps([principal])}",
            "--output", "none",
        ],
        check=True,
    )
    for attempt in range(6):
        try:
            capture(records, args)
            print(f"Agent {args.agent} Cosmos access verified ({principal}).", flush=True)
            return
        except RuntimeError as error:
            if not missing_cosmos_grant(error, args.cosmos_account, principal) or attempt == 5:
                raise
            print("Waiting 20 seconds for Cosmos data-plane RBAC propagation.", flush=True)
            time.sleep(20)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--agent-details", required=True, type=Path)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--cosmos-account", required=True)
    ensure_access(parser.parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
