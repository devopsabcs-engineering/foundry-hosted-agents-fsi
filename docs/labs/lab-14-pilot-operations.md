---
permalink: /labs/lab-14-pilot-operations
title: "Lab 14 - Pilot Operations"
description: "Run the validation pipeline locally, read the evaluation gate, and walk the teardown workflow that protects shared infrastructure."
---

> 🇫🇷 **[Version française](../fr/labs/lab-14-pilot-operations.md)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

> [!WARNING]
> If you are continuing to Labs 15 through 18, do not execute teardown against
> the shared restored demo. Keep approved staging v5 and production v6 deployed; study
> teardown safeguards here without deleting those environments.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 40 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 13](lab-13-reviewer-ui.md) |

You have now seen every component: the calculator, the state machine, the MCP servers, the agent, the applicant chat, and the reviewer interface. This lab covers what keeps them honest between changes.

## Learning Objectives

By the end of this lab, you will be able to:

* Run the same checks CI runs, locally and offline
* Read the deterministic evaluation gate and explain what it refuses to let through
* Explain why the pipeline authenticates with OIDC and carries almost no secrets
* Describe the safety design of the teardown workflow
* Explain why some resources have to be deleted rather than reconfigured
* Identify teardown commands for an explicitly approved disposable sandbox only

## Exercises

### Exercise 14.1: Inventory the Pipeline

```powershell
Get-ChildItem .github/workflows -Filter *.yml | Select-Object -ExpandProperty Name
```

Expected result: ten workflows.

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `continuous-validation.yml` | push, pull request, dispatch | Offline regression tests and Bicep compile |
| `reviewer-app-build.yml` | path-filtered push/PR, dispatch | Tests; ACR image publication on `main` push |
| `web-chat-build.yml` | path-filtered push/PR, dispatch | Tests; ACR image publication on `main` push |
| `publish-test-trends.yml` | after validation, dispatch | Publishes retained test evidence to the wiki |
| `require-linked-issue.yml` | pull request lifecycle | Requires a closing issue reference in the PR |
| `deploy-and-evaluate.yml` | call and dispatch only | Provision and deploy, staging then production |
| `hosted-agent-cd.yml` | call and dispatch only | Hosted agent deployment |
| `reviewer-app-teardown.yml` | dispatch only | Removes reviewer-scoped resources |
| `network-rebuild-teardown.yml` | dispatch only | Removes resources whose network configuration is immutable |
| `full-teardown.yml` | dispatch only | Deletes whole resource groups at the end of the workshop |

Validation, linked-issue checks and wiki publication run automatically on their
configured events. Both app build workflows authenticate to Azure with OIDC and
publish ACR images on eligible `main` pushes. Image publication is not deployment:
agent rollout and destructive teardown remain explicit call/dispatch operations,
with production protected by environment approval.

### Exercise 14.2 (Hands-on): Run the Offline Suite Locally

From the repository root, reactivate the Lab 00 environment and install the
agent/backend requirements from their earlier labs. These run the same Python
suites as `continuous-validation.yml`; optional SDK checks may be skipped when
their dependencies are absent, so inspect the reasons.

```powershell
python -m pytest src/quote-preparation-agent/tests -v
python -m pytest eval -v
python -m pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests -v
```

Expected result: all three suites pass. The application and reviewer surfaces are tested by their own workflows:

```powershell
python -m pytest apps/reviewer-app/tests -v
$env:PYTHONPATH = 'apps/web-chat'
python -m pytest apps/web-chat/tests -v
```

The reviewer tests insert their own import path, while the chat tests rely on `PYTHONPATH`. The workflows differ in exactly the same way, which is worth noticing before you copy a command between them.

### Exercise 14.3 (Hands-on): Read the Evaluation Gate

```powershell
python eval/evaluation_gate.py
```

Expected result: a line reporting how many golden records passed, a bilingual parity result, and a final verdict.

```text
13/13 records passed; bilingual_parity=PASS
Gate: PASS
```

The gate is deterministic. It calls no model and makes no network request, so a failure always means a behaviour change rather than a flaky provider.

Bilingual parity is covered by unit tests as well as the golden-record gate.
An English-only improvement can still violate the bilingual contract. The gate
checks both locales across the dataset. Native judges are separate: scores
remain advisory, but complete, error-free EN/FR judge evidence is required for
promotion. Preserve historical 0/10 results under their original contract.

