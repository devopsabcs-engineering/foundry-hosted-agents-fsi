---
permalink: /labs/lab-10-azure-foundation
title: "Lab 10 - Provision the Azure Foundation"
description: "Read the Bicep template that backs the pilot, compile it offline, and understand why the deployment itself stays gated."
---

> 🇫🇷 **[Version française](../fr/labs/lab-10-azure-foundation)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 35 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 09](lab-09-teardown.md), Azure CLI installed |

Labs 00 through 09 never left your laptop. That was deliberate: the calculator, the state machine, and the agent graph are all easier to reason about when nothing can fail for a network reason. This lab introduces the infrastructure that carries the same components into Azure for a pilot.

You will read and compile the template. You will not deploy it.

## Learning Objectives

By the end of this lab, you will be able to:

* Explain what `infra/main.bicep` provisions and how the staging and production names are derived
* Compile the template offline and regenerate the committed `infra/main.json` artifact
* Describe why two parameters, `reviewerClientId` and `agentPrincipalId`, default to empty strings
* Explain the gate that keeps the deployment workflow from running

## Exercises

### Exercise 10.1: Read the Deployment Gate

Open `infra/main.bicep` and read the banner comment at the top of the file before anything else.

```powershell
Get-Content infra/main.bicep -TotalCount 12
```

Expected result: a comment marking the template `AUTHOR-ONLY / NOT DEPLOYED`, gated behind G2 (platform and security), G3 (reproducible compatibility), and G6 (regulatory and privacy). The same gate applies to `.github/workflows/deploy-and-evaluate.yml`, which is why that workflow has no `push` trigger.

Treat this as the governing constraint for the rest of the lab. A template that compiles is not a template that has been approved to run.

### Exercise 10.2: Inventory What the Template Provisions

```powershell
Select-String -Path infra/main.bicep -Pattern "^module " | Select-Object -ExpandProperty Line
```

Expected result: a list of modules covering monitoring (Log Analytics and Application Insights), the Foundry account and project, the model deployment, the Cosmos DB case store, the MCP Container Apps, and the reviewer app.

Each module lives in `infra/modules/`. The workshop's local components map onto them directly: the approval repository you built in Lab 03 becomes the Cosmos case store, and the two MCP servers from Labs 04 and 05 become two Container Apps.

### Exercise 10.3 (Hands-on): Trace How Names Are Derived

This template has no `uniqueString()` calls and no azd tagging. Names come from a single `environmentName` parameter.

```powershell
Select-String -Path infra/main.bicep -Pattern "endsWith\(environmentName" | Select-Object -ExpandProperty Line
```

Expected result: several branches on the `-staging` suffix, including the MCP name prefix, the model capacity, the reviewer environment label, and the reviewer Container App name.

That last branch exists for a hard reason. Container App names are capped at 32 characters, and `reviewer-` prefixed to the staging environment name would be 45. The template therefore uses two literal names instead of interpolating:

| Environment | Reviewer Container App name |
| --- | --- |
| Production | `foundry-quote-reviewer` |
| Staging | `foundry-quote-reviewer-staging` |

Lab 12 depends on this determinism. Because the name is fixed rather than randomized, you can compute the sign-in redirect URI before the app is ever deployed.

### Exercise 10.4 (Hands-on): Compile the Template Offline

Compiling requires no Azure login and touches no subscription.

```powershell
az bicep install
az bicep build --file infra/main.bicep --outfile infra/main.json
```

Expected result: the command exits 0. `infra/main.json` is a committed artifact, so if the compile changes it, commit the regenerated file alongside your Bicep edit.

```powershell
git status --short infra/main.json
```

Expected result: no output when your working tree matches the committed artifact.

### Exercise 10.5: Understand the Two Empty Parameters

Two parameters default to an empty string, and in both cases the empty value skips work rather than deploying something broken.

```powershell
Select-String -Path infra/main.bicep -Pattern "param reviewerClientId|param agentPrincipalId|var deployReviewerApp" | Select-Object -ExpandProperty Line
```

Expected result: both parameters default to `''`, and `deployReviewerApp` is computed as `!empty(reviewerClientId)`.

The reviewer app parses its client ID with `uuid.UUID()` at startup. Passing an empty string would not produce a degraded mode, it would produce a crash loop, so the template skips the module entirely until Lab 12 supplies a real registration.

`agentPrincipalId` is subtler. A hosted agent receives its own dedicated per-agent Entra identity, and Foundry creates that identity at deploy time, after this template has already run. It is explicitly not the Foundry account or project system-assigned identity, so it cannot be resolved here. Until it is supplied, the agent cannot write cases to Cosmos.

## Validation Checklist

* [ ] You located the G2, G3, and G6 gate banner in `infra/main.bicep`
* [ ] You listed the modules the template provisions
* [ ] `az bicep build` exits 0 and leaves `infra/main.json` unchanged
* [ ] You can explain why `reviewerClientId` defaulting to empty skips the reviewer module
* [ ] You can explain why `agentPrincipalId` cannot be resolved at template authoring time

## Knowledge Check

* Why does the reviewer Container App use two literal names instead of interpolating `environmentName`?
* If `infra/main.json` is generated from `infra/main.bicep`, why is it committed rather than ignored?
* What breaks first if someone deploys the reviewer module with `reviewerClientId` set to an empty string?

## Next Steps

Continue to [Lab 11: The Applicant Web Chat UI](lab-11-web-chat.md).
