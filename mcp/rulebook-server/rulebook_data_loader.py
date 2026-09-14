"""Loads the pinned synthetic rulebook for the read-only rulebook-server.

Reads data/synthetic/rulebook.json once at import time. This synthetic
dataset pins exactly one rulebook (RULEBOOK-SYN-ON); any other requested
rulebook ID is rejected by the server rather than fabricated. This module
duplicates the small amount of loading logic in
mcp/application-server/data_loader.py rather than importing across the two
MCP server directories, keeping each service independently deployable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RULEBOOK_PATH = REPO_ROOT / "data" / "synthetic" / "rulebook.json"


def load_rulebook(rulebook_path: Path = RULEBOOK_PATH) -> dict[str, Any]:
    """Return the single pinned rulebook, as read from disk."""
    return json.loads(rulebook_path.read_text(encoding="utf-8"))
