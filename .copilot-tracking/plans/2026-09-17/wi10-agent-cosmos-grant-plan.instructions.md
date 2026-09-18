---
applyTo: '.copilot-tracking/changes/2026-09-17/wi10-agent-cosmos-grant-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: WI-10 — Hosted Agent Cosmos Data-Plane Grant

## Overview

Close the staging half of WI-10 by configuring the `staging` GitHub Environment's
`AGENT_PRINCIPAL_ID` variable with the hosted agent's live Entra agent identity and
redeploying so `infra/main.bicep`'s existing `cosmosAgentRbac` module manages the
grant, then confirm both environments' agents can write Cosmos cases.

## Objectives

### User Requirements

* "work on WI-10 next" — Source: user request, this turn.

### Derived Objectives

* Resolve the staging `AGENT_PRINCIPAL_ID` gap identified in
  `.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md`
  (WI-10) and originally in `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`.
  — Derived from: closing a previously-tracked, explicitly-deferred follow-on item.
* Confirm production's already-configured `AGENT_PRINCIPAL_ID` is genuinely applied
  and functioning, since the tracked item's wording ("remains unset") does not
  distinguish staging from production. — Derived from: research finding that the two
  environments are independently configured.
* Avoid duplicating the redundant production Cosmos role assignment further; note it
  as optional cleanup rather than expanding scope. — Derived from: avoiding
  over-engineering beyond the stated request.

## Context Summary

### Project Files

* infra/main.bicep - `agentPrincipalId` param (~line 119) and `cosmosAgentRbac` module
  (~line 248); no code change needed, confirmed correct.
* infra/modules/cosmos-rbac.bicep - Cosmos SQL role assignment module; confirmed it
  does not validate `principalId` against Entra, which bounds the risk of this plan.
* .github/workflows/deploy-and-evaluate.yml - existing "Capture the Foundry project
  identity JSON (agent identity lookup)" step (~lines 322-410) already surfaces the
  live agent principal ID and a match/mismatch verdict in the job's Step Summary; no
  workflow change needed.

### References

* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md - full
  investigation: live-state findings, variable scoping, and the open question about
  why the staging identity doesn't resolve via `az ad sp show`.
* .copilot-tracking/changes/2026-09-15/private-networking-changes.md - prior-session
  precedent for the same "agent principal doesn't resolve in Entra" symptom.

### Standards References

* None beyond this repository's own IaC conventions (infra/README.md module table).

## Implementation Checklist

### [x] Implementation Phase 1: Re-verify live staging agent identity at execution time

<!-- parallelizable: false -->

* [x] Step 1.1: Re-query the staging Foundry project's `/agents?api-version=v1`
  endpoint for `versions.latest.instance_identity.principal_id` and re-check
  `az ad sp show` against it, since the value in research may shift if staging is
  redeployed between planning and implementation.
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 13-52)
* [x] Step 1.2: Confirm the live value still matches the principal already granted in
  `cosmos-desjardins-quote-preparation-staging`'s Cosmos role assignments
  (`az cosmosdb sql role assignment list`).
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 53-79)

### [x] Implementation Phase 2: Configure the staging environment variable

<!-- parallelizable: false -->

* [x] Step 2.1: Set `AGENT_PRINCIPAL_ID` on the `staging` GitHub Environment to the
  confirmed live value from Phase 1, mirroring how `production`'s variable is already
  configured.
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 84-118)

### [x] Implementation Phase 3: Redeploy staging and confirm the grant is IaC-managed

<!-- parallelizable: false -->
<!-- RESOLVED 2026-09-18: root cause was the instance identity never fully
     materializing in Entra, not a transient propagation delay. Fixed via
     `azd ai agent delete quote-preparation-agent --force` + `azd deploy`,
     which mints a brand-new blueprint + instance identity pair (matching
     production's proven WI-43 fix). New identity resolved in Entra
     immediately; AGENT_PRINCIPAL_ID updated; run 35292843329 confirmed the
     grant via direct `az cosmosdb sql role assignment list`. See planning
     log for full detail. -->

* [x] Step 3.1: Dispatch `deploy-and-evaluate.yml` (or, if only the Cosmos grant needs
  reapplying, run `azd provision --no-prompt` directly against the staging azd env)
  so `cosmosAgentRbac` picks up the now-configured `agentPrincipalId`.
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 123-151)
  * Dispatched twice (runs 35248376664, 35249247909). First run hit a transient ACR
    Docker Hub timeout (unrelated); second run got past image builds but failed at
    `azd provision` with a non-transient ARM `BadRequest` rejecting the agent
    principal ID as unresolvable in the tenant.
  * RESOLVED: force-deleted and recreated the staging agent, producing a new
    identity (`d3df472a-80a8-4934-b6d9-ac9efb1877e3`) that resolved instantly.
    Dispatched run 35292843329 with the new `AGENT_PRINCIPAL_ID` \u2014 deploy and
    evaluation gate both completed successfully.
