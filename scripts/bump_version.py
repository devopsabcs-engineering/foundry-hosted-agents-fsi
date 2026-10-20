"""Bump an app version, or derive a read-only source-qualified image version.

Reads `apps/<app>/VERSION`, increments the requested part (default: patch),
writes the new version back with a trailing newline, and prints the new
version to stdout (and only the new version, so CI can capture it via
command substitution, e.g. `NEW_VERSION=$(python scripts/bump_version.py --app web-chat)`).
With --source-sha, print X.Y.Z-<full-sha> without modifying the file; release
jobs can publish exact-source images without committing to protected main.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

REPO_ROOT = Path(__file__).resolve().parent.parent


def bump(version: str, part: str) -> str:
    """Return `version` with `part` ("major", "minor", or "patch") incremented."""
    match = VERSION_RE.match(version.strip())
    if not match:
        raise ValueError(f"Invalid semver version: {version!r} (expected X.Y.Z)")
    major, minor, patch = (int(group) for group in match.groups())
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid part: {part!r} (expected major, minor, or patch)")
    return f"{major}.{minor}.{patch}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, choices=["web-chat", "reviewer-app"])
    parser.add_argument("--part", choices=["major", "minor", "patch"], default="patch")
    parser.add_argument("--source-sha", help="Derive an image version without changing VERSION")
    args = parser.parse_args()

    version_path = REPO_ROOT / "apps" / args.app / "VERSION"
    current_version = version_path.read_text(encoding="utf-8")
    if args.source_sha is not None:
        if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
            parser.error("--source-sha must be a full lowercase Git commit SHA")
        if not VERSION_RE.fullmatch(current_version.strip()):
            parser.error("VERSION must contain X.Y.Z")
        print(f"{current_version.strip()}-{args.source_sha}")
        return
    new_version = bump(current_version, args.part)
    version_path.write_text(f"{new_version}\n", encoding="utf-8")
    print(new_version)


if __name__ == "__main__":
    main()
