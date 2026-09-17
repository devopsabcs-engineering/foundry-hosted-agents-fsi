<!-- markdownlint-disable-file -->
# Implementation Details: WI-10 — Hosted Agent Cosmos Data-Plane Grant

## Context Reference

Sources: .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md,
.copilot-tracking/changes/2026-09-15/private-networking-changes.md

## Implementation Phase 1: Re-verify live staging agent identity at execution time

<!-- parallelizable: false -->

### Step 1.1: Re-query the live agent instance identity and Entra resolution

Query the staging Foundry project's data-plane `/agents` endpoint the same way
`deploy-and-evaluate.yml`'s own "Capture the Foundry project identity JSON" step does,
then check the result against Entra:

```powershell
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
$endpoint = "https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging"
curl.exe -sS -H "Authorization: Bearer $token" "$endpoint/agents?api-version=v1" | python -m json.tool
# extract data[0].versions.latest.instance_identity.principal_id, then:
az ad sp show --id <principal_id> --query "{appId:appId, displayName:displayName, id:id}" -o json
```

At research time (2026-09-17), this returned `f6ef6272-c2db-45f7-9071-6667ae65a37d`
(agent `quote-preparation-agent`, version 3), which did not resolve via `az ad sp show`.
Re-run at implementation time in case staging was redeployed in between (a redeploy
does not change the agent identity unless the account itself was recreated, per
Microsoft's docs: "Agent identities persist as long as the associated Foundry project
... exists").

Files:
* None — read-only verification, no file changes.

Discrepancy references:
* Relates to DD-01 in the planning log (agent identity doesn't resolve via
  `az ad sp show` despite an existing working-looking Cosmos grant).

Success criteria:
* The live `instance_identity.principal_id` value is captured and recorded in the
  changes log for this step, whether or not it resolves via `az ad sp show`.

Context references:
* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md (Lines
  "Staging: variable unset, but a matching Cosmos grant unexpectedly already exists")
  - the exact command sequence and prior result being re-verified.

Dependencies:
* `az` CLI authenticated to subscription `64c3d212-40ed-4c6d-a825-6adfbdf25dad`.

### Step 1.2: Confirm the live identity matches the existing Cosmos grant

```powershell
az cosmosdb sql role assignment list --account-name cosmos-desjardins-quote-preparation-staging --resource-group rg-desjardins-quote-preparation -o table
```

Confirm the principal ID from Step 1.1 already appears in this list (as it did at
research time, assignment name `11e012aa-08b0-4e28-936a-f9111d869228`). If the live
identity has changed (e.g., a new agent version was deployed and its instance identity
differs), note the discrepancy — the existing Cosmos grant would then be for a stale,
no-longer-current agent identity and should be treated as informational only, not as
confirmation for the new value.

Files:
* None — read-only verification.

Success criteria:
* Documented match or mismatch between the live identity and the existing Cosmos
  grant, recorded in the changes log.

Context references:
* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md - full
  Cosmos role assignment listing captured this session for comparison.

Dependencies:
* Step 1.1 completion.

## Implementation Phase 2: Configure the staging environment variable

<!-- parallelizable: false -->

### Step 2.1: Set the `staging` environment's `AGENT_PRINCIPAL_ID` variable

```powershell
gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/environments/staging/variables/AGENT_PRINCIPAL_ID -X PATCH -f name=AGENT_PRINCIPAL_ID -f value=<confirmed_principal_id>
# or, if the variable does not yet exist under that name:
gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/environments/staging/variables -X POST -f name=AGENT_PRINCIPAL_ID -f value=<confirmed_principal_id>
```

Use the value confirmed in Phase 1 (expected `f6ef6272-c2db-45f7-9071-6667ae65a37d`
unless Phase 1 found a changed live identity). This mirrors the `production`
environment's existing configuration pattern exactly (same variable name, same
environment-scoped placement, confirmed via `gh api
repos/.../environments/production/variables/AGENT_PRINCIPAL_ID` returning a value).

Files:
* None — this is a GitHub repository configuration change, not a file in the repo.

Discrepancy references:
* Addresses DD-02 in the planning log (staging environment variable never configured,
  unlike production).

Success criteria:
* `gh api repos/.../environments/staging/variables/AGENT_PRINCIPAL_ID` returns the
  newly-set value.

Context references:
* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md (Lines
  under "Variable scope: `AGENT_PRINCIPAL_ID` is per-GitHub-Environment, not repo-wide")
  - confirms environment-scoped variables are the correct mechanism, not repository
  variables.

Dependencies:
* Phase 1 completion (confirmed value to set).
* `gh` CLI authenticated with `repo` scope sufficient to manage Environment variables.

## Implementation Phase 3: Redeploy staging and confirm the grant is IaC-managed

<!-- parallelizable: false -->

### Step 3.1: Trigger a staging provision with the new variable applied

Preferred: dispatch the full pipeline so both the variable and its downstream effects
are exercised the same way production's already was:

```powershell
gh workflow run deploy-and-evaluate.yml --repo devopsabcs-engineering/foundry-hosted-agents-fsi --ref main
```

