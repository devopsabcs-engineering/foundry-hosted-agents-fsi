---
permalink: /labs/lab-13-reviewer-ui
title: "Lab 13 - The Reviewer UI"
description: "Seed a local case queue, sign in as a reviewer, approve a case, and read the audit trail the decision leaves behind."
---

> 🇫🇷 **[Version française](../fr/labs/lab-13-reviewer-ui)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 50 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 12](lab-12-reviewer-identity.md) completed against a tenant you can sign in to |

In Lab 07 you played the reviewer by calling `ApprovalRepository.approve` from a Python one-liner. This lab replaces that with the interface a reviewer actually uses.

Exercises 13.1 through 13.10 run on your workstation using SQLite when no
Cosmos endpoint is configured. Hosted-agent resubmission in Exercise 13.11
requires an approved deployment and the shared Cosmos store; it does not
silently fall back to a local calculator in the reviewer app.

> [!NOTE]
> The reviewer interface includes a manual EN/FR toggle in the header, matching the applicant-facing chat. Every label, message, and the fixed disclaimer render in whichever language the toggle selects, and the choice persists in the browser between visits.

## Learning Objectives

By the end of this lab, you will be able to:

* Seed a local case queue from the checked-in fixtures
* Run the reviewer app against your real Entra registration
* Read a case whose calculation produced no amount
* Approve a case and read the audit entry the decision writes
* Explain why the reviewer identity in the audit trail is an object ID

## Exercises

### Exercise 13.1: Read the Case Store Fallback

```powershell
Select-String -Path src/quote-preparation-agent/case_store.py -Pattern "def build_case_store" -Context 0,12
```

Expected result: the factory returns a Cosmos-backed store when `COSMOS_ENDPOINT` is set and a SQLite store otherwise, defaulting to `:memory:` unless `CASE_STORE_DB_PATH` names a file.

That fallback makes local persistence possible without the Azure data plane.
Real Entra sign-in still needs connectivity. The app uses the same store protocol.

### Exercise 13.2 (Hands-on): Seed the Queue

`scripts/seed_review_queue.py` walks the same two store commands the agent's composition node walks, `create_draft` followed by `submit_for_review_with_calculation`, against the real deterministic calculator and the checked-in fixtures. Every amount it writes comes from `calculate_quote` reading a fixture rulebook. None is a literal in the script.

```powershell
python scripts/seed_review_queue.py --db-path .local/reviewer-cases.db
```

Expected result: five cases, each reported with its state and calculation status.

```text
CASE-SYN-001: PENDING_REVIEW, calculation READY, 100000 cents
CASE-SYN-002: PENDING_REVIEW, calculation READY, 90000 cents
CASE-SYN-003: PENDING_REVIEW, calculation UNSUPPORTED, no amount
CASE-SYN-004: PENDING_REVIEW, calculation READY, 110000 cents
CASE-SYN-005: PENDING_REVIEW, calculation INCOMPLETE, no amount
```

Two of the five carry no amount. That is deliberate. A queue where every row is priced would not exercise the case the interface most needs to get right.

The script is safe to re-run: a case that already exists is skipped rather than duplicated.

### Exercise 13.3 (Hands-on): Build and Run the Reviewer App

At the repository root, reactivate the Lab 00 environment. These commands
install the backend dependencies and finish in `apps/reviewer-app`:

```powershell
python -m pip install -r apps/reviewer-app/requirements.txt
cd apps/reviewer-app/frontend
npm ci
npm test
npm run build
cd ..
```

Expected result: frontend tests pass and a bundle is written to `frontend/dist`.
The build parses JSX as well as resolving imports; a plain JavaScript syntax
check is not a replacement.

Start the backend with your real client ID from Lab 12:

```powershell
$env:ENTRA_TENANT_ID = '<your-tenant-id>'
$env:REVIEWER_CLIENT_ID = '<reviewer-client-id>'
$env:ENVIRONMENT = 'local'
$env:COSMOS_ENDPOINT = ''
$env:CASE_STORE_DB_PATH = (Resolve-Path ../../.local/reviewer-cases.db).Path
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8100
```

Expected result: `Application startup complete`. Setting `COSMOS_ENDPOINT` to an empty string forces the SQLite branch even if a Cosmos endpoint happens to be exported in your shell.

```powershell
# In a second terminal
Invoke-WebRequest -Uri 'http://127.0.0.1:8100/api/config' -UseBasicParsing | Select-Object -ExpandProperty Content
```

