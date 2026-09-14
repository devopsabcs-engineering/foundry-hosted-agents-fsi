"""Read-only MCP server exposing the pinned synthetic rate/add-on rulebook.

Runs fully independently of the workshop backend (apps/workshop) and the
quote-preparation agent -- no shared runtime or import. Serves only
get_rulebook(rulebook_id): the pinned RULEBOOK-SYN-ON rulebook from
data/synthetic/rulebook.json, or an explicit "not found" result for any
other rulebook ID -- never a fabricated or default table. Reuses the
calculator's WORKSHOP_AUTHORS_ONLY-authority, "unsupported"/"not found"
framing (apps/workshop/calculator.py) conceptually only; this server does
not import that application-layer module. No write, SQL, URL, or path-based
tool is exposed.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from rulebook_data_loader import load_rulebook

PORT = int(os.environ.get("PORT", "8002"))

mcp = FastMCP("rulebook-mcp-server", host="0.0.0.0", port=PORT)

_RULEBOOK = load_rulebook()


@mcp.tool()
def get_rulebook(rulebook_id: str) -> dict:
    """Look up the pinned synthetic rate/add-on rulebook by rulebook ID (read-only)."""
    if rulebook_id != _RULEBOOK.get("id"):
        return {"rulebookId": rulebook_id, "error": "rulebook not found"}
    return _RULEBOOK


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
