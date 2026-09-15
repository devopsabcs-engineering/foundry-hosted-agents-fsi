---
permalink: /labs/lab-10-azure-foundation
title: "Lab 10 - Provision the Azure Foundation"
description: "Read the Bicep templates that back the pilot, compile them offline, and understand why the network foundation is deployed separately from everything else."
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

You will read and compile the templates. Deployment runs from CI, not from this lab.

## Learning Objectives

By the end of this lab, you will be able to:

* Explain what `infra/main.bicep` provisions and how the staging and production names are derived
* Explain why the virtual network lives in `infra/network.bicep` rather than in `infra/main.bicep`
* Compile the templates offline and regenerate the committed JSON artifacts
* Describe why two parameters, `reviewerClientId` and `agentPrincipalId`, default to empty strings

## Exercises

### Exercise 10.1: Read the Network Foundation

Two templates deploy into one resource group. Open `infra/network.bicep` and read the banner before anything else.

```powershell
Get-Content infra/network.bicep -TotalCount 12
```

Expected result: a comment explaining that this template is deployed once for the whole resource group, separately from `infra/main.bicep`.

The reason is worth understanding, because it is a trap that is easy to walk into. `infra/main.bicep` is deployed twice into the same resource group, once for staging and once for production. A virtual network is a single resource with its subnets as properties, so an ARM write that omits `subnets` removes the ones it does not name. Had the network been declared inside `infra/main.bicep`, provisioning staging would delete production's subnets and provisioning production would delete staging's.

```powershell
Select-String -Path infra/network.bicep -Pattern "name: 'snet-" | Select-Object -ExpandProperty Line
```

Expected result: five subnets. Two carry the Container Apps environments, two carry the agent runtimes, and one carries private endpoints.

The agent subnets are separate from the Container Apps subnets because a Foundry account claims its injection subnet exclusively. Two accounts cannot share one, which is why staging and production each get their own.

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

### Exercise 10.4 (Hands-on): Compile the Templates Offline

Compiling requires no Azure login and touches no subscription.

```powershell
az bicep install
az bicep build --file infra/network.bicep --outfile infra/network.json
az bicep build --file infra/main.bicep --outfile infra/main.json
```

Expected result: both commands exit 0. The JSON files are committed artifacts, so if a compile changes one, commit the regenerated file alongside your Bicep edit.

```powershell
git status --short infra/main.json infra/network.json
```

Expected result: no output when your working tree matches the committed artifacts.

### Exercise 10.5: Understand the Two Empty Parameters

Two parameters default to an empty string, and in both cases the empty value skips work rather than deploying something broken.

```powershell
Select-String -Path infra/main.bicep -Pattern "param reviewerClientId|param agentPrincipalId|var deployReviewerApp" | Select-Object -ExpandProperty Line
```

Expected result: both parameters default to `''`, and `deployReviewerApp` is computed as `!empty(reviewerClientId)`.

The reviewer app parses its client ID with `uuid.UUID()` at startup. Passing an empty string would not produce a degraded mode, it would produce a crash loop, so the template skips the module entirely until Lab 12 supplies a real registration.

`agentPrincipalId` is subtler. A hosted agent receives its own dedicated per-agent Entra identity, and Foundry creates that identity at deploy time, after this template has already run. It is explicitly not the Foundry account or project system-assigned identity, so it cannot be resolved here. Until it is supplied, the agent cannot write cases to Cosmos.

### Exercise 10.6: Understand Why Cosmos Is Unreachable From the Internet

```powershell
Select-String -Path infra/modules/cosmos-db.bicep -Pattern "publicNetworkAccess|privateEndpoints|groupIds" | Select-Object -ExpandProperty Line
```

Expected result: `publicNetworkAccess: 'Disabled'`, a `Microsoft.Network/privateEndpoints` resource, and a `groupIds` array containing `Sql`.

The template declares `Disabled` because an Azure Policy assignment at the tenant root applies a `modify` effect that rewrites this property on every write. An earlier version of this template declared `Enabled`, which produced a specific and instructive failure. The deployment reported success, policy immediately set the account back to `Disabled`, and the reviewer app then returned HTTP 500 on every request with `Request originated from IP ... through public internet. This is blocked by your Cosmos DB account firewall settings.`

> [!IMPORTANT]
> A template that declares a value policy overrides is not merely cosmetic drift. It means the deployment is no longer a description of the running system, so nobody reading the template can predict the behaviour of what is deployed.

The private endpoint gives workloads inside the virtual network a path that the firewall accepts. The private DNS zone matters just as much: without it, callers inside the network resolve the account's public address, and the firewall rejects them exactly as before.

```powershell
Select-String -Path infra/modules/cosmos-db.bicep -Pattern "privateDnsZoneGroups" | Select-Object -ExpandProperty Line
```

Expected result: a `privateDnsZoneGroups` child resource, which is what writes the A records into the zone.

## Validation Checklist

* [ ] You can explain why the virtual network is not declared in `infra/main.bicep`
* [ ] You listed the modules the template provisions
* [ ] `az bicep build` exits 0 for both templates and leaves the JSON artifacts unchanged
* [ ] You can explain why `reviewerClientId` defaulting to empty skips the reviewer module
* [ ] You can explain why `agentPrincipalId` cannot be resolved at template authoring time
* [ ] You can explain what breaks when a template declares a value that policy overrides

## Knowledge Check

* Why does the reviewer Container App use two literal names instead of interpolating `environmentName`?
* If `infra/main.json` is generated from `infra/main.bicep`, why is it committed rather than ignored?
* What breaks first if someone deploys the reviewer module with `reviewerClientId` set to an empty string?
* A private endpoint exists but the private DNS zone group was never created. What does a caller inside the virtual network see?

## Next Steps

Continue to [Lab 11: The Applicant Web Chat UI](lab-11-web-chat.md).
