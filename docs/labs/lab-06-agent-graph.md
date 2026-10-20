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
* Distinguish the local in-process MCP functions from the hosted HTTP client path
* Confirm the agent's own code never calls `approve`, `reject`, or `revise` on the approval repository

## Exercises

### Exercise 6.1: Read the Supervisor's Routing Logic

Open `src/quote-preparation-agent/graph.py` and read `decide_next_step`. The supervisor always visits `intake` first. If intake found the case reference valid, it routes to `reference_lookup` next; if intake found it invalid, it skips straight to `composition` so composition can still produce a bounded rejection message. Once composition completes, the graph ends.

### Exercise 6.2: Compare Local and Hosted Toolbox Calls

Read `src/quote-preparation-agent/toolbox.py`, including its implementation
after the original local-phase docstring. In this checkout it loads each MCP
server's `main.py` and calls the functions in-process, keeping these exercises
network-free. In the hosted image the monorepo server directories are absent;
the wrappers instead call `_call_remote_mcp_tool` with a streamable-HTTP
`ClientSession` and `APPLICATION_MCP_URL`/`RULEBOOK_MCP_URL` from `azure.yaml`.
You do not need to start the Lab 04/05 servers for the local graph.

`approve`, `reject`, `revise`, and `open_training_preview` are not exposed by
the toolbox. Employee decisions use the separate reviewer surface. Calculation
and case-store submission happen inside `COMPOSITION`; `AGENT_TASK_INSTRUCTIONS`
is evaluation metadata, not an executed system prompt. See the
[architecture](../architecture.md) for the hosted boundary.

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
* [ ] You located both the in-process and hosted streamable-HTTP toolbox paths
* [ ] Your Exercise 6.4 stub model's text appeared in the graph's output

## Knowledge Check

* Why does `toolbox.py` never import `approve`, `reject`, `revise`, or `open_training_preview` from the approval repository?
* What packaging condition selects the existing remote MCP path, and which two environment variables does it require?

## Next Steps

Continue to [Lab 07: Run the Agent End to End](lab-07-run-agent.md).
