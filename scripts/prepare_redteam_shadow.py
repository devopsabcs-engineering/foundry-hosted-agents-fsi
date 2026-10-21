"""Prepare, never deploy, a NEW isolated azd remote-build quote-agent version.

The resulting standalone azure.yaml has no infrastructure, models, connections,
toolbox creation, or hooks. Deployment and invocation require separate approval.
Native post-deployment preflight must observe the original immutable content_hash;
unchanged Git source alone does not prove reproducible azd packaging.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "eval"))

from native_showcase_evaluation import (  # noqa: E402
    SHADOW_ENVIRONMENT_KEYS,
    shadow_bounds,
    shadow_environment,
    write_json,
)


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()


def git_archive(revision: str, source: str) -> bytes:
    return subprocess.run(
        ["git", "archive", "--format=zip", revision, source],
        cwd=REPO_ROOT, check=True, capture_output=True,
    ).stdout


def prepare(args) -> dict:
    if args.allow_new_code_deployment is not True:
        raise ValueError("Explicit --allow-new-code-deployment is required; this only prepares local files")
    args.endpoint = args.staging_endpoint
    args.turns, args.agent_version = 1, None
    shadow_bounds(args)
    if not re.fullmatch(r"[0-9a-f]{64}", args.source_content_sha256):
        raise ValueError("Explicit expected native source-content-sha256 is required")
    output = args.output_dir.resolve()
    source = REPO_ROOT / "src" / "quote-preparation-agent"
    if output == REPO_ROOT or output.is_relative_to(source):
        raise ValueError("Preparation must not modify the baseline repository manifest or source")
    if not output.is_relative_to(REPO_ROOT / ".local"):
        raise ValueError("Use a fresh preparation directory under this repository's .local directory")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("output-dir must be new or empty")
    settings = {}
    for setting in args.runtime_setting:
        name, separator, value = setting.partition("=")
        if not separator or name not in SHADOW_ENVIRONMENT_KEYS or name in settings:
            raise ValueError("runtime-setting requires unique allowlisted non-secret NAME=VALUE entries")
        settings[name] = value
    environment = shadow_environment(settings, args.endpoint)
    if git("rev-parse", "--verify", args.source_revision + "^{commit}") != args.source_revision:
        raise ValueError("Approved full source commit is unavailable")
    relative_source = source.relative_to(REPO_ROOT).as_posix()
    if git("diff", "--name-only", args.source_revision, "--", relative_source):
        raise ValueError("Quote source differs from the approved deployment commit")
    tracked = set(git("ls-files", "--", relative_source).splitlines())
    if not tracked or not (source / "main.py").is_file():
        raise ValueError("Approved quote source is unavailable")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Source links require explicit packaging review")
        if path.is_file() and not {"__pycache__", ".pytest_cache"}.intersection(path.relative_to(source).parts):
            if path.relative_to(REPO_ROOT).as_posix() not in tracked:
                raise ValueError("Untracked source files require packaging review before upload")
    source_tree = git("rev-parse", args.source_revision + ":" + relative_source)
    snapshot = {}
    with zipfile.ZipFile(io.BytesIO(git_archive(args.source_revision, relative_source))) as archive:
        if len(archive.infolist()) > 1000 or sum(item.file_size for item in archive.infolist()) > 10_000_000:
            raise ValueError("Source archive exceeds the bounded initial shadow package")
        for item in archive.infolist():
            if item.is_dir():
                continue
            member = item.filename.removeprefix(relative_source + "/")
            relative = Path(member)
            windows_relative = PureWindowsPath(member)
            if (not item.filename.startswith(relative_source + "/") or relative.is_absolute()
                    or windows_relative.anchor or ".." in relative.parts or ".." in windows_relative.parts
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Source archive contains unreviewed paths or links")
            snapshot[relative] = archive.read(item)
    if not snapshot or Path("main.py") not in snapshot:
        raise ValueError("Approved source archive is incomplete")
    service = {
        "name": args.agent, "kind": "hosted", "host": "azure.ai.agent", "language": "python",
        "project": str(output / "source"), "uses": ["ai-project"],
        "codeConfiguration": {
            "dependencyResolution": "remote_build", "entryPoint": "main.py", "runtime": "python_3_13",
        },
        "container": {"resources": {"cpu": "0.5", "memory": "1Gi"}},
        "protocols": [{"protocol": "responses", "version": "2.0.0"}],
        "environmentVariables": [
            {"name": key, "value": "${SHADOW_" + key + "}"} if key != "CASE_STORE_DB_PATH"
            else {"name": key, "value": ":memory:"}
            for key in sorted(environment)
        ],
    }
    # Pin the project explicitly so ambient azd configuration cannot retarget it.
    # Only deploy the named agent; never provision this standalone project.
    manifest = {
        "name": args.agent,
        "services": {
            "ai-project": {"host": "azure.ai.project", "endpoint": args.staging_endpoint},
            args.agent: service,
        },
    }
    evidence = {
        "schema": "redteam-shadow-preparation/v1", "deployment_kind": "NEW-azd-remote-build",
        "cloud_operations_performed": False, "running": False, "ready_for_native_scan": False,
        "source_agent": args.source_agent, "source_agent_version": args.source_agent_version,
        "source_definition_sha256": args.source_definition_sha256,
        "expected_native_content_sha256": args.source_content_sha256,
        "source_revision": args.source_revision, "source_tree_oid": source_tree,
        "source_materialization": "Exact approved Git archive bytes; caches and untracked files not uploaded",
        "source_deployment_provenance": args.source_deployment_provenance,
        "agent": args.agent, "baseline_modified": False, "case_store": "private-in-memory",
        "preserved_environment_names": sorted(environment), "turns": 1, "timeout": args.timeout,
        "telemetry": "Source telemetry settings omitted; platform defaults not asserted disabled",
        "limitations": [
            "NEW upload and remote build, not SDK artifact reuse. No observed uploaded hash or activation yet.",
            "Post-deployment source/target native hashes and full sanitized runtime definitions must match.",
            "azd timeout only bounds waiting; it does not cancel Azure build/deployment or cap spend.",
            "No Toolbox is created or changed; existing staging routing settings must match the pinned source.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    for relative, content in snapshot.items():
        destination = output / "source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    write_json(output / "azure.yaml", manifest)  # JSON is a YAML-compatible manifest; no YAML dependency.
    write_json(output / "preparation.json", evidence)
    # Values stay in a local operational environment file, never in evidence or stdout.
    write_json(output / "runtime-settings.local.json", {
        "FOUNDRY_PROJECT_ENDPOINT": args.endpoint,
        **{"SHADOW_" + key: value for key, value in environment.items() if key != "CASE_STORE_DB_PATH"},
    })
    return evidence


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-new-code-deployment", action="store_true")
    parser.add_argument("--staging-endpoint", required=True)
    parser.add_argument("--source-agent", required=True)
    parser.add_argument("--source-agent-version", required=True)
    parser.add_argument("--source-definition-sha256", required=True)
    parser.add_argument("--source-content-sha256", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--source-deployment-provenance", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--runtime-setting", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args(argv)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
