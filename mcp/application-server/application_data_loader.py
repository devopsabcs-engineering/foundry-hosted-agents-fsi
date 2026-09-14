"""Loads synthetic application fixtures for the read-only application-server.

Reads every JSON fixture from data/synthetic/fixtures/ once at import time
and exposes only the narrow (fixtureId, input) pair for each one, matching
the platform research constraint: get_application returns the requested
synthetic input record, never the full test envelope (expectedCalculation,
workflow, nextCommand, expectedDisplay).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "data" / "synthetic" / "fixtures"


def load_applications(fixtures_dir: Path = FIXTURES_DIR) -> dict[str, dict[str, Any]]:
    """Return a mapping of fixtureId -> {"fixtureId": ..., "input": ...}."""
    applications: dict[str, dict[str, Any]] = {}
    for path in sorted(fixtures_dir.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        fixture_id = fixture["fixtureId"]
        applications[fixture_id] = {"fixtureId": fixture_id, "input": fixture["input"]}
    return applications
