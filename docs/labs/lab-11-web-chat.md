---
permalink: /labs/lab-11-web-chat
title: "Lab 11 - The Applicant Web Chat UI"
description: "Run the applicant-facing chat locally, read its access gate, and prove the surface can never show a premium."
---

> 🇫🇷 **[Version française](../fr/labs/lab-11-web-chat)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 40 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 10](lab-10-azure-foundation.md), Node.js 20 or later |

In Lab 07 you read the agent's applicant message as raw JSON on a terminal. `apps/web-chat` is the surface that message is written for. It is a FastAPI backend serving a compiled React single-page application, and it is the only place an applicant interacts with the system.

The constraint you proved in Lab 02 and Lab 07 now has a user interface to defend: the applicant never sees a premium.

## Learning Objectives

By the end of this lab, you will be able to:

* Run the web chat backend and frontend locally
* Describe the four environment variables the app refuses to start without
* Explain how group membership, not an app role, gates access to the chat
* Trace how a bilingual agent payload is narrowed to a single locale for display
* Explain why a local run stops at the access gate while the deployed origin does not

## Exercises

### Exercise 11.1: Read the Startup Contract

```powershell
Select-String -Path apps/web-chat/app.py -Pattern "os.environ\[" | Select-Object -ExpandProperty Line
```

Expected result: four required variables, `AGENT_ENDPOINT`, `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, and `PILOT_GROUP_ID`. The three identity values are parsed with `uuid.UUID()`, so a malformed value fails at startup rather than at first request.

`AGENT_ENDPOINT` is validated harder than the rest:

```powershell
Select-String -Path apps/web-chat/app.py -Pattern "must be a Foundry HTTPS endpoint" -Context 3,0
```

Expected result: the scheme must be `https` and the host must end in `.services.ai.azure.com`. The app will not be pointed at an arbitrary URL.

### Exercise 11.2 (Hands-on): Build the Frontend

```powershell
cd apps/web-chat/frontend
npm ci
npm test
npm run build
cd ../../..
```

Expected result: `npm test` runs the `node --test` suites in `apps/web-chat/frontend/tests` and passes. `npm run build` writes a compiled bundle to `apps/web-chat/frontend/dist`, which the backend mounts at `/` when it is present.

### Exercise 11.3 (Hands-on): Run the App Locally

The identity values below are placeholders. They are enough to start the process and render the access gate, which is all this exercise needs.

```powershell
cd apps/web-chat
$env:ENTRA_TENANT_ID = '00000000-0000-0000-0000-000000000000'
$env:ENTRA_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
$env:PILOT_GROUP_ID = '00000000-0000-0000-0000-000000000002'
$env:AGENT_ENDPOINT = 'https://example-project.services.ai.azure.com/api/projects/demo/agents/quote-preparation/stream'
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8200
```

Expected result: uvicorn reports `Application startup complete`. There is no module-level `app` object in `apps/web-chat/app.py`, so the `--factory` flag is required.

In a second terminal:

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8200/api/config' -UseBasicParsing | Select-Object -ExpandProperty Content
```

Expected result: a JSON document with `tenantId`, `clientId`, `scope`, and `environment`. The scope is derived as `api://<clientId>/Chat.Access`. Notice what is absent: the pilot group ID never reaches the browser, because the browser is not the thing that enforces it.

### Exercise 11.4: Read the Access Gate

Open `http://localhost:8200` in a browser.

![The applicant chat before sign-in, showing the heading "Quotes start with access.", a Sign in with Microsoft button, a disabled message box, and a synthetic-data disclaimer](/assets/images/web-chat-sign-in.png)

Expected result: the composer is disabled, the sidebar reads `Not signed in`, and the footer carries the synthetic training data disclaimer. The disclaimer is part of the layout rather than part of a message, so it cannot be scrolled away or displaced by agent output.

### Exercise 11.5 (Hands-on): Trace the Authorization Checks

Open `apps/web-chat/auth.py` and read `PilotAuth.verify`.

```powershell
Select-String -Path apps/web-chat/auth.py -Pattern "raise HTTPException" | Select-Object -ExpandProperty Line
```

