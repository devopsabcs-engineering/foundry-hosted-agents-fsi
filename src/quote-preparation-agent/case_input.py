"""Parse a case-input request into the graph's initial-state fields.

Shared by `main.py` (local CLI path) and `response_bridge.py` (hosted
Responses-protocol path). Deliberately kept out of `main.py` itself: when
the hosted agent runs as `python main.py` (see `main.serve`), its own
module is loaded as `__main__`, not `main` -- and `toolbox.py`'s sys.path
insertion of `mcp/application-server`/`mcp/rulebook-server` (each of which
also has its own unrelated `main.py`) can shadow a plain `import main`
elsewhere in the process. A neutral module name avoids that collision.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Matches a case-reference-shaped token (e.g. CASE-SYN-001, CASE-FAULT-SELF-
# APPROVAL-001, NOT-A-CASE-ID) embedded in a natural-language sentence, so a
# free-text request (e.g. "Please prepare a training quote for case
# CASE-SYN-001: a COMPACT vehicle...", as used by the judge-evaluation
# dataset and by conversational Responses-protocol clients) can still be
# routed to the graph's own strict `CASE_ID_PATTERN` validator in graph.py --
# this pattern deliberately does not validate the reference itself, it only
# extracts the candidate token and lets the graph decide if it's valid.
_CASE_ID_TOKEN_PATTERN = re.compile(r"[A-Z]+(?:-[A-Z0-9]+)+")


def parse_case_input(raw: str) -> dict[str, Any]:
    """Accept a bare case ID, a JSON object with a caseId field, or a free-text sentence."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = _CASE_ID_TOKEN_PATTERN.search(raw)
        return {"caseId": match.group(0) if match else raw}
    if isinstance(payload, str):
        return {"caseId": payload}
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Unsupported case input: {raw!r}")
