"""Tool wrappers for the quote-preparation LangGraph agent (Phase 5).

Design choice -- in-process calls, not an MCP client session:
This workshop calls the Phase 4 MCP servers' tool functions
(`get_application`, `get_rulebook`) directly in-process, by loading each
server's `main.py` under a private module name, rather than opening a
`mcp` Python SDK `ClientSession` against a running streamable-http server
(the pattern the sibling `foundry-hosted-agents` toolbox.py uses --
`toolbox_tools`/`ToolboxAuth` there authenticate against a *deployed,
authenticated* Foundry Toolbox MCP endpoint over HTTPS). The sibling's
out-of-process client exists because its tools are hosted behind Foundry's
gateway; this project's Phase 4 servers are local, unauthenticated,
read-only FastMCP services (mcp/application-server, mcp/rulebook-server)
that this local/unhosted phase is explicitly forbidden from deploying
anywhere (Gate G2/G3/G6 not cleared). Calling their `@mcp.tool()`-decorated
functions in-process keeps this phase's tests fast and free of any server
process or open port, while still exercising the exact same functions the
servers expose over MCP -- the same convention already used by
mcp/application-server/tests/test_application_server.py and
mcp/rulebook-server/tests/test_rulebook_server.py. Swapping `get_application`
and `get_rulebook` below for a real `streamable_http_client`/`ClientSession`
call is a drop-in replacement once a hosted deployment is authorized.

This module also wraps the Phase 2 calculator (`calculate_quote`) and only
the read/create-draft surface of the Phase 3 `ApprovalRepository`
(`create_draft`, `submit_for_review`). `approve`, `reject`, `revise`, and
`open_training_preview` are intentionally never imported or wrapped here:
those transitions may only be performed by a human reviewer through a
separate reviewer-facing surface, never by agent code.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# A hosted Foundry agent deploy (see azure.yaml's `quote-preparation-agent`
# `project: ./src/quote-preparation-agent`) only ships this directory's own
# files -- `parents[2]` (the full monorepo checkout) does not exist in that
# container, so resolving it unconditionally crashed every hosted invocation
# with `IndexError: 2` (discovered during the first live `azd deploy` of this
# workshop). Guard it: fall back to `None` and skip sys.path insertion for
# any monorepo-relative directory that isn't actually present, so the local
# dev/test checkout (where these directories DO exist) keeps its original
# behaviour unchanged, while a hosted container degrades gracefully to the
# vendored fallbacks below instead of raising at import time.
try:
    REPO_ROOT: Path | None = Path(__file__).resolve().parents[2]
except IndexError:
    REPO_ROOT = None

APPS_WORKSHOP_DIR = REPO_ROOT / "apps" / "workshop" if REPO_ROOT else None
APPLICATION_SERVER_DIR = REPO_ROOT / "mcp" / "application-server" if REPO_ROOT else None
RULEBOOK_SERVER_DIR = REPO_ROOT / "mcp" / "rulebook-server" if REPO_ROOT else None

for _dir in (APPS_WORKSHOP_DIR, APPLICATION_SERVER_DIR, RULEBOOK_SERVER_DIR):
    if _dir is not None and _dir.exists():
        _path = str(_dir)
        if _path not in sys.path:
            sys.path.insert(0, _path)

# `approval_repository.py`/`calculator.py` are self-contained (stdlib only)
# application-layer modules. When the full monorepo checkout is present
# (local dev/test), the sys.path insertion above makes the canonical
# `apps/workshop` copies resolve first. When it isn't (hosted deploy), this
# import instead resolves to the vendored copies co-located with this file
# (`src/quote-preparation-agent/approval_repository.py`/`calculator.py`),
# which Python already finds via the entrypoint script's own directory on
# `sys.path` -- kept byte-identical to their `apps/workshop` originals.
from approval_repository import (  # noqa: E402
    ApprovalRepository,
    ApprovalRepositoryError,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidTransitionError,
)
from calculator import calculate_quote as _calculate_quote  # noqa: E402


def _load_mcp_tool(server_dir: Path, module_name: str, tool_name: str) -> Any:
    """Load one MCP server's `main.py` under a private module name and return one tool function.

    `application-server/main.py` and `rulebook-server/main.py` share the
    filename `main.py`; loading each under a unique module name avoids a
    `sys.modules["main"]` collision, matching the convention already used
    by this project's own MCP server tests.
    """
    spec = importlib.util.spec_from_file_location(module_name, server_dir / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return getattr(module, tool_name)


def _call_remote_mcp_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call `tool_name` on a deployed streamable-HTTP MCP server (hosted deploy path).

    Used only when the local monorepo checkout of the MCP servers
    (`mcp/application-server`, `mcp/rulebook-server`) isn't present -- i.e.
    inside the hosted agent container, which ships only
    `src/quote-preparation-agent`. `url` is the Container App's public
    `/mcp` endpoint (`APPLICATION_MCP_URL`/`RULEBOOK_MCP_URL`, set as
    environment variables by `azure.yaml`).
    """
    import asyncio

    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async def _invoke() -> dict[str, Any]:
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                for content in result.structuredContent and [result.structuredContent] or result.content:
                    if isinstance(content, dict):
                        return content
                    data = getattr(content, "data", None)
                    if isinstance(data, dict):
                        return data
                    text = getattr(content, "text", None)
                    if text:
                        import json

                        return json.loads(text)
                return {}

    return asyncio.run(_invoke())


