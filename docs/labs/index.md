---
permalink: /labs/
title: "Labs"
description: "The ten-lab curriculum for the synthetic Ontario auto-insurance quote-preparation workshop."
---

> 🇫🇷 **[Version française](../fr/labs/)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output across these labs is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Lab Curriculum

Work through the labs in order. Each one builds on the code and fixtures introduced by the labs before it.

| Lab | Title | What you will do |
| --- | --- | --- |
| [00](lab-00-setup.md) | Setup | Create a virtual environment, install dependencies, and run the existing test suites |
| [01](lab-01-fixtures-schema.md) | Fixtures and Schema | Explore the synthetic fixtures and the JSON Schema that binds their shape |
| [02](lab-02-calculator.md) | The Deterministic Calculator | Trace `calculate_quote` and prove it never invents an amount |
| [03](lab-03-approval-repository.md) | Approval Repository and State Machine | Walk the DRAFT to PENDING_REVIEW to APPROVED/REJECTED state machine |
| [04](lab-04-application-server.md) | The Application MCP Server | Run the read-only `get_application` MCP service |
| [05](lab-05-rulebook-server.md) | The Rulebook MCP Server | Run the read-only `get_rulebook` MCP service |
| [06](lab-06-agent-graph.md) | The LangGraph Agent | Trace the supervisor and its three sequential specialists |
| [07](lab-07-run-agent.md) | Run the Agent End to End | Run the agent against a fixture, then act as the human reviewer |
| [08](lab-08-evaluations.md) | Evaluation Suite | Explore the golden dataset and deterministic evaluation gate |
| [09](lab-09-teardown.md) | Teardown | Stop local processes and confirm there is no cloud teardown to run |

## Next Steps

Start with [Lab 00: Setup](lab-00-setup.md).
