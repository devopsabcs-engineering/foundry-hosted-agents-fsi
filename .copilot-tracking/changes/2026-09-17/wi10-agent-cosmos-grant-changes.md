<!-- markdownlint-disable-file -->
# Release Changes: WI-10 — Hosted Agent Cosmos Data-Plane Grant

**Related Plan**: wi10-agent-cosmos-grant-plan.instructions.md
**Implementation Date**: 2026-09-17

## Summary

Closing the staging half of WI-10: configure the `staging` GitHub Environment's
`AGENT_PRINCIPAL_ID` variable with the hosted agent's live Entra agent identity so
`infra/main.bicep`'s existing `cosmosAgentRbac` module manages the Cosmos grant, then
functionally confirm both staging and production hosted agents can write cases.

## Changes

### Added

* (pending)

### Modified

* (pending)

### Removed

* (pending)

## Additional or Deviating Changes

* Phase 1 (verification, no files changed): re-queried the staging Foundry project's
  `/agents?api-version=v1` endpoint. Live `instance_identity.principal_id` is
  `f6ef6272-c2db-45f7-9071-6667ae65a37d` (agent `quote-preparation-agent`, version 3),
  unchanged since research. `az ad sp show` still fails to resolve it (same error as
  research time, consistent with DD-01 in the planning log). Confirmed this principal
  already has a Cosmos SQL role assignment (`11e012aa-08b0-4e28-936a-f9111d869228`,
  Cosmos Data Contributor) on `cosmos-desjardins-quote-preparation-staging`. This is
  the confirmed target value for Phase 2's `AGENT_PRINCIPAL_ID` variable.
* Phase 2 (GitHub repository configuration, no repo files changed): created the
  `staging` GitHub Environment variable `AGENT_PRINCIPAL_ID` (previously unset, GET
  returned 404) with value `f6ef6272-c2db-45f7-9071-6667ae65a37d`, confirmed via a
  follow-up GET. `production`'s existing variable was left untouched.
* Phase 3 (BLOCKED, no files changed): dispatched `deploy-and-evaluate.yml` (run
  [35248376664](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/35248376664)).
  `Lint` and `Bicep validate and what-if` succeeded, but `Deploy candidate to staging`
  failed at "Build immutable staging MCP images" (`rulebook-mcp`, second loop
  iteration) due to a transient Docker Hub pull timeout inside the ACR remote-build
  agent — unrelated to the `AGENT_PRINCIPAL_ID`/Cosmos RBAC change. Every downstream
  step, including "Capture the Foundry project identity JSON (agent identity
  lookup)" and `azd provision`, was skipped as a result, so the staging Cosmos grant
  was NOT re-applied via IaC in this run. No production approval gate was reached or
  interacted with. Cosmos role assignments on staging remain unchanged (still exactly
  one assignment, `11e012aa-08b0-4e28-936a-f9111d869228`, for the target principal) —
  this reflects pre-existing state, not confirmation from this run.
* Phase 3 retry (BLOCKED, no files changed, user-approved re-dispatch): run
  [35249247909](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/35249247909).
  MCP/reviewer image builds succeeded this time (prior transient timeout resolved),
  but `azd provision` inside "Provision staging infrastructure (idempotent)" failed
  on all 3 internal retries with an ARM `BadRequest`:
  `The provided principal ID [f6ef6272-c2db-45f7-9071-6667ae65a37d] was not found in
  the AAD tenant(s) [aa93b9d9-037d-4f08-a26d-783cff0e2369]`. This is a **non-transient**
  failure and directly contradicts research's DD-01 finding that Cosmos SQL role
  assignments don't validate `principalId` against Entra at write time — see planning
  log DD-03. "Capture the Foundry project identity JSON" and every downstream step
  were skipped as a result. Per the plan's Step 4.3 escalation clause, no further
  automated retry was attempted; stopped and reported to the user for a decision.
* Further root-cause investigation (no files changed, no new deploy triggered, at
  user's direction to keep investigating): confirmed via the ARM error's
  `ActivityId` line that the failure originates from
  `Microsoft.Azure.Documents.Common/2.14.0` (the Cosmos DB resource provider itself)
  — `infra/main.bicep` has only one RBAC resource tied to `agentPrincipalId` (the
  `cosmosAgentRbac` module), ruling out a separate classic role assignment as the
  real culprit. Re-checked resolution via four additional Graph query paths
  (`az ad sp show`, `directoryObjects/{id}`, beta `servicePrincipals/{id}`, a
  `$filter` query, and an eventual-consistency `$search` query) — all still 404 for
  `f6ef6272-c2db-45f7-9071-6667ae65a37d`, ruling out an API-version or single-cache
  quirk. Cross-checked production's currently-configured, working identity
  (`171dca8a-bda3-46ec-8121-a235ecee6e30`) — it resolves fine via `az ad sp show`
  (`displayName` ends in `-AgentIdentity`), confirming agent identities do become
  classic-resolvable service principals once propagated; this isn't an
  architectural exclusion. Production's Cosmos account carries 3 role assignments:
  2 duplicates for the working identity plus 1 orphaned assignment for an older,
  different principal (`c6ab63bf-914a-4f0e-a65b-5d17a7876823`). Re-examined
  `.copilot-tracking/changes/2026-09-15/private-networking-changes.md`: production
  hit this exact same ARM error on 2026-09-15 for a **different** GUID
  (`4fcc9b60-d117-4d6c-912a-a3e206270403`) than its current working value — meaning
  production's fix was a changed/newer identity value becoming available, not the
  same value eventually resolving. Staging has no newer identity available from the
  agents API (still `f6ef6272-...`, version 3, unchanged since research).
  **Conclusion**: this is Entra Agent ID propagation/replication lag on the
  directory side, not an auth, permission, or code defect — no interactive login or
  MFA action can fix it, since the same access token successfully resolves other
  principals (including production's). No further remediation is available from
  this session; recommended path is to wait a longer interval (hours) before
  retrying Phase 3, rather than continuing to re-dispatch the full staging pipeline.
* Phase 4.1 (production only, no files changed): per the user's decision to proceed
  with production validation now and revisit staging later, queried production's
  Application Insights via its Log Analytics workspace
  (`log-desjardins-quote-preparation-poc`) for the last 7 days of Cosmos dependency
  traces. Result: 63 total calls, 0 failures, including
  `POST /dbs/quote-preparation/colls/cases/docs/` (9/9 success) and
  `PUT .../docs/CASE-SYN-001|002|004/` (1/1 success each — genuine case writes),
  most recent 2026-09-17T13:19:03Z. This functionally confirms production's hosted
  agent can and does write cases to Cosmos using its existing grant, satisfying
  Step 4.1 for production without needing to trigger new test traffic. Staging's
  Step 4.1 remains pending, blocked on Phase 3.

## Release Summary

(pending — completed after final phase)
