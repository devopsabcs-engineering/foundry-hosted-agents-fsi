---
permalink: /labs/lab-04-application-server
title: "Lab 04 - The Application MCP Server"
description: "Run the read-only application-server and confirm it exposes only get_application, rejecting unknown fixture IDs."
---

> 🇫🇷 **[Version française](../fr/labs/lab-04-application-server)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 25 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 00](lab-00-setup.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain why `mcp/application-server` runs independently of `apps/workshop` and the agent, with no shared runtime
* Confirm the server exposes exactly one tool, `get_application(fixture_id)`
* Start the server locally and query it for a known and an unknown fixture ID
* Confirm the server never returns write-capable behavior of any kind

## Exercises

### Exercise 4.1: Read the Server

Open `mcp/application-server/main.py` and `mcp/application-server/application_data_loader.py`. Note that `get_application` looks up a fixture by ID from the data loaded at startup and returns an explicit `{"fixtureId": ..., "error": "fixture not found"}` object for any ID it does not recognize, rather than raising an exception or returning an empty result.

### Exercise 4.2: Run the Existing Tests

```powershell
python -m pytest mcp/application-server/tests -v
```

Expected result: every test passes, including cases for a known fixture, an unknown fixture ID, and a check that no other tool is registered on this server.

### Exercise 4.3 (Hands-on): Start the Server and Query It

In one terminal, start the server:

```powershell
python mcp/application-server/main.py
```

The server listens on `http://0.0.0.0:8001` using the streamable-http transport by default. Leave it running, then in a second terminal, call `get_application` directly by importing the same tool function the server exposes:

```powershell
python -c "
import sys
sys.path.insert(0, 'mcp/application-server')
from main import get_application

print(get_application('CASE-SYN-001'))
print(get_application('CASE-SYN-999'))
"
```

Expected result: the known fixture ID returns the fixture's `input` content; the unknown ID returns an explicit `error` field, never a raised exception or a fabricated fixture. Stop the server with `Ctrl+C` when you are done.

## Validation Checklist

* [ ] `pytest mcp/application-server/tests -v` passes
* [ ] A known `fixtureId` returns the exact fixture input
* [ ] An unknown `fixtureId` returns an explicit `error` result, not an exception
* [ ] You confirmed the server exposes no tool other than `get_application`

## Knowledge Check

* Why does this server load its data once at startup rather than reading from disk on every call?
* What would go wrong if `get_application` raised an exception for an unknown fixture ID instead of returning an error object?

## Next Steps

Continue to [Lab 05: The Rulebook MCP Server](lab-05-rulebook-server.md).
