---
permalink: /labs/lab-03-approval-repository
title: "Lab 03 - Approval Repository and State Machine"
description: "Walk the DRAFT to PENDING_REVIEW to APPROVED/REJECTED state machine and prove self-approval is impossible."
---

> 🇫🇷 **[Version française](../fr/labs/lab-03-approval-repository.md)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 40 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 01](lab-01-fixtures-schema.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Describe the `ApprovalRepository` state machine: DRAFT, PENDING_REVIEW, APPROVED, REJECTED
* Explain why the reviewer of a case can never be the same person who prepared it
* Trigger and catch a `SelfApprovalError` yourself
* Confirm that revising a decided case resets it to DRAFT and clears the prior decision

## Exercises

### Exercise 3.1: Read the State Machine

Open `apps/workshop/approval_repository.py` and read the module docstring and the `ApprovalRepository` class. Identify:

* `create_draft` creates a case in `DRAFT` at revision 1
* `submit_for_review` moves `DRAFT` to `PENDING_REVIEW`
* `approve` and `reject` both call the private `_decide` method, which moves `PENDING_REVIEW` to `APPROVED` or `REJECTED`
* `revise` creates a new revision from any state, resetting it to `DRAFT` and clearing the reviewer and approval timestamp

### Exercise 3.2: Run the Existing Tests

```powershell
python -m pytest apps/workshop/tests/test_approval_repository.py -v
```

Expected result: every test passes, covering the full state machine and revision-invalidation behavior.

### Exercise 3.3 (Hands-on): Trigger a Self-Approval Rejection

Run this self-contained command from PowerShell. It creates a draft, rejects
self-approval, and then approves with a distinct reviewer. The process exits
after the command; its in-memory repository does not survive.

```powershell
python -c "
import sys
sys.path.insert(0, 'apps/workshop')
from approval_repository import ApprovalRepository, SelfApprovalError

repo = ApprovalRepository()
repo.create_draft('CASE-LAB-001', preparer_id='EMP-001')
repo.submit_for_review('CASE-LAB-001', actor_id='EMP-001')

try:
    repo.approve('CASE-LAB-001', reviewer_id='EMP-001')
    print('UNEXPECTED: self-approval succeeded')
except SelfApprovalError as exc:
    print(f'Blocked as expected: {exc}')

record = repo.approve('CASE-LAB-001', reviewer_id='EMP-002')
print(f'Approved by a distinct reviewer: state={record.state}')
"
```

Expected result: the first `approve` call raises `SelfApprovalError`. The second call, with a different `reviewer_id`, succeeds and reports `state=APPROVED`.

### Exercise 3.4 (Hands-on): Revise an Approved Case

Insert these Python lines inside the Exercise 3.3 command, immediately before
its closing double quote, then rerun the complete command:

```python
record = repo.revise('CASE-LAB-001', actor_id='EMP-001')
print(record.state, record.revision, record.reviewer_id, record.approved_at)
repo.close()
```

Expected result: `DRAFT 2 None None`. The prior approval no longer applies to
the new revision; the append-only audit retains the earlier decision.

## Validation Checklist

* [ ] `pytest apps/workshop/tests/test_approval_repository.py -v` passes
* [ ] You triggered and caught `SelfApprovalError` from a `reviewer_id` equal to the case's `preparer_id`
* [ ] A distinct `reviewer_id` approved the same case successfully
* [ ] `revise` after `APPROVED` reset the case to `DRAFT` and cleared the reviewer and approval timestamp

## Knowledge Check

* Why does `_decide` check `reviewer_id == record.preparer_id` before it checks the case's current state?
* What happens if you call `approve` twice in a row with the same `reviewer_id` on an already-approved case? Read `_decide` again if you are unsure.

## Next Steps

Continue to [Lab 04: The Application MCP Server](lab-04-application-server.md).
