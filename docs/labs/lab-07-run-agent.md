---
permalink: /labs/lab-07-run-agent
title: "Lab 07 - Run the Agent End to End"
description: "Run the local agent against a fixture, read its bounded bilingual applicant message, then act as the human reviewer."
---

> 🇫🇷 **[Version française](../fr/labs/lab-07-run-agent)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 06](lab-06-agent-graph.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Run the agent's CLI end to end against a fixture, with no Azure or hosted Foundry call
* Confirm the applicant-facing message never includes an amount, a rulebook table, or a reviewer-only field
* Act as the human reviewer against the same `ApprovalRepository`, since no reviewer UI exists yet
* Confirm an invalid case reference produces a bounded rejection message instead of a raised exception

## Exercises

### Exercise 7.1: Run the CLI Against a Known Fixture

```powershell
python src/quote-preparation-agent/main.py CASE-SYN-001
```

Expected result: a JSON object with `en-CA` and `fr-CA` keys, each holding a bilingual sentence telling the applicant their request was submitted for employee review. No dollar amount, rulebook field, or reviewer identifier appears anywhere in the output.

### Exercise 7.2 (Hands-on): Confirm the Workflow State Directly

The CLI only prints the applicant message. Call `run_case` directly to inspect the full state, including `workflow_state`.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
from main import run_case

final_state = run_case('CASE-SYN-001')
print('workflow_state:', final_state['workflow_state'])
print('draft_case_id:', final_state['draft_case_id'])
print('applicant_message:', final_state['applicant_message'])
"
```

Expected result: `workflow_state` is `PENDING_REVIEW`. The case was created and submitted for review, but nothing in the agent's own code approved or rejected it.

### Exercise 7.3 (Hands-on): Act as the Human Reviewer

Because no reviewer interface exists yet in this project, a reviewer acts directly against `ApprovalRepository`. Share one repository instance between the agent run and your reviewer step so they operate on the same case.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
sys.path.insert(0, 'apps/workshop')
from main import run_case
from approval_repository import ApprovalRepository

repo = ApprovalRepository()
final_state = run_case('CASE-SYN-001', repository=repo, preparer_id='AGENT-INTAKE')
print('after agent run:', final_state['workflow_state'])

record = repo.approve(final_state['draft_case_id'], reviewer_id='EMP-REVIEWER-01')
print('after human review:', record.state)
"
```

Expected result: the state moves from `PENDING_REVIEW` to `APPROVED`, and the reviewer ID (`EMP-REVIEWER-01`) differs from the preparer ID (`AGENT-INTAKE`) used by the agent.

### Exercise 7.4: Run Against an Invalid Case Reference

```powershell
python src/quote-preparation-agent/main.py "NOT-A-VALID-CASE-ID"
```

Expected result: a bilingual message stating the request could not be processed because the case reference was invalid, with no exception raised and no case created in the approval repository.

## Validation Checklist

* [ ] Exercise 7.1 prints a bilingual message with no dollar amount
* [ ] Exercise 7.2 confirms `workflow_state` is `PENDING_REVIEW` immediately after the agent runs
* [ ] Exercise 7.3 approves the case as a distinct reviewer, moving it to `APPROVED`
* [ ] Exercise 7.4 returns the bounded rejection message for an invalid case reference

## Knowledge Check

* Why does the agent stop at `PENDING_REVIEW` instead of deciding the case itself?
* What would happen in Exercise 7.3 if you called `repo.approve` with `reviewer_id='AGENT-INTAKE'` instead of a distinct reviewer?

## Next Steps

Continue to [Lab 08: Evaluation Suite](lab-08-evaluations.md).