### Exercise 14.4: Understand the Credential Posture

```powershell
Select-String -Path .github/workflows/*.yml -Pattern "secrets\." | Select-Object -ExpandProperty Line
```

Expected result: `WIKI_PUSH_TOKEN` is the only custom `secrets.*` reference.
Workflows also use the built-in `github.token` for GitHub operations and OIDC
for Azure; repository variables provide deployment identifiers, not credentials.

Azure access uses workload identity federation:

```powershell
Select-String -Path .github/workflows/deploy-and-evaluate.yml -Pattern "azure/login|client-id|tenant-id|subscription-id" | Select-Object -ExpandProperty Line
```

Expected result: `azure/login` configured from `vars.AZURE_CLIENT_ID`, `vars.AZURE_TENANT_ID`, and `vars.AZURE_SUBSCRIPTION_ID`. There is no client secret anywhere, because OIDC exchanges a short-lived GitHub token for an Azure token at run time. A leaked repository variable is a set of identifiers, not a credential.

This is also why Lab 12 had to be run by an administrator. The federated identity holds Azure resource permissions and no Microsoft Graph permissions at all.

### Exercise 14.5 (Hands-on): Lint the Workflows

```powershell
actionlint
```

Results depend on the installed actionlint/schema version. Older versions
report `unexpected key "queue"` at the five `concurrency.queue` declarations
in deployment, wiki and teardown workflows. Compare each diagnostic with the
actual declaration and supported Actions syntax; line numbers are not an
allowlist. Investigate all other findings. Never ignore arbitrary errors merely
because a run reports five findings.

### Exercise 14.6: Read the Teardown Safety Design

Teardown is the most dangerous workflow in any pilot, so read its header before reading its steps.

```powershell
Get-Content .github/workflows/reviewer-app-teardown.yml -TotalCount 44
```

Expected result: a banner explaining that the workflow never deletes the resource group.

The reason is specific. `vars.AZURE_RESOURCE_GROUP` names a single resource group shared by both the staging and production environments, so `az group delete` issued while tearing down staging would take production with it. The workflow therefore deletes individually named reviewer-scoped resources only, and a protected-name guard fails the run if a computed deletion target ever collides with shared infrastructure.

Four independent safeguards sit in front of the first Azure call:

* The workflow is dispatch only, never push, schedule, or pull request
* The operator must type the target environment name into a `confirm` input, and a mismatch fails before any Azure call
* `execute` defaults to false, so a run with no inputs changed is a dry run that reports without deleting
* The job binds to the matching GitHub Environment, so required-reviewer protection applies

Every delete is existence-checked, so a rerun after a partial failure succeeds and a run against already-absent resources exits 0.

### Exercise 14.7: Read the Network Rebuild Teardown

Some configuration cannot be changed in place. `vnetConfiguration` on a Container Apps managed environment and `networkInjections` on a Foundry account are both set only at creation, so moving an already-deployed environment onto a virtual network means deleting it first.

```powershell
Get-Content .github/workflows/network-rebuild-teardown.yml -TotalCount 46
```

Expected result: a banner naming the three resource kinds it deletes and, at greater length, what it preserves.

The preserved list is the more interesting half. The Cosmos accounts stay, because a private endpoint attaches to an existing account and deleting them would discard every case in the store. The virtual network stays, because both environments share it. The Entra registrations stay, because one reviewer registration serves staging and production together.

```powershell
Select-String -Path .github/workflows/network-rebuild-teardown.yml -Pattern "seq 1 30|purgeable" | Select-Object -ExpandProperty Line
```

Expected result: a polling loop around the Foundry account purge.

That loop exists because of a timing detail that is easy to get wrong. `az cognitiveservices account delete` returns success while the account is still in a `Deleting` state, and a purge issued during that window is rejected. An injected account also holds a service association link on its subnet until the purge completes, so a single purge attempt leaves the subnet pinned and the rebuild blocked.

> [!WARNING]
> Deleting a managed environment changes the FQDN of every app inside it. The redirect URIs you registered in Lab 12 and the chat registration from Lab 11 both need refreshing afterwards, using the same scripts. Both scripts merge redirect URIs rather than replacing them, so rerunning them is safe.

### Exercise 14.8 (Hands-on): Tear Everything Down