Expected result: JSON carrying the tenant ID, client ID, the `Review.Access` scope, the `Reviewer` role, and an environment of `local`.

### Exercise 13.4 (Hands-on): Sign In

Open `http://localhost:8100` in a browser.

> [!IMPORTANT]
> Use `localhost`, not `127.0.0.1`. They are different origins, and only `http://localhost:8100` is a registered redirect URI.

![The reviewer app before sign-in, showing the Foundry Case Review brand, a Local Pilot badge, the heading "Reviews start with access.", an amber training-simulation notice, and a Sign in with Microsoft button]({{ "/assets/images/reviewer-sign-in.png" | relative_url }})

Expected result: an access gate with no case data behind it. Sign in with an account you added to the reviewer group in Lab 12.

If Entra rejects the sign-in, the message tells you which step of Lab 12 to revisit. A redirect URI mismatch is a registration problem. A message about the application not being assigned to a user is the `appRoleAssignmentRequired` flag doing its job.

### Exercise 13.5: Read the Queue

The screenshots preserve the English view. Use the header EN/FR selector
to inspect the current French labels too. Do not use **Clear queue** on
retained shared environments; destructive deletion is not this exercise.

![The reviewer queue listing five pending cases with columns for case, state, revision, preparer, submitted time, and premium; two rows read Not priced]({{ "/assets/images/reviewer-queue.png" | relative_url }})

Expected result: five rows in `PENDING_REVIEW`. Three show a premium in CAD. Two show `Not priced` with the reason underneath, `unsupported` for CASE-SYN-003 and `incomplete` for CASE-SYN-005.

The preparer on every row is `AGENT-INTAKE`. No row has a reviewer yet.

### Exercise 13.6 (Hands-on): Open a Priced Case

Select CASE-SYN-001.

![The detail view for CASE-SYN-001 showing state PENDING_REVIEW, a premium of CAD 1,000.00 per training year, rule ids, rulebook version training-1, three decision buttons, and a two-entry audit trail]({{ "/assets/images/reviewer-case-detail.png" | relative_url }})

Expected result: the calculation panel shows the premium, the currency, the period, a status of `READY`, the rule IDs that produced the figure, and the rulebook version.

This is the amount the applicant never saw in Lab 11. Note what accompanies it: a reviewer is not shown a number in isolation but the rule IDs and rulebook version that generated it, which is what makes the figure checkable rather than merely readable.

The audit trail already has two entries, `CREATE_DRAFT` and `SUBMIT`, both attributed to `AGENT-INTAKE`.

### Exercise 13.7 (Hands-on): Open an Unpriced Case

Return to the queue and select CASE-SYN-003.

![The detail view for CASE-SYN-003 showing Not priced with reason unsupported, a status of UNSUPPORTED, no rule ids, and an issue of UNSUPPORTED_INPUT]({{ "/assets/images/reviewer-case-not-priced.png" | relative_url }})

Expected result: the premium reads `Not priced`, the status is `UNSUPPORTED`, the rule IDs are `None`, and the issues field names `UNSUPPORTED_INPUT`.

The decision buttons remain enabled. A reviewer can still act on a case the calculator declined to price, which is the correct behaviour: an unpriceable case still needs a human outcome rather than being stranded in the queue.

### Exercise 13.8 (Hands-on): Approve a Case

Return to CASE-SYN-001 and select Approve.

![The confirmation step for approving CASE-SYN-001, reading that approving records the premium decision and cannot be undone, with Confirm approve and Cancel buttons]({{ "/assets/images/reviewer-approve-confirm.png" | relative_url }})

Expected result: confirmation before a write. The decision remains in the audit
trail. A later revision resets the case to `DRAFT` and invalidates approval for
the new revision; it does not erase the original audit entry.

Reject and Send back for revision also confirm, but they additionally offer an optional reason code. Approve does not, because an approval is not a finding that needs explaining.

Confirm it.

![CASE-SYN-001 after approval, showing a banner reading recorded as APPROVED, a reviewer object ID, a decision section stating the case can no longer be decided, and a third audit entry for APPROVE]({{ "/assets/images/reviewer-case-approved.png" | relative_url }})

Expected result: the state becomes `APPROVED`, the reviewer field fills with an object ID, the decision buttons are replaced by a sentence explaining the case can no longer be decided, and a third audit entry appears recording the `PENDING_REVIEW` to `APPROVED` transition against your identity.

