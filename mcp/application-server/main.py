"""Read-only MCP server exposing the synthetic quote-preparation application record.

Runs fully independently of the workshop backend (apps/workshop) and the
quote-preparation agent -- no shared runtime or import. Serves only
get_application(fixture_id): the requested fixtureId/input pair from
data/synthetic/fixtures/, or an explicit "not found" result for an unknown
ID. Never returns expectedCalculation, workflow, or nextCommand test
scaffolding, and exposes no write, SQL, URL, or path-based tool -- the
ApprovalRepository (apps/workshop/approval_repository.py) is the only
write-capable component in this project and is never reachable from here.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from application_data_loader import load_applications

PORT = int(os.environ.get("PORT", "8001"))

mcp = FastMCP("application-mcp-server", host="0.0.0.0", port=PORT)

_APPLICATIONS = load_applications()


@mcp.tool()
def get_application(fixture_id: str) -> dict:
    """Look up a synthetic quote-preparation application input by fixture ID (read-only)."""
    application = _APPLICATIONS.get(fixture_id)
    if application is None:
        return {"fixtureId": fixture_id, "error": "fixture not found"}
    return application


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
