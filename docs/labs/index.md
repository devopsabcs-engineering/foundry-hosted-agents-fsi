---
permalink: /labs/
title: "Labs"
description: "The twenty-lab curriculum for the synthetic Ontario auto-insurance quote-preparation workshop."
---

> 🇫🇷 **[Version française](../fr/labs/)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output across these labs is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Lab Curriculum

Work through the labs in order. Each one builds on the code and fixtures introduced by the labs before it.

Labs 00 through 09 run entirely on your laptop. Labs 10 through 14 add the pilot surfaces: the Azure foundation, the two web interfaces, the identity configuration behind them, and the pipeline that keeps them honest.

Labs 15 through 18 add isolated native showcase exercises with explicit evidence
checks. Some exercises require approved service prerequisites or retained native
artifacts; record missing prerequisites as blocked rather than inventing results.
Keep the approved staging v6 and production v7 deployment available when
continuing. Check the [release evidence](../showcase-evidence.md#current-approved-release)
and [architecture](../architecture.md) before using live surfaces.

### Local Foundations

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
| [09](lab-09-teardown.md) | Teardown | Stop local processes and clean up the on-disk state you created |

### The Pilot Surfaces

| Lab | Title | What you will do |
| --- | --- | --- |
| [10](lab-10-azure-foundation.md) | Provision the Azure Foundation | Read and compile the Bicep templates, and understand why the network is deployed separately |
| [11](lab-11-web-chat.md) | The Applicant Web Chat UI | Run the applicant chat and trace the bounded no-premium message contract |
| [12](lab-12-reviewer-identity.md) | Reviewer Identity and Access | Register the reviewer app, grant the Reviewer role, and compute redirect URIs |
| [13](lab-13-reviewer-ui.md) | The Reviewer UI | Seed a queue, sign in, approve a case, and read the audit trail |
| [14](lab-14-pilot-operations.md) | Pilot Operations | Run the validation pipeline, read the evaluation gate, and walk the teardown safeguards |

### Native Showcase

| Lab | Title | What you will do |
| --- | --- | --- |
| [15](lab-15-native-files-generation.md) | Native Files and Generation | Upload the synthetic reference, download native QnA and diagnose historical failed jobs |
| [16](lab-16-native-search-invoice.md) | File Search and Invoice Extraction | Check bilingual citations and refusals, then inspect native invoice fields and grounding |
| [17](lab-17-native-skills-memory.md) | Runtime Skills and Memory Boundaries | Prove isolated skill consumption and distinguish verified memory namespaces from caller authorization |
| [18](lab-18-native-evaluation-traces.md) | Native Evaluation and Trace Replay | Compare real evaluator runs, preserve failed grounding controls and require ingestion before replay |

The [native showcase runbook](../native-showcase.md) records historical evidence
and service limits. The labs do not authorize deployment, access changes or teardown.

### Evaluation Engineering

| Lab | Title | What you will do |
| --- | --- | --- |
| [19](lab-19-evaluation-engineering.md) | Evaluation Engineering | Build a layered non-regression plan, run native EN/FR judges, calibrate controls, repeat trials and evaluate stateful revisions |

Use the [step-by-step guide](../evaluation-guide.md) and
[PowerPoint with instructor notes](../assets/decks/foundry-evaluation-engineering-en.pptx)
for the 3–4 hour deep lab. The complete curriculum now spans Labs 00–19.

Exercise 19.4 includes retained-run screenshots for read-only inspection.
The separate portal practice uses supplied authored synthetic
[English JSONL](../assets/datasets/portal-practice-en-CA.jsonl) or
[French JSONL](../assets/datasets/portal-practice-fr-CA.jsonl), not captured agent
responses. Uploads and paid submissions require separate approval.

## Next Steps

Start with [Lab 00: Setup](lab-00-setup.md).