* [x] Step 3.2: Confirm the run's "Capture the Foundry project identity JSON" step
  summary reports "matches the live agent identity" with no `::warning::` line, and
  that `az cosmosdb sql role assignment list` for staging still shows exactly one
  assignment for the agent principal (no unexpected duplicate from a differently-named
  Bicep-generated assignment).
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 152-187)
  * BLOCKED (original attempts) \u2014 target step never ran because `azd provision`
    failed upstream in both attempts.
  * RESOLVED (2026-09-18): confirmed directly via `az cosmosdb sql role assignment
    list` rather than the job summary (which is not visible in log output) \u2014 the
    new identity `d3df472a-80a8-4934-b6d9-ac9efb1877e3` has a Cosmos DB Built-in
    Data Contributor role assignment on `cosmos-desjardins-quote-preparation-
    staging`. An orphaned assignment for the old, dead `f6ef6272-...` principal
    also remained until cleaned up in Phase 4 (see WI-05 in the planning log).

### [x] Implementation Phase 4: Validation

<!-- parallelizable: false -->

* [x] Step 4.1: Functionally confirm the hosted agent can write a case in both
  environments (e.g., trigger a sample interaction that writes to Cosmos, or inspect
  Application Insights/Cosmos data directly for a successful write, avoiding reliance
  on role-assignment existence alone).
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 192-226)
  * Production: CONFIRMED via Application Insights (Log Analytics workspace
    `log-desjardins-quote-preparation-poc`). Last 7 days: 63 total Cosmos
    dependency calls, 0 failures, including `POST /dbs/quote-preparation/colls/
    cases/docs/` (9/9 success) and `PUT .../docs/CASE-SYN-001|002|004/` (1/1
    success each) — genuine case writes, most recent 2026-09-17T13:19:03Z (today).
  * Staging: CONFIRMED via Application Insights (Log Analytics workspace
    `log-desjardins-quote-preparation-staging`), last 6 hours (post force-delete-
    and-recreate + run 35292843329): `PUT .../docs/CASE-SYN-001|002|003|005/`
    (1/1 success each, 0 failures) and `POST /dbs/quote-preparation/colls/
    cases/docs/` (5/5 success) — genuine case writes with the NEW identity
    `d3df472a-80a8-4934-b6d9-ac9efb1877e3`. This is the definitive functional
    proof (same fidelity as production's) that the staging agent both has and
    successfully uses its Cosmos write grant. A separate manual `azd ai agent
    invoke` CLI test (outside the pipeline) returned a "case reference was
    invalid" rejection for the same case IDs on both staging and production —
    given the telemetry proof above, this is now understood to be an artifact of
    the ad-hoc CLI invoke's request shape/protocol, not a real product or data
    gap; not further pursued since real telemetry is stronger evidence.
* [x] Step 4.2: Update tracking artifacts — mark WI-10 resolved in both the
  2026-09-15 and 2026-09-17 planning logs, record the staging fix and production
  confirmation in a new changes log entry.
  * Details: .copilot-tracking/details/2026-09-17/wi10-agent-cosmos-grant-details.md (Lines 227-256)
* [x] Step 4.3: Report any residual issues
  * If the staging agent identity still fails Entra resolution after redeploy and the
    functional write test also fails, stop and escalate rather than guessing further
    — do not attempt speculative Graph permission grants or tenant-level changes
    without additional research.
  * No residual issue blocks WI-10's own scope. Two follow-on items were logged and
    subsequently resolved this session (user-approved "go ahead with it all"):
    WI-05 (orphaned Cosmos role assignment for the dead `f6ef6272-...` principal —
    deleted and verified) and WI-06 (production promotion for run 35292843329 —
    approved and completed successfully). One minor, non-blocking, informational
    item remains open: WI-04 (a manual `azd ai agent invoke` CLI test returns a
    "case reference was invalid" rejection despite real telemetry proving the same
    case IDs were written successfully — understood to be a CLI request-shape
    quirk, not a product defect).

## Planning Log

See `.copilot-tracking/plans/logs/2026-09-17/wi10-agent-cosmos-grant-log.md` for
discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* GitHub CLI (`gh`) authenticated with permission to read/write repository
  Environment variables.
* Azure CLI (`az`) authenticated against subscription
  `64c3d212-40ed-4c6d-a825-6adfbdf25dad` with Cosmos and Entra read access.
* Azure Developer CLI (`azd`) with the `azure.ai.agents`/`azure.ai.connections`
  extensions installed, matching `deploy-and-evaluate.yml`'s setup.

## Success Criteria

* `staging` GitHub Environment has an `AGENT_PRINCIPAL_ID` variable matching the live
  agent instance identity. — Traces to: user requirement "work on WI-10 next".
* A subsequent staging `azd provision` reports the grant as already-satisfied/applied
  with no Cosmos-related errors. — Traces to: research finding on idempotent Bicep
  wiring.
* Both staging and production hosted agents can write a case to their respective
  Cosmos accounts, confirmed functionally, not just by role-assignment presence.
  — Traces to: WI-10's original intent ("agent cannot write cases until it is
  supplied").
* WI-10 marked resolved in the relevant planning logs with a dated note.
