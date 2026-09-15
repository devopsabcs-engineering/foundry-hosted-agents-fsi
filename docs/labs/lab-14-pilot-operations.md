---
permalink: /labs/lab-14-pilot-operations
title: "Lab 14 - Pilot Operations"
description: "Run the validation pipeline locally, read the evaluation gate, and walk the teardown workflow that protects shared infrastructure."
---

> 🇫🇷 **[Version française](../fr/labs/lab-14-pilot-operations)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

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
* Identify which workflows are gated and why

## Exercises

### Exercise 14.1: Inventory the Pipeline

```powershell
Get-ChildItem .github/workflows -Filter *.yml | Select-Object -ExpandProperty Name
```

Expected result: seven workflows.

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `continuous-validation.yml` | push, pull request, dispatch | Offline regression tests and Bicep compile |
| `reviewer-app-build.yml` | path-filtered push and pull request | Reviewer backend and frontend tests, image build |
| `web-chat-build.yml` | path-filtered push and pull request | Chat backend and frontend tests, image build |
| `publish-test-trends.yml` | after validation completes | Publishes test evidence to the wiki |
| `deploy-and-evaluate.yml` | call and dispatch only | Provision and deploy, gated |
| `hosted-agent-cd.yml` | call and dispatch only | Hosted agent deployment, gated |
| `reviewer-app-teardown.yml` | dispatch only | Removes reviewer-scoped resources |

Only the first three run automatically. Nothing that touches Azure runs on a push.

### Exercise 14.2 (Hands-on): Run the Offline Suite Locally

These are the same commands `continuous-validation.yml` runs.

```powershell
pytest src/quote-preparation-agent/tests -v
pytest eval -v
pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests -v
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

Bilingual parity is the check worth pausing on. A change that improved the English message while leaving the French one stale would pass every unit test in this repository and still be a defect, because both locales are the product. The gate treats a parity break as a failure.

### Exercise 14.4: Understand the Credential Posture

```powershell
Select-String -Path .github/workflows/*.yml -Pattern "secrets\." | Select-Object -ExpandProperty Line
```

Expected result: the only secret referenced across the pipeline is the wiki push token. Everything else comes from repository variables.

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

Expected result: exit code 1 with exactly three findings, all reporting `unexpected key "queue"`:

| File | Line |
| --- | --- |
| `deploy-and-evaluate.yml` | 58 |
| `publish-test-trends.yml` | 48 |
| `reviewer-app-teardown.yml` | 80 |

These are expected. `concurrency.queue` is valid to this repository's deployment model and unrecognized by the linter's schema. Treat any fourth finding as a real one, and leave these three alone.

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

### Exercise 14.7: Locate the Remaining Gate

Lab 10 introduced the G2, G3, and G6 gate on the infrastructure template. The same gate covers deployment.

```powershell
Get-Content .github/workflows/deploy-and-evaluate.yml -TotalCount 20
```

Expected result: an author-only banner instructing that the workflow not be dispatched until the gates clear.

Two consequences follow, and both are correct rather than defects:

* The HTTPS redirect URIs you registered in Lab 12 do not resolve, because no reviewer Container App exists yet
* The hosted agent has no Entra agent identity, so `agentPrincipalId` from Lab 10 stays empty and the deployment link tables published to the wiki omit reviewer rows

The pilot is complete as a system and deliberately incomplete as a deployment. Recognizing that difference is the point of this lab.

## Validation Checklist

* [ ] You listed all seven workflows and identified which run automatically
* [ ] Every local test suite passes
* [ ] `python eval/evaluation_gate.py` reports `Gate: PASS`
* [ ] The only secret in the pipeline is the wiki push token
* [ ] `actionlint` reports exactly three known `queue` findings
* [ ] You can name the four safeguards in front of the teardown workflow
* [ ] You located the author-only banner on the deployment workflow

## Knowledge Check

* Why would a bilingual parity failure be invisible to the unit test suites?
* Why is a repository variable an acceptable home for `AZURE_CLIENT_ID` when a client secret would not be?
* The teardown workflow deletes an AcrPull role assignment but never the container registry. Why?
* If `execute` defaults to false, what does a first run of the teardown workflow actually produce?
* Why does the deterministic evaluation gate avoid calling a model?

## Next Steps

You have completed the bilingual quote-preparation workshop, from a synthetic fixture on your laptop to a reviewed decision with an audit trail.

Return to the [labs index](index.md) or the [workshop home page](../index.md).
