"""Unit tests for the read-only application-server MCP tool.

Verifies get_application returns exactly the fixtureId/input pair for a
known fixture ID, a clear "not found" result for an unknown ID (never a
fabricated record), and that the server registers no write-capable tool.
No network, LLM, or database access is used anywhere in this file.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

# mcp/application-server is not installed as a package; add it directly to
# sys.path so main.py's own `from application_data_loader import ...` import
# resolves, matching the apps/workshop test convention. main.py itself is
# loaded under a unique module name (not the plain "main") because
# mcp/rulebook-server/main.py shares the same filename and would otherwise
# collide in sys.modules within the same pytest session.
SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

_spec = importlib.util.spec_from_file_location("application_server_main", SERVER_DIR / "main.py")
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)  # type: ignore[union-attr]

get_application = _main.get_application
mcp = _main.mcp

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "data" / "synthetic" / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_get_application_returns_known_fixture_input():
    fixture = _load_fixture("case-syn-001.json")

    result = get_application(fixture["fixtureId"])

    assert result == {"fixtureId": fixture["fixtureId"], "input": fixture["input"]}


def test_get_application_returns_only_fixture_id_and_input():
    # The full test envelope (expectedCalculation, workflow, nextCommand,
    # expectedDisplay) must never leave the MCP boundary.
    result = get_application("CASE-SYN-001")

    assert set(result) == {"fixtureId", "input"}


def test_get_application_rejects_unknown_fixture_id():
    result = get_application("CASE-SYN-999")

    assert result["fixtureId"] == "CASE-SYN-999"
    assert "error" in result
    assert "input" not in result


def test_all_fixtures_are_individually_resolvable():
    for path in FIXTURES_DIR.glob("*.json"):
        fixture = json.loads(path.read_text(encoding="utf-8"))

        result = get_application(fixture["fixtureId"])

        assert result["input"] == fixture["input"]


def test_server_exposes_only_get_application():
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == ["get_application"]