### Exercise 13.9: Read the Audit Trail

Compare the three entries. The first two name `AGENT-INTAKE`. The third names a GUID.

That GUID is your Entra object ID, taken from the verified token's `oid` claim rather than from anything the browser sent. A display name can change and an email address can be reassigned, but an object ID is stable for the life of the account, which is the property an audit record needs.

The separation you enforced in Lab 03 is now visible end to end: the identity that prepared the case and the identity that decided it are different, and both are recorded.

Check the server log in your uvicorn terminal:

```text
reviewer_decision command=approve case=CASE-SYN-001 revision=1 reason=None
```

Expected result: a structured decision line accompanying the HTTP request log. The decision is recorded in the case store and in the application log.

### Exercise 13.10: Clean Up the Local Database

```powershell
# In the terminal running uvicorn
Ctrl+C
```

```powershell
# Back at the repository root after stopping uvicorn
cd ../..
Remove-Item .local/reviewer-cases.db -Force
```

The `.local/` directory is in `.gitignore`, so the seeded database is never committed. Re-run Exercise 13.2 whenever you want a fresh queue.

### Exercise 13.11: Correct and Resubmit a Returned Draft

Run this optional exercise only after an approved release containing
[issue #28](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/28).
Use an authorized synthetic staging case, not a shared customer-demo case
without coordination. Do not clear the queue or change the fixture.

1. Open `CASE-SYN-005`, which initially has `INCOMPLETE`, `MISSING_PLAN`
   and no amount. Select **Send back for revision** with reason `MISSING_PLAN`.
2. Confirm revision 2 is `DRAFT`, and return to the active queue. The draft
   must still be visible. Reopen it and inspect the current audit trail.
3. Supply `TRAINING_BASIC` in the correction form, then request preparation.
   Jurisdiction/vehicle fields may be left unchanged. Values are constrained;
   there is no price editor or arbitrary JSON input.
4. Confirm the native hosted agent returns the **same revision 2** to
   `PENDING_REVIEW`, calculation `READY`, `80000` synthetic cents.
   `TRAINING_EXTENDED` would produce `100000` cents with the same fixture.
5. Inspect `PREPARATION_REQUESTED` and `PREPARATION_COMPLETED`: corrections,
   employee identity, hashed correlation, native response ID and calculation
   provenance. Refresh and revisit the queue: revision and audit must agree.
6. Confirm the correcting employee cannot approve this revision. Another
   authorized employee must decide it. Check the French labels too.

On failure, refresh before retrying. Corrections remain on the visible draft
with a failed audit event. An abandoned in-progress request can be retried
after its 240-second lease; new attempts use a fresh request key. Previous
calculations on a draft are historical, not a new quote.

The deployed reviewer API requires `AGENT_ENDPOINT` pointing to the native
Responses endpoint and a project-scoped invocation-only managed-identity role,
in addition to Cosmos access. Infrastructure supplies both declaratively.
An unconfigured local endpoint returns 503 without submitting anything.
The reviewer never calls `approve`, `reject` or `revise` through the agent.

Offline regression coverage, without touching deployed cases:

```powershell
python -m pytest src/quote-preparation-agent/tests/test_case_store_contract.py src/quote-preparation-agent/tests/test_graph.py -q
python -m pytest apps/reviewer-app/tests -q
```

## Validation Checklist

* [ ] Five cases were seeded, two of them without an amount
* [ ] `npm test` and `npm run build` succeed in `apps/reviewer-app/frontend`
* [ ] `/api/config` reports the `Reviewer` role and an environment of `local`
* [ ] You signed in through `http://localhost:8100` and reached the queue
* [ ] CASE-SYN-001 shows a premium, rule IDs, and a rulebook version
* [ ] CASE-SYN-003 shows `Not priced` with its issue named
* [ ] Approving CASE-SYN-001 wrote a third audit entry carrying your object ID
* [ ] On an approved hosted build, returned drafts remain visible and a corrected revision retains its current audit

## Knowledge Check

* Why does the reviewer app work with no Cosmos endpoint configured?
* Why does the audit trail store an object ID instead of a display name?
* Why are the decision buttons enabled on a case the calculator could not price?
* The applicant saw no amount in Lab 11 and you saw one here. Where in the pipeline does that divergence originate?
* Why does approval offer no reason code when reject and revision both do?

## Next Steps

Continue to [Lab 14: Pilot Operations](lab-14-pilot-operations.md).
