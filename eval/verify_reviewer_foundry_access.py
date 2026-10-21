"""Verify native invocation and memory denial using the deployed reviewer identity."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess

MARKER = "REVIEWER_FOUNDRY_ACCESS="
PROBE = """
import json, os, time, httpx
from azure.identity import ManagedIdentityCredential
endpoint = os.environ['AGENT_ENDPOINT']
with ManagedIdentityCredential(client_id=os.environ['AZURE_CLIENT_ID']) as credential:
    for attempt in range(12):
        token = credential.get_token('https://ai.azure.com/.default')
        headers = {'Authorization': 'Bearer ' + token.token}
        response = httpx.post(endpoint, headers=headers,
                              json={'input':'CASE-SYN-001','stream':False}, timeout=180)
        if response.status_code != 403 or attempt == 11:
            break
        time.sleep(45)
    response.raise_for_status()
    body = response.json()
    if (body.get('object') != 'response' or not body.get('id') or body.get('error')
            or body.get('status') not in (None, 'completed')):
        raise RuntimeError('Native reviewer invocation did not complete')
    project = endpoint.split('/agents/')[0]
    memory = httpx.post(project + '/memory_stores/showcase-synthetic-memory/items:list?api-version=v1',
                        headers=headers,
                        json={'scope':'showcase-synthetic-operator-alice-v1'}, timeout=30)
    print('REVIEWER_FOUNDRY_ACCESS=' + json.dumps({
        'invocationHttpStatus': response.status_code,
        'responseId': body['id'],
        'memoryHttpStatus': memory.status_code,
        'attempts': attempt + 1,
        'tokenLogged': False,
        'memoryModified': False,
    }))
"""


def validate_result(stdout: str) -> dict:
    results = [
        json.loads(line.split(MARKER, 1)[1])
        for line in stdout.splitlines() if MARKER in line
    ]
    if len(results) != 1:
        raise RuntimeError("Reviewer identity probe did not return exactly one result")
    result = results[0]
    if (
        not isinstance(result, dict)
        or result.get("invocationHttpStatus") != 200
        or not isinstance(result.get("responseId"), str) or not result["responseId"].strip()
        or result.get("memoryHttpStatus") != 403
        or result.get("tokenLogged") is not False
        or result.get("memoryModified") is not False
    ):
        raise RuntimeError("Reviewer identity must invoke the agent and remain denied memory access")
    return result


def verify_access(args) -> dict:
    cli = shutil.which("az")
    if cli is None:
        raise RuntimeError("Azure CLI is required for the reviewer workload identity probe")
    cli_python = Path(cli).parent.parent / "python.exe"
    prefix = (
        [str(cli_python), "-IBm", "azure.cli"]
        if cli.lower().endswith(".cmd") and cli_python.is_file() else [cli]
    )
    encoded = base64.b64encode(PROBE.encode()).decode()
    command = f"python -c \"exec(__import__('base64').b64decode('{encoded}'))\""
    try:
        completed = subprocess.run([
            *prefix, "containerapp", "exec", "--name", args.app,
            "--resource-group", args.resource_group, "--subscription", args.subscription,
            "--command", command,
        ], capture_output=True, text=True, check=True, timeout=1200)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Reviewer workload probe exited {exc.returncode}:\n{exc.stdout}\n{exc.stderr}"
        ) from exc
    result = validate_result(completed.stdout)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--output", type=Path)
    verify_access(parser.parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