_get_application_tool: Any = None
_get_rulebook_tool: Any = None


def get_application(fixture_id: str) -> dict[str, Any]:
    """Look up a synthetic quote-preparation application by fixture/case ID (read-only)."""
    global _get_application_tool
    if APPLICATION_SERVER_DIR is not None and APPLICATION_SERVER_DIR.exists():
        if _get_application_tool is None:
            _get_application_tool = _load_mcp_tool(
                APPLICATION_SERVER_DIR, "quote_agent_application_server_main", "get_application"
            )
        return _get_application_tool(fixture_id)
    url = os.environ["APPLICATION_MCP_URL"]
    return _call_remote_mcp_tool(url, "get_application", {"fixture_id": fixture_id})


def get_rulebook(rulebook_id: str) -> dict[str, Any]:
    """Look up the pinned synthetic rate/add-on rulebook by rulebook ID (read-only)."""
    global _get_rulebook_tool
    if RULEBOOK_SERVER_DIR is not None and RULEBOOK_SERVER_DIR.exists():
        if _get_rulebook_tool is None:
            _get_rulebook_tool = _load_mcp_tool(
                RULEBOOK_SERVER_DIR, "quote_agent_rulebook_server_main", "get_rulebook"
            )
        return _get_rulebook_tool(rulebook_id)
    url = os.environ["RULEBOOK_MCP_URL"]
    return _call_remote_mcp_tool(url, "get_rulebook", {"rulebook_id": rulebook_id})


def calculate_quote(
    input_data: dict[str, Any] | None,
    rulebook: dict[str, Any] | None,
    *,
    expected_rulebook_version: str | None = None,
) -> dict[str, Any]:
    """Run the Phase 2 pure deterministic calculator. No I/O, no LLM calls."""
    return _calculate_quote(input_data, rulebook, expected_rulebook_version=expected_rulebook_version)


def create_draft(repository: ApprovalRepository, case_id: str, preparer_id: str):
    """Create a DRAFT case. Never call approve/reject/revise from agent code."""
    return repository.create_draft(case_id, preparer_id)


def submit_for_review(repository: ApprovalRepository, case_id: str, actor_id: str):
    """Submit a DRAFT case for human review. Never call approve/reject/revise from agent code."""
    return repository.submit_for_review(case_id, actor_id)


__all__ = [
    "ApprovalRepository",
    "ApprovalRepositoryError",
    "CaseAlreadyExistsError",
    "CaseNotFoundError",
    "InvalidTransitionError",
    "get_application",
    "get_rulebook",
    "calculate_quote",
    "create_draft",
    "submit_for_review",
]
