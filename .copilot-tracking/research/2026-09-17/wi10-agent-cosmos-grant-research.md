<!-- markdownlint-disable-file -->
# Research: WI-10 — Hosted Agent's Cosmos Data-Plane Grant (`AGENT_PRINCIPAL_ID`)

## Scope

WI-10, tracked in `.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md`
and originally in `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`: the hosted
agent's own Microsoft Entra "agent identity" needs a Cosmos DB data-plane grant
(`modules/cosmos-rbac.bicep`) so it can write review cases, distinct from the
Foundry *project's* system-assigned identity (already fixed for Foundry User in
commit `3e6520b`, unrelated to this item). This document captures the live-state
investigation performed instead of guessing, since two prior sessions already
recorded conflicting/incomplete state for this exact variable
(`.copilot-tracking/changes/2026-09-15/private-networking-changes.md`,
`.copilot-tracking/plans/logs/2026-09-15/workshop-ui-labs-log.md`).

## How the repo already models this (no code gap found)

* `infra/main.bicep` (`agentPrincipalId` param, ~line 119; `cosmosAgentRbac` module,
  ~line 248): grant is conditional on `!empty(agentPrincipalId)`, correctly wired,
  serialized after `cosmosReviewerRbac` (Cosmos data-plane writes 409 if concurrent).
* `infra/modules/cosmos-rbac.bicep`: creates
  `Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments` scoped to the account,
  role `00000000-0000-0000-0000-000000000002` (Cosmos DB Built-in Data Contributor).
  **Important**: Cosmos SQL role assignments do NOT validate `principalId` against
  Entra at write time (unlike `Microsoft.Authorization/roleAssignments`). An assignment
  for a principal that doesn't resolve in Entra still deploys successfully and then
  fails only at data-plane auth time — this is why `deploy-and-evaluate.yml` added its
  own defensive `az ad sp show` pre-check (see below) rather than relying on ARM to
  reject a bad value.
* `.github/workflows/deploy-and-evaluate.yml`, step "Capture the Foundry project
  identity JSON (agent identity lookup)" (~line 322-410, both in `deploy-staging` and
  `promote-production` jobs): already does everything by design —
  1. Queries the project's `/agents?api-version=v1` data-plane endpoint for
     `versions.latest.instance_identity.principal_id` (the "live" agent identity).
  2. Checks it resolves via `az ad sp show`; if not, warns and refuses to recommend it.
  3. Compares the live value against the configured `AGENT_PRINCIPAL_ID` and writes a
     human-readable verdict to `$GITHUB_STEP_SUMMARY` (only visible in the Actions UI
     Summary tab, NOT retrievable via `gh api .../jobs/<id>/logs` — confirmed empirically
     this session, since `>> "$GITHUB_STEP_SUMMARY"` never touches stdout).
  4. Never auto-applies the value — by design, to avoid granting Cosmos access to the
     wrong principal (see WI-10 comment at that step, and the git history rationale in
     `private-networking-changes.md`).
  * Conclusion: **there is no missing code/Bicep change for WI-10.** The remaining work
    is purely operational: read the live value, confirm it's trustworthy, set it as a
    GitHub Environment variable, and redeploy so `azd provision` applies the grant.

## Variable scope: `AGENT_PRINCIPAL_ID` is per-GitHub-Environment, not repo-wide

Both `deploy-staging` (`environment: staging`) and `promote-production`
(`environment: production`) jobs read `${{ vars.AGENT_PRINCIPAL_ID }}`. GitHub Actions
resolves `vars.*` from the job's Environment first, falling back to the repository
level only if no environment-scoped variable of that name exists. Confirmed via API
(`gh api repos/.../environments/<env>/variables`):

| Scope | `AGENT_PRINCIPAL_ID` present? |
|---|---|
| Repository-level | No |
| `staging` environment | **No** — this is the actual gap |
| `production` environment | **Yes**, value `171dca8a-bda3-46ec-8121-a235ecee6e30` (set 2026-09-16) |

So the two environments are independently configured, and only staging is missing
the variable. Production is not the blocked one, contrary to what a repo-wide reading
of the changes log might suggest.

## Production: already resolved, verified end-to-end (no action needed)

* `az ad sp show --id 171dca8a-bda3-46ec-8121-a235ecee6e30` resolves:
  `displayName: aif-desjardins-quote-preparation-poc-proj-desjardins-quote-preparation-poc-quote-preparation-agent-AgentIdentity`.
* `az cosmosdb sql role assignment list --account-name cosmos-desjardins-quote-preparation-poc
  --resource-group rg-desjardins-quote-preparation` shows a live assignment for this exact
  principal (assignment name `bfe58d42-e8ee-5c32-b369-7670f7a20a58`), alongside the
  reviewer app's own grant (`c6ab63bf-914a-4f0e-a65b-5d17a7876823`) and a second,
  functionally-redundant assignment for the same agent principal
  (`40683a67-6907-4c86-b6f1-f78b254f52d2` — likely a leftover from a manual grant made
  before the environment variable was set durably; harmless, same role/scope/principal).
