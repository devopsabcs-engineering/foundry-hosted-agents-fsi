"""Prepare a separately pinned protocol shadow without changing original files."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = "redteam_protocol_entrypoint.py"
ENTRYPOINT_PATH = "scripts/" + ENTRYPOINT
MAX_PACKAGE_BYTES = 10_000_000


def reviewed_entrypoint(revision: str, expected_sha256: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256,
    ):
        raise ValueError("Protocol revision and entrypoint hash must be explicit full hashes")
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if current != revision:
        raise ValueError("Protocol correction must run from its exact reviewed Git revision")
    content = subprocess.run(
        ["git", "show", revision + ":" + ENTRYPOINT_PATH],
        cwd=REPO_ROOT, check=True, capture_output=True,
    ).stdout
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Protocol entrypoint differs from the separately reviewed hash")
    return content


def supported_graph_hash(entrypoint: bytes) -> str:
    module = ast.parse(entrypoint.decode("utf-8"))
    values = [
        node.value.value for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SUPPORTED_GRAPH_SHA256"
                for target in node.targets)
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    ]
    if len(values) != 1 or not re.fullmatch(r"[0-9a-f]{64}", values[0]):
        raise ValueError("Reviewed protocol entrypoint must pin one supported graph hash")
    return values[0]


def build_package(
    original: bytes, *, source_sha256: str, protocol_revision: str,
    entrypoint_sha256: str,
) -> tuple[bytes, dict]:
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("Original native package requires its reviewed SHA-256")
    if len(original) > MAX_PACKAGE_BYTES:
        raise ValueError("Protocol source package exceeds the bounded 10 MB limit")
    if hashlib.sha256(original).hexdigest() != source_sha256:
        raise ValueError("Protocol source ZIP differs from the original immutable package")
    entrypoint = reviewed_entrypoint(protocol_revision, entrypoint_sha256)
    graph_hash = supported_graph_hash(entrypoint)
    try:
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(item.file_size for item in entries) > MAX_PACKAGE_BYTES:
                raise ValueError("Protocol source ZIP exceeds bounded file/expanded-size limits")
            names = set()
            for item in entries:
                path, windows_path = PurePosixPath(item.filename), PureWindowsPath(item.filename)
                if (
                    not item.filename or item.orig_filename != item.filename
                    or "\\" in item.orig_filename or path.is_absolute()
                    or windows_path.anchor or ".." in path.parts
                    or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1
                    or item.filename in names
                ):
                    raise ValueError("Protocol source ZIP has unsafe, duplicate or encrypted entries")
                names.add(item.filename)
            if ENTRYPOINT in names or not {"main.py", "graph.py", "response_bridge.py"} <= names:
                raise ValueError("Protocol source ZIP must contain the unmodified original quote entrypoints")
            if hashlib.sha256(archive.read("graph.py").replace(b"\r\n", b"\n")).hexdigest() != graph_hash:
                raise ValueError("Protocol source graph is not the reviewed network-free implementation")
            if archive.testzip() is not None:
                raise ValueError("Protocol source ZIP has corrupt file contents")
    except zipfile.BadZipFile as exc:
        raise ValueError("Protocol source is not a valid original native ZIP") from exc
    result = io.BytesIO(original)
    with zipfile.ZipFile(result, "a") as archive:
        info = zipfile.ZipInfo(ENTRYPOINT, date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, entrypoint)
    package = result.getvalue()
    if len(package) > MAX_PACKAGE_BYTES:
        raise ValueError("Derived protocol package exceeds the bounded 10 MB limit")
    return package, {
        "schema": "redteam-protocol-package/v1",
        "source_content_sha256": source_sha256,
        "protocol_revision": protocol_revision,
        "protocol_entrypoint_sha256": entrypoint_sha256,
        "target_content_sha256": hashlib.sha256(package).hexdigest(),
        "supported_graph_sha256": graph_hash,
        "entrypoint": ENTRYPOINT,
        "original_files_preserved": True,
        "immutable_artifact_equality": False,
        "baseline_modified": False,
        "cloud_operations_performed": False,
        "model_usage_scope": "Pinned network-free model only; excludes evaluator/service models and charges",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--source-content-sha256", required=True)
    parser.add_argument("--protocol-revision", required=True)
    parser.add_argument("--protocol-entrypoint-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if not output.is_relative_to(REPO_ROOT / ".local"):
        parser.error("Use a fresh preparation directory under this repository's .local directory")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("output-dir must be new or empty to preserve evidence")
    if args.source_zip.stat().st_size > MAX_PACKAGE_BYTES:
        parser.error("Protocol source package exceeds the bounded 10 MB limit")
    package, evidence = build_package(
        args.source_zip.read_bytes(), source_sha256=args.source_content_sha256,
        protocol_revision=args.protocol_revision,
        entrypoint_sha256=args.protocol_entrypoint_sha256,
    )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "protocol-native-code.zip").open("xb") as handle:
        handle.write(package)
    with (output / "protocol-preparation.json").open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2)
        handle.write("\n")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
