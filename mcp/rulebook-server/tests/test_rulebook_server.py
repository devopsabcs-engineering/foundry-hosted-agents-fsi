"""Unit tests for the read-only rulebook-server MCP tool.

Verifies get_rulebook returns the exact pinned RULEBOOK-SYN-ON table for its
known ID, a clear "not found" result for any other rulebook ID (never a
fabricated table), and that the server registers no write-capable tool.
No network, LLM, or database access is used anywhere in this file.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

# mcp/rulebook-server is not installed as a package; add it directly to
# sys.path so main.py's own `from rulebook_data_loader import ...` import
# resolves, matching the apps/workshop test convention. main.py itself is
# loaded under a unique module name (not the plain "main") because
# mcp/application-server/main.py shares the same filename and would
# otherwise collide in sys.modules within the same pytest session.
SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

_spec = importlib.util.spec_from_file_location("rulebook_server_main", SERVER_DIR / "main.py")
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)  # type: ignore[union-attr]

get_rulebook = _main.get_rulebook
mcp = _main.mcp

REPO_ROOT = Path(__file__).resolve().parents[3]
RULEBOOK_PATH = REPO_ROOT / "data" / "synthetic" / "rulebook.json"


def test_get_rulebook_returns_pinned_rulebook_for_known_id():
    expected = json.loads(RULEBOOK_PATH.read_text(encoding="utf-8"))

    result = get_rulebook("RULEBOOK-SYN-ON")

    assert result == expected


def test_get_rulebook_rejects_unknown_rulebook_id():
    result = get_rulebook("RULEBOOK-SYN-QC")

    assert result["rulebookId"] == "RULEBOOK-SYN-QC"
    assert "error" in result
    assert "baseCents" not in result


def test_server_exposes_only_get_rulebook():
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == ["get_rulebook"]
