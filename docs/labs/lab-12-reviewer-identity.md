---
permalink: /labs/lab-12-reviewer-identity
title: "Lab 12 - Reviewer Identity and Access"
description: "Register the reviewer application, grant the Reviewer role through a security group, and compute redirect URIs before the app is deployed."
---

> 🇫🇷 **[Version française](../fr/labs/lab-12-reviewer-identity)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 45 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 11](lab-11-web-chat.md), an Entra tenant where you can consent to Microsoft Graph application permissions |

The reviewer app is the only surface in this system that displays a calculated premium. Everything about its identity configuration follows from that single fact.

> [!WARNING]
> This lab writes to your Entra tenant. Use a development or sandbox tenant. Every step is reversible, and Exercise 12.7 shows you how.

## Learning Objectives

By the end of this lab, you will be able to:

* Run `scripts/setup-reviewer-identity.ps1` in preview mode and then for real
* Explain why the reviewer app uses an app role while the chat app uses a group
* Compute a Container App redirect URI before the Container App exists
* Grant the Reviewer role to a security group rather than to individual people
* Publish the resulting client ID as a repository variable for CI

## Exercises

### Exercise 12.1: Read the Script Contract

```powershell
Get-Help ./scripts/setup-reviewer-identity.ps1 -Full
```

Expected result: a synopsis, three parameters (`RedirectUri`, `TenantId`, `ReviewerGroupId`), and a description noting that the script is safe to re-run because it resolves the application by exact display name and patches it when it already exists.

Read the permissions paragraph carefully. The script needs Microsoft Graph application permissions, and an Azure subscription role such as Owner or Contributor grants none of them:

| Operation | Graph permission |
| --- | --- |
| Create or patch the application | `Application.ReadWrite.All` |
| Grant the Reviewer role to a group | `AppRoleAssignment.ReadWrite.All` |
| Admin-consent the Review.Access scope | `DelegatedPermissionGrant.ReadWrite.All` |

This is why the repository's CI identity does not run this script. An administrator runs it from a workstation after `az login`.

### Exercise 12.2 (Hands-on): Preview the Changes

The script supports `ShouldProcess`, so you can see what it would do before it does anything.

```powershell
az login --tenant <your-tenant-id>
./scripts/setup-reviewer-identity.ps1 -TenantId <your-tenant-id> -WhatIf
```

Expected result: a description of the application that would be created, named `Foundry Quote Preparation Reviewer`, with no change written to the tenant.

### Exercise 12.3 (Hands-on): Create the Registration

```powershell
./scripts/setup-reviewer-identity.ps1 -TenantId <your-tenant-id>
```

Expected result: the script exits 0 and prints the reviewer client ID. Record it. Re-running the script returns the same ID, because the application is resolved by display name rather than created blindly.

Inspect what was created:

```powershell
az ad app show --id <reviewer-client-id> --query "{name:displayName, spa:spa.redirectUris, scopes:api.oauth2PermissionScopes[].value, roles:appRoles[].value}"
```

Expected result: one SPA redirect URI (`http://localhost:8100`), one delegated scope (`Review.Access`), and one app role (`Reviewer`).

### Exercise 12.4: Understand Why a Role and Not a Group

Lab 11 showed the chat app gating on `groups`. The reviewer app gates on an app role instead.

```powershell
az ad sp show --id <reviewer-client-id> --query "{assignmentRequired:appRoleAssignmentRequired}"
```

Expected result: `appRoleAssignmentRequired` is `true`.

That flag is the substantive difference. With assignment required, Entra refuses to issue a token for this application to anyone who has not been assigned the role, so an unauthorized person is stopped at the identity provider rather than at the application. A group membership claim, by contrast, is informational: the application must remember to check it.

For a surface that reveals a priced decision, failing closed at the identity provider is the stronger default.

### Exercise 12.5 (Hands-on): Compute the Deployed Redirect URIs

The reviewer frontend configures MSAL with `redirectUri: window.location.origin`.

```powershell
Select-String -Path apps/reviewer-app/frontend/src/main.jsx -Pattern "redirectUri" | Select-Object -ExpandProperty Line
```

