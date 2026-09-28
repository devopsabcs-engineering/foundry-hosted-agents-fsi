---
permalink: /labs/lab-05-rulebook-server
title: "Lab 05 - The Rulebook MCP Server"
description: "Run the read-only rulebook-server and confirm it serves only the pinned synthetic rate table."
---

> 🇫🇷 **[Version française](../fr/labs/lab-05-rulebook-server)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 20 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 00](lab-00-setup.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain why `mcp/rulebook-server` runs independently of `apps/workshop` and the agent, with no shared runtime
* Confirm the server exposes exactly one tool, `get_rulebook(rulebook_id)`
* Start the server locally and query it for the pinned rulebook ID and an unknown one
* Explain why the served rulebook always carries `"authority": "WORKSHOP_AUTHORS_ONLY"`

## Exercises

### Exercise 5.1: Read the Server

Open `mcp/rulebook-server/main.py` and `mcp/rulebook-server/rulebook_data_loader.py`. Note that `get_rulebook` compares the requested `rulebook_id` against the single pinned rulebook's `id` field, `RULEBOOK-SYN-ON`, and returns an explicit `{"rulebookId": ..., "error": "rulebook not found"}` object for any other value.

### Exercise 5.2: Run the Existing Tests

```powershell
python -m pytest mcp/rulebook-server/tests -v
```

Expected result: every test passes, mirroring Lab 04's coverage for the rulebook lookup.

### Exercise 5.3 (Hands-on): Start the Server and Query It

```powershell
python mcp/rulebook-server/main.py
```

The server listens on `http://0.0.0.0:8002` by default. Leave it running, then in a second terminal, call it over MCP:

```powershell
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client('http://localhost:8002/mcp') as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('tools:', [t.name for t in tools.tools])
            for rulebook_id in ('RULEBOOK-SYN-ON', 'RULEBOOK-DOES-NOT-EXIST'):
                result = await session.call_tool('get_rulebook', {'rulebook_id': rulebook_id})
                print(rulebook_id, '->', result.content[0].text)

asyncio.run(main())
"
```

Expected result: the pinned rulebook ID returns the full rulebook, including its `baseCents`, `planAddOnCents`, and the `en-CA`/`fr-CA` notice text. The unknown ID returns an explicit `error` field. The server console shows one `get_rulebook(...) -> found` or `-> rulebook not found` line per call. Stop the server with `Ctrl+C` when you are done.

## Validation Checklist

* [ ] `pytest mcp/rulebook-server/tests -v` passes
* [ ] The pinned `rulebookId` returns the exact rulebook content
* [ ] An unknown `rulebookId` returns an explicit `error` result, not an exception
* [ ] You can state what `"authority": "WORKSHOP_AUTHORS_ONLY"` communicates to anyone reading this data

## Knowledge Check

* Why does this server serve only one rulebook ID instead of a lookup table of many rulebooks?
* If a new rulebook version were pinned tomorrow, what would have to change in this server's data file for `get_rulebook` to return it?

## Next Steps

Continue to [Lab 06: The LangGraph Agent](lab-06-agent-graph.md).