This is a read-only study for the retained demo. Execute deletion only in your
own disposable sandbox after explicit owner approval and target inventory.
Do not run either option against the shared staging/production group. First
list environments and the resource group each points at:

```powershell
azd env list
azd env get-value AZURE_RESOURCE_GROUP -e <environment>
```

The historical reference inventory contained these two groups; it is not a
current existence check or a deletion authorization:

| Resource group | Contents |
| --- | --- |
| `rg-desjardins-quote-preparation` | Staging and production: Foundry, Container Apps, Cosmos DB, the container registry, and the virtual network |
| `rg-desjardins-quote-preparation-poc` | An earlier proof-of-concept deployment |

> [!CAUTION]
> `rg-desjardins-quote-preparation` holds staging and production together, which is exactly why Exercise 14.6's workflow refuses to delete it. Deleting it ends the pilot for everyone. The GitHub OIDC identity's role assignments are scoped to that group and disappear with it, so a later rebuild needs a subscription administrator to recreate the group and re-grant those roles.

**Option A: locally with azd.** This uses your own Azure sign-in, so you need Contributor on the group.

```powershell
azd down --force --purge -e <environment>
```

`--force` skips the confirmation prompt and `--purge` permanently removes the soft-deleted Foundry account and Log Analytics workspaces, so their names are free for a future deployment. If `azd down` reports nothing to delete (for example, because the environment was provisioned by the pipeline rather than from your machine), delete the group directly and purge the Foundry account yourself:

```powershell
az group delete --name <resource-group> --yes
az cognitiveservices account list-deleted --output table
az cognitiveservices account purge --name <account> --resource-group <resource-group> --location <location>
```

**Option B: through the pipeline.** `full-teardown.yml` is the third teardown workflow. Start with a dry run, which only inventories each group in the run summary:

```powershell
gh workflow run full-teardown.yml -f target=poc -f confirm=poc
gh workflow run full-teardown.yml -f target=poc -f confirm=poc -f execute=true
```

Expected result: protected `production` approval before execution. The first
command inventories; the second deletes the approved `poc` target. The workflow
also supports `shared`/`both`, but those targets must not be used on this retained
demo. Approval of a dry run does not authorize a later destructive run.

The workflow keeps the same four safeguards as the other teardown workflows and adds a fifth: resource group names must match an allowlist pattern, so a mistyped repository variable cannot point it at an unrelated group. It also purges each Foundry account before deleting the group, because the identity's roles are scoped to the group and would be gone by the time a purge ran afterwards.

> [!NOTE]
> By default the workflow identity has access to `vars.AZURE_RESOURCE_GROUP` only. A `poc` run reports the proof-of-concept group as not accessible and skips it with a warning; either grant the identity Contributor on that group first or use Option A for it. The workflow is safe to rerun: when the groups are already gone, it succeeds with a warning and deletes nothing. The Entra app registrations are not deleted by either option; remove the reviewer registration with `scripts/remove-reviewer-identity.ps1`.

## Validation Checklist

* [ ] You listed all ten workflows, including automatic ACR publication and issue linkage
* [ ] Every local test suite passes
* [ ] `python eval/evaluation_gate.py` reports `Gate: PASS`
* [ ] You distinguished the custom wiki secret, built-in GitHub token and Azure OIDC
* [ ] You reviewed actionlint diagnostics against the installed schema and actual declarations
* [ ] You can name the four safeguards in front of the teardown workflows
* [ ] You can explain why the network rebuild teardown preserves the Cosmos accounts
* [ ] You retained the shared environments and identified the approval required for sandbox deletion

## Knowledge Check

* How do parity unit tests and the dataset-wide gate complement each other?
* Why is a repository variable an acceptable home for `AZURE_CLIENT_ID` when a client secret would not be?
* The teardown workflow deletes an AcrPull role assignment but never the container registry. Why?
* If `execute` defaults to false, what does a first run of the teardown workflow actually produce?
* Why does the deterministic evaluation gate avoid calling a model?
* Why does the Foundry account have to be purged rather than merely deleted before the rebuild can proceed?
* Why does `full-teardown.yml` purge the Foundry account before deleting the resource group rather than after?

## Next Steps

You have completed the pilot operations sequence. Continue to
[Lab 15: Native Files and Generation](lab-15-native-files-generation.md) for the
isolated native showcase, keeping the shared environments deployed.

Return to the [labs index](index.md) or the [workshop home page](../index.md).