Expected result: the redirect is the page origin, with no trailing slash and no path. A registered URI must therefore match the origin exactly.

A Container App origin is its name joined to its environment's default domain. Lab 10 showed that the reviewer app name is deterministic, and the environment domain is readable from Azure:

```powershell
az containerapp env list --query "[].{name:name, rg:resourceGroup, domain:properties.defaultDomain}" -o table
```

Expected result: one row per Container Apps environment. Build the origin as `https://<reviewer-app-name>.<defaultDomain>`.

Register it alongside the local URI. The script unions the new value with whatever is already registered, so running it once per environment accumulates rather than replaces:

```powershell
./scripts/setup-reviewer-identity.ps1 -TenantId <your-tenant-id> -RedirectUri 'https://foundry-quote-reviewer.<production-domain>'
./scripts/setup-reviewer-identity.ps1 -TenantId <your-tenant-id> -RedirectUri 'https://foundry-quote-reviewer-staging.<staging-domain>'
az ad app show --id <reviewer-client-id> --query "spa.redirectUris"
```

Expected result: three URIs, the two deployed origins and `http://localhost:8100`. Any value other than the localhost origin must be HTTPS, and the script rejects anything else.

Keeping the local URI registered is intentional. Lab 13 runs the reviewer app on your workstation against the real registration, which only works while `http://localhost:8100` remains valid.

### Exercise 12.6 (Hands-on): Grant the Role Through a Group

Assign the role to a group rather than to people. Membership then changes without touching the app registration.

```powershell
az ad group create --display-name 'Foundry Quote Preparation Reviewers' --mail-nickname 'foundry-quote-reviewers'
$groupId = az ad group show --group 'Foundry Quote Preparation Reviewers' --query id -o tsv
./scripts/setup-reviewer-identity.ps1 -TenantId <your-tenant-id> -ReviewerGroupId $groupId
```

Expected result: the Reviewer role is assigned with a `principalType` of `Group`.

Add yourself so Lab 13 can sign in:

```powershell
$me = az ad signed-in-user show --query id -o tsv
az ad group member add --group $groupId --member-id $me
az role assignment list --assignee $me --query "[].roleDefinitionName" -o tsv
```

Expected result: your account is a member. Note that the Reviewer role is an application role, not an Azure resource role, so it does not appear in `az role assignment list`. Confirm it on the service principal instead:

```powershell
az ad sp show --id <reviewer-client-id> --query "appRoles[?value=='Reviewer']"
```

### Exercise 12.7: Publish the Client ID and Clean Up

CI reads the client ID from a repository variable. The Bicep template in Lab 10 skips the reviewer module entirely when it is absent.

```powershell
gh variable set REVIEWER_CLIENT_ID --body '<reviewer-client-id>'
gh variable list
```

Expected result: `REVIEWER_CLIENT_ID` appears in the list. It is a variable rather than a secret because a public client ID is not a credential.

When you have finished Lab 13 and want to remove what this lab created:

```powershell
az ad app delete --id <reviewer-client-id>
az ad group delete --group 'Foundry Quote Preparation Reviewers'
gh variable delete REVIEWER_CLIENT_ID
```

## Validation Checklist

* [ ] `-WhatIf` previewed the registration without writing to the tenant
* [ ] The registration exposes the `Review.Access` scope and the `Reviewer` role
* [ ] `appRoleAssignmentRequired` is `true`
* [ ] `spa.redirectUris` contains both deployed origins and `http://localhost:8100`
* [ ] The Reviewer role is assigned to a group, and you are a member of that group
* [ ] `REVIEWER_CLIENT_ID` is published as a repository variable

## Knowledge Check

* Why can a GitHub Actions OIDC identity with Owner on the subscription still fail to run this script?
* What would break if a redirect URI were registered as `https://<host>/` with a trailing slash?
* Why does the script union redirect URIs instead of replacing them?
* Why is a client ID published as a repository variable rather than a secret?

## Next Steps

Continue to [Lab 13: The Reviewer UI](lab-13-reviewer-ui.md).