* Both of today's `promote-production` runs (`35235911956`, `35238867109`) re-ran
  `azd provision --no-prompt` against production with this variable already configured,
  so the grant is live and IaC-managed today. **Production requires no further action**
  beyond an optional cleanup of the duplicate assignment (see Suggested Follow-On Work
  in the plan).

## Staging: variable unset, but a matching Cosmos grant unexpectedly already exists

* Live agent identity right now (via direct query against the staging project's Foundry
  data-plane endpoint, same technique the workflow step uses):
  `GET https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging/agents?api-version=v1`
  → `data[0].versions.latest.instance_identity.principal_id = f6ef6272-c2db-45f7-9071-6667ae65a37d`
  (agent `quote-preparation-agent`, version `3`, status `active`).
* `az ad sp show --id f6ef6272-c2db-45f7-9071-6667ae65a37d` **fails** (checked twice):
  `Resource ... does not exist or one of its queried reference-property objects are not
  present.` This is the exact failure mode the workflow's defensive check anticipates
  and would currently block an operator from configuring this value through the
  documented path.
* Despite that, `az cosmosdb sql role assignment list --account-name
  cosmos-desjardins-quote-preparation-staging --resource-group
  rg-desjardins-quote-preparation` **already shows a live assignment for this exact
  principal** (assignment name `11e012aa-08b0-4e28-936a-f9111d869228`), alongside the
  reviewer app's grant (`44472dba-3cb1-4561-8fd8-40b41716e6ce`).
* Today's two staging deploys both ran with `AGENT_PRINCIPAL_ID` empty (confirmed in
  job logs: `azd env set AGENT_PRINCIPAL_ID ""`), so neither created or touched this
  assignment — it predates today's runs and was not created by Bicep on this branch's
  current commit. Its exact origin (manual `az cosmosdb sql role assignment create`
  during the 2026-09-15 private-networking session, or an earlier now-untracked
  `azd provision` run with a since-cleared variable) could not be confirmed from
  available history and is not required to proceed.

## Why `az ad sp show` fails for a seemingly-live, already-granted identity

Not fully resolved — documented as an open question rather than guessed at:

* Microsoft's own docs (`learn.microsoft.com/azure/ai-foundry/agents/concepts/agent-identity`,
  fetched this session) describe agent identities as "a specialized identity type in
  Microsoft Entra ID" viewable through a **separate** Entra admin blade
  ("Entra ID > Agent ID > All agent identities"), distinct from classic App
  registrations/Enterprise apps/service principals. This strongly suggests the newer
  "Agent ID" object type may not always be resolvable through the classic
  `servicePrincipals` Graph query that `az ad sp show` performs, independent of whether
  the identity is otherwise valid and already able to receive/use RBAC grants.
* This does not fully explain why *production's* agent identity (`171dca8a...`,
  same "AgentIdentity" object family, same tenant) resolves fine while staging's does
  not. Possible explanations not confirmed: Graph read-replica propagation lag right
  after a fresh `azd deploy` (today's staging redeploy is minutes old; production's
  value is a day old), or a difference between the object types created for
  "hosted"/new-object-model agents at different points in the Foundry service rollout.
* Practical implication for the plan: since Cosmos SQL role assignments do not validate
  the principal against Entra, setting `AGENT_PRINCIPAL_ID` to a value that doesn't yet
  resolve via `az ad sp show` cannot break the deployment (`azd provision` will not
  reject it) — the only risk is granting the wrong principal, which is already
  mitigated by cross-checking the value against the same live agents-API query the
  workflow itself uses, not by requiring `az ad sp show` success first.

## Existing repo-documented precedent for this exact failure mode

`.copilot-tracking/changes/2026-09-15/private-networking-changes.md` ("Both configured
agent principals were dead" and "The production agent identity does not resolve in
Entra at all") describes this identical symptom occurring for both environments during
the prior network rebuild, and states the production agent identity eventually became
resolvable after some elapsed time (its currently-configured value dates to
2026-09-16, one day after that investigation) — supporting the propagation-lag
explanation over a fundamentally broken identity for staging's current value.

## Sources

* `infra/main.bicep` (lines ~100-260), `infra/modules/cosmos-rbac.bicep`,
  `infra/modules/rbac.bicep`, `infra/main.parameters.json`.
* `.github/workflows/deploy-and-evaluate.yml` (lines ~150-420, ~640-660).
* `.github/workflows/network-rebuild-teardown.yml` (line ~385).
* `.copilot-tracking/changes/2026-09-15/private-networking-changes.md`,
  `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`,
  `.copilot-tracking/plans/logs/2026-09-15/workshop-ui-labs-log.md`.
* Live Azure state (this session, 2026-09-17): `gh api .../environments/{staging,production}/variables`,
  `az ad sp show`, `az cosmosdb sql role assignment list`, direct `curl` to the Foundry
  project's `/agents?api-version=v1` data-plane endpoint for both environments.
* `learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/agent-identity` (fetched
  this session) — agent identity vs. agent identity blueprint vs. project managed
  identity terminology, shared-vs-distinct identity model, "Agent ID" Entra admin blade.