This queues behind `concurrency: desjardins-quote-preparation-shared-environments` if
another run is in flight (see repo memory `/memories/repo/foundry-rbac-and-azdyaml.md`).
Confirm the resulting `deploy-staging` job's "Provision staging infrastructure" step
succeeds, which now runs with the configured `AGENT_PRINCIPAL_ID` populated at the
"Configure staging deployment environment" step (`azd env set AGENT_PRINCIPAL_ID
"${{ vars.AGENT_PRINCIPAL_ID }}"`).

Files:
* None — this dispatches an existing, unmodified workflow.

Success criteria:
* `deploy-staging` job completes with `conclusion: success`.

Context references:
* .github/workflows/deploy-and-evaluate.yml (lines ~150-300) - staging provision and
  deploy steps this dispatch exercises.

Dependencies:
* Phase 2 completion.

### Step 3.2: Confirm the grant is now IaC-managed with no duplicate or warning

After the run completes, check for the workflow's own defensive verdict and the
resulting Cosmos state:

```powershell
# Job log does not contain GITHUB_STEP_SUMMARY content; check for the ::warning:: annotation instead, which IS in job logs:
gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/jobs/<deploy-staging-job-id>/logs --allow-escape-sequences | Select-String -Pattern "::warning::.*AGENT_PRINCIPAL_ID|::warning::.*agent principal"

az cosmosdb sql role assignment list --account-name cosmos-desjardins-quote-preparation-staging --resource-group rg-desjardins-quote-preparation -o table
```

Expect no `::warning::` line referencing `AGENT_PRINCIPAL_ID` or "does not resolve in
Entra", and expect the Cosmos role assignment list to still show exactly one
assignment for the agent principal (Bicep's deterministic `guid(account.id,
principalId, roleDefinitionId)` naming should reuse the existing assignment if the
principal ID matches exactly what's already granted; if a second, differently-named
assignment for the same principal appears, note it as a minor, harmless duplicate
rather than a failure — same pattern already observed and accepted for production).

Files:
* None — read-only verification.

Success criteria:
* No RBAC/Cosmos-related warning or error in the job log.
* Exactly one (or, if a harmless duplicate, clearly identified as such) Cosmos role
  assignment for the agent principal in staging.

Context references:
* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md (Lines
  under "Production: already resolved, verified end-to-end") - the accepted pattern
  for a harmless duplicate assignment, used as the comparison baseline.

Dependencies:
* Step 3.1 completion.

## Implementation Phase 4: Validation

<!-- parallelizable: false -->

### Step 4.1: Functionally confirm the agent can write a case

Do not rely on role-assignment presence alone (Cosmos SQL role assignments do not
validate the principal, so a "successful" assignment proves nothing about actual
write capability). Prefer one of:

* Invoke the deployed hosted agent with a request that exercises its case-writing tool
  path (per `src/quote-preparation-agent`'s case-store integration) and confirm a new
  document appears in the staging Cosmos container.
* If a direct agent invocation is impractical in this pass, inspect Application
  Insights (`eastus2-3.in.applicationinsights.azure.com`, per the agent's environment
  variables captured in the live `/agents` response) for the most recent case-write
  dependency/exception traces following the redeploy.

Repeat the same confirmation for production, since research showed the Cosmos grant
exists there but did not include a functional write test — only role-assignment
presence.

Files:
* None — functional verification only.

Success criteria:
* At least one confirmed successful case write to Cosmos per environment, evidenced by
  either a queryable Cosmos document or a clean (non-403) Application Insights
  dependency trace to the Cosmos endpoint.

Context references:
* .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md - notes
  that role-assignment existence was the only evidence available this session; this
  step closes that gap.

Dependencies:
* Phase 3 completion (staging); no additional deployment needed for production, which
  is already provisioned with its grant.

### Step 4.2: Update tracking artifacts

* Add a dated entry to a new `.copilot-tracking/changes/2026-09-17/wi10-agent-cosmos-grant-changes.md`
  describing: the staging variable now configured, the redeploy run ID, the
  before/after Cosmos role assignment state, and the functional write confirmation for
  both environments.
* Update `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`'s WI-10 entry
  and `.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md`'s
  WI-10 mention with a "RESOLVED" note and date, consistent with how WI-01 was closed
  out earlier this session.

Files:
* .copilot-tracking/changes/2026-09-17/wi10-agent-cosmos-grant-changes.md - new
  changes log for this task.
* .copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md - mark WI-10 resolved.
* .copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md -
  update the existing WI-10 mention with a resolution note.

Success criteria:
* Both planning logs reflect WI-10 as resolved with a dated note and links to the
  evidence gathered in Phase 4.1.

Context references:
* .copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md (Line 100) - the
  original WI-10 entry being closed.
* .copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md
  (Line 135) - the carried-over WI-10 mention being updated.

Dependencies:
* Step 4.1 completion.

## Dependencies

* GitHub CLI (`gh`) with permission to read/write repository Environment variables.
* Azure CLI (`az`) authenticated against subscription
  `64c3d212-40ed-4c6d-a825-6adfbdf25dad`.
* Azure Developer CLI (`azd`) with `azure.ai.agents`/`azure.ai.connections` extensions,
  only if Step 3.1 uses a direct `azd provision` instead of the full workflow dispatch.

## Success Criteria

* Staging's `AGENT_PRINCIPAL_ID` environment variable is set and IaC-managed.
* Both environments' hosted agents are functionally confirmed able to write Cosmos
  cases.
* WI-10 is marked resolved across all planning logs that reference it.
