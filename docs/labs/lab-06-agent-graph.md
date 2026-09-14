---
permalink: /labs/lab-06-agent-graph
title: "Lab 06 - The LangGraph Agent"
description: "Trace the supervisor and three sequential specialists: intake, reference lookup, and composition."
---

> 🇫🇷 **[Version française](../fr/labs/lab-06-agent-graph)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 35 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 02](lab-02-calculator.md), [Lab 03](lab-03-approval-repository.md), [Lab 04](lab-04-application-server.md), [Lab 05](lab-05-rulebook-server.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Name the agent's three sequential stages: intake, reference lookup, composition
* Explain the supervisor's routing rule in `decide_next_step`, including the short-circuit for an invalid case reference
* Explain why `toolbox.py` calls the Lab 04/05 MCP tool functions in-process instead of opening a network client session
* Confirm the agent's own code never calls `approve`, `reject`, or `revise` on the approval repository

## Exercises

### Exercise 6.1: Read the Supervisor's Routing Logic

Open `src/quote-preparation-agent/graph.py` and read `decide_next_step`. The supervisor always visits `intake` first. If intake found the case reference valid, it routes to `reference_lookup` next; if intake found it invalid, it skips straight to `composition` so composition can still produce a bounded rejection message. Once composition completes, the graph ends.

### Exercise 6.2: Read Why Toolbox Calls Are In-Process

Open `src/quote-preparation-agent/toolbox.py` and read its module docstring. It explains that this phase calls `get_application` and `get_rulebook` by loading each MCP server's `main.py` directly, rather than opening an `mcp` Python SDK `ClientSession` against a running server. This keeps tests fast and free of any open port, while still exercising the exact functions each server exposes over MCP. Note also that `approve`, `reject`, `revise`, and `open_training_preview` are intentionally never imported here: only a human reviewer may call those.

### Exercise 6.3: Run the Existing Tests

```powershell
python -m pytest src/quote-preparation-agent/tests/test_toolbox.py -v
```

Expected result: every test passes, confirming the toolbox wrappers call through to the calculator, the approval repository, and both MCP servers correctly.

### Exercise 6.4 (Hands-on): Inject a Stub Model

`build_graph` in `graph.py` accepts an optional `model` callable, defaulting to `default_model`, which makes no network call. Build the graph with your own stub and confirm the intake node's note reflects it.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
from graph import build_graph

def my_stub_model(prompt: str) -> str:
    return f'[lab-06-stub] {prompt}'

graph = build_graph(model=my_stub_model)
result = graph.invoke({
    'case_id': 'CASE-SYN-001',
    'preparer_id': 'AGENT-INTAKE',
    'rulebook_id': 'RULEBOOK-SYN-ON',
    'intake_complete': False,
    'lookup_complete': False,
    'composition_complete': False,
})
print(result['intake_note'])
"
```

Expected result: the printed note starts with `[lab-06-stub]`, confirming the model callable is a genuine seam and not hardcoded.

## Validation Checklist

* [ ] `pytest src/quote-preparation-agent/tests/test_toolbox.py -v` passes
* [ ] You can name the three sequential stages and explain the invalid-case-reference short-circuit
* [ ] You located the toolbox docstring explaining the in-process MCP call design choice
* [ ] Your Exercise 6.4 stub model's text appeared in the graph's output

## Knowledge Check

* Why does `toolbox.py` never import `approve`, `reject`, `revise`, or `open_training_preview` from the approval repository?
* What would have to change in `toolbox.py` for this agent to call a deployed MCP server instead of an in-process function?

## Next Steps

Continue to [Lab 07: Run the Agent End to End](lab-07-run-agent.md).