Expected result: seven rejection paths, covering a missing header, an unreachable key endpoint, an invalid signature, and four claim checks. The token signature is validated against the tenant's published keys, then the claims are checked in sequence:

| Claim | Requirement |
| --- | --- |
| `tid` | Matches the configured tenant |
| `azp` | Matches the configured client ID |
| `scp` | Contains `Chat.Access` |
| `groups` | Contains the configured pilot group ID |

The last check is what distinguishes this app from the reviewer app in Lab 12. Chat access is granted by security group membership. Reviewer access is granted by an app role assignment. Both are enforced server side on every request.

Run the backend tests to see those paths exercised:

```powershell
$env:PYTHONPATH = 'apps/web-chat'
python -m pytest apps/web-chat/tests -v
```

Expected result: the authorization and application suites pass. The `PYTHONPATH` assignment is required because these tests import `app` and `auth` as top-level modules, and the pipeline sets the same variable for the same reason.

### Exercise 11.6 (Hands-on): Prove the Surface Cannot Show a Premium

The agent emits bilingual content, and the backend narrows it to one locale before it reaches the browser.

```powershell
python -c "
import sys
sys.path.insert(0, 'apps/web-chat')
from app import content_text

payload = {'text': {'en-CA': 'Your request was submitted for employee review.', 'fr-CA': 'Votre demande a ete soumise pour revision.'}}
print(repr(content_text(payload, 'en-CA')))
print(repr(content_text(payload, 'fr-CA')))
"
```

Expected result: each call returns the sentence for the requested locale. `content_text` reads only the `text` field of a content block, so no other field of an agent payload can reach the transcript.

Now confirm where the amount actually lives. In Lab 07 the agent stopped at `PENDING_REVIEW` without ever placing a figure into `applicant_message`, and in Lab 13 you will watch that same figure appear in the reviewer UI. The premium is not hidden from the applicant by a filter that could be misconfigured. It is never written into the applicant channel in the first place.

### Exercise 11.7: Understand What a Local Run Cannot Do

Sending a message requires two things your local run does not have: a live `AGENT_ENDPOINT` backed by a deployed hosted agent, and an app registration whose redirect URI points at your local origin.

The deployed chat has both. `scripts/setup-web-chat-identity.ps1` registers the deployed origins alongside `http://localhost:8000`, so signing in against the deployed URL works while the placeholder identity values from Exercise 11.2 cannot.

```powershell
az containerapp show --name foundry-quote-chat-staging --resource-group $env:AZURE_RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv
```

Expected result: a hostname ending in `azurecontainerapps.io`. Open it in a browser and sign in with an account in the pilot group.

> [!NOTE]
> The hostname changes whenever the Container Apps environment is recreated, which Lab 14 covers. If sign-in fails with a redirect URI mismatch, the registration is stale rather than misconfigured; rerun `scripts/setup-web-chat-identity.ps1` with the current FQDN.

A local run still teaches the part that matters most here. The access gate, the config endpoint, and the locale reduction are all exercised without any deployment at all, and those are the boundaries a reviewer would ask about.

Stop the server when you are finished.

```powershell
# In the terminal running uvicorn
Ctrl+C
```

## Validation Checklist

* [ ] `npm test` and `npm run build` succeed in `apps/web-chat/frontend`
* [ ] The backend starts with `--factory` and reports `Application startup complete`
* [ ] `/api/config` returns a scope of `api://<clientId>/Chat.Access` and omits the pilot group ID
* [ ] The browser shows a disabled composer and a `Not signed in` sidebar before authentication
* [ ] You located all four claim checks in `PilotAuth.verify`
* [ ] `python -m pytest apps/web-chat/tests` passes with `PYTHONPATH` set to `apps/web-chat`

## Knowledge Check

* Why does `/api/config` expose the client ID but not the pilot group ID?
* Why is `AGENT_ENDPOINT` restricted to hosts ending in `.services.ai.azure.com`?
* The chat uses group membership and the reviewer app uses an app role. What does an app role give you that a group does not?
* If `content_text` receives a payload whose `text` is a plain string rather than a locale map, what does it return?

## Next Steps

Continue to [Lab 12: Reviewer Identity and Access](lab-12-reviewer-identity.md).
