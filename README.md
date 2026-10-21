---
title: Foundry Hosted Agents Workshop - Financial Services (FSI)
description: Bilingual hands-on workshop adapting Microsoft Foundry hosted agents to a synthetic Ontario auto-insurance quote-preparation scenario with a deterministic calculator and a mandatory employee-approval gate.
---

[English](README.md) | [Français](README.fr.md)

## Overview

This repository is a bilingual (English/French) hands-on workshop adapted
from the sibling
[`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents)
repository. It replaces that repository's airline threat-assessment
scenario with a financial-services scenario: a synthetic Ontario
auto-insurance quote-preparation agent, backed by a deterministic
calculator and a mandatory, separately persisted employee-approval gate
before any applicant-facing preview.

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this repository is
> synthetic and non-binding. Nothing here represents an actual Desjardins
> product, rate, or policy, and no regulator or insurer has reviewed or
> endorsed this workshop.

## Learner path

The default path through these labs does not require GitHub Copilot or any
other AI coding assistant. Where workshop authors used AI-assisted tooling
to help draft or review content, that assistance is disclosed in the
affected lab or file rather than implied as part of the learner
experience.

## Repository layout

* `docs/` holds the English workshop site (Jekyll, Just the Docs theme);
  start at [docs/index.md](docs/index.md).
* `docs/fr/` holds the French workshop site, structurally paired with
  `docs/`; start at [docs/fr/index.md](docs/fr/index.md).
* `src/quote-preparation-agent/` holds the hosted LangGraph
  quote-preparation agent.
* `mcp/application-server/` holds a read-only MCP service exposing
  synthetic application data.
* `mcp/rulebook-server/` holds a read-only MCP service exposing
  synthetic rulebook data.
* `apps/workshop/` holds the deterministic calculator and SQLite approval
  repository used by the local exercises.
* `apps/reviewer-app/` holds the bilingual employee review queue. Its
  backend and the agent share the `CaseStore` contract in
  `src/quote-preparation-agent/case_store.py`, with SQLite locally and
  private Cosmos DB in the retained environments.
* `apps/web-chat/` holds an internal-pilot web chatbot for the hosted
  agent, ported from the sibling repository. It is deployed out of band
  ([infra/web-chat.bicep](infra/web-chat.bicep)) alongside
  `apps/reviewer-app/` -- see [Deployment links](#deployment-links) below
  for both UIs' current URLs.
* `data/synthetic/` holds the synthetic fixtures and JSON Schema for
  the quote-preparation contract.
* `eval/` holds the evaluation harness for arithmetic, approval,
  injection, and bilingual-parity checks.
* `infra/` holds Bicep infrastructure modules for the controlled synthetic
  pilot. An approved pilot release is not regulatory or insurer approval.
* `scripts/` holds shared helpers, including the bilingual
  workshop-deck generator.

## Getting started

Start at the workshop landing page: [docs/index.md](docs/index.md) in
English, or [docs/fr/index.md](docs/fr/index.md) in French. The same
content is published as a browsable site at
<https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/>
(GitHub sign-in is required while this repository is private).

Read the [architecture and trust boundaries](docs/architecture.md)
([French](docs/fr/architecture.md)) before the Azure exercises. The graph
routes a validated synthetic case ID through `INTAKE`, `REFERENCE_LOOKUP`
and `COMPOSITION`; calculation and draft persistence happen inside
`COMPOSITION`, not in additional agent stages. Applicant chat receives only
bounded bilingual messages, while the reviewer API exposes the calculation
and records employee decisions.

## Evaluation engineering workshop

Use the [step-by-step Foundry evaluation guide](docs/evaluation-guide.md)
and [Lab 19: Evaluation Engineering](docs/labs/lab-19-evaluation-engineering.md)
for a 3–4 hour progression from deterministic contracts to native model judges,
calibration, repeated trials and stateful regression checks.
The [English PowerPoint](docs/assets/decks/foundry-evaluation-engineering-en.pptx)
and [French PowerPoint](docs/assets/decks/foundry-evaluation-engineering-fr.pptx)
contain 34 editable slides each with instructor notes. Rebuild both with
`npm run build-evaluation-deck`. The [French guide](docs/fr/evaluation-guide.md)
and [French lab](docs/fr/labs/lab-19-evaluation-engineering.md) cover the same exercises.

## Try the web chatbot

For the session-2 customer demonstration, use the
[native Foundry showcase runbook](docs/native-showcase.md)
([French](docs/fr/native-showcase.md)). It separates restored deployment
evidence from verified native File Search RAG, operator skill consumption,
isolated memory checks, and custom trace replay. Content Understanding invoice
extraction passed in staging and production. Foundry IQ performs real MCP
retrieval but has strict acceptance failures; the approved isolated red-team
scan failed before producing scored results. Neither is presented as a pass,
and production IQ remains unpromoted.
Native grounding judges missed a known negative control; the runbook records
that limitation rather than claiming a quality pass. Keep both environments deployed.

See [current release evidence and screenshots](docs/showcase-evidence.md) for
the successful replacements of both failed generation jobs and the distinction
between published images and deployed runtime versions. Approved release
[`39527950931`, attempt 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931)
deployed runtime revision `2c3f13b` as staging v6 and production v7, with
both chat/reviewer UIs and both MCP services ready. Production revision-2
correction, current audit and self-approval denial passed; both actual reviewer
identities passed invocation200/memory403. Chat retains its verified image.
Native applicant-message judging passed 5/5 in each language on all
three criteria without errors; the historical 0/10 result belongs to a
different contract and remains preserved. These retained results are not
continuous availability guarantees.

The chat UI in `apps/web-chat/` is deployed out of band to staging and production (see
[Deployment links](#deployment-links) for the current URL). To run it
locally instead, against the real deployed agent, activate the Lab 00 virtual
environment and run from the repository root. Supply that environment's real
Foundry project endpoint, Entra registration and pilot group, and authenticate
your local Azure identity with the required Foundry access:

```powershell
python -m pip install -r apps/web-chat/requirements.txt
cd apps/web-chat/frontend
npm ci
npm run build
cd ..
$env:AGENT_ENDPOINT = "$env:FOUNDRY_PROJECT_ENDPOINT/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1"
$env:ENTRA_TENANT_ID = (az account show --query tenantId -o tsv)
$env:ENTRA_CLIENT_ID = "<app registration id from scripts/setup-web-chat-identity.ps1>"
$env:PILOT_GROUP_ID = "<pilot security group object id>"
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8000
```

Then open <http://localhost:8000/> to match the registered redirect origin.
All four settings above are required at startup; the three identity values
must be valid UUIDs. Lab 11 uses UUID-shaped placeholders only to render the
access gate. Real sign-in and message submission require the actual identity
configuration, group membership, deployed Responses endpoint and authorized
backend caller.

![Quote preparation chat UI](assets/web-chat-ui.png)

If npm is blocked by your network, use your approved registry proxy. Both
frontends were clean-installed and built through the Microsoft proxy with:

```powershell
npm ci --ignore-scripts --registry=https://packagefeedproxy.microsoft.io/npm/
```

Keep npm's remote-fetch restrictions enabled. `EALLOWREMOTE` can indicate that
registry metadata introduced an absolute Azure DevOps tarball URL. The
committed lockfiles use canonical npm registry URLs, which npm remaps through
the selected proxy. Do not switch to `--allow-remote=all` or disable integrity
checks. If the approved proxy still refuses a package, retain the error and
contact the feed administrator.

## Try the reviewer app

`apps/reviewer-app/` is the reviewer-facing case queue: every case the
agent submits for review lands here, gated by an Entra app role rather
than the chatbot's security-group membership. See
[Deployment links](#deployment-links) for the current deployed URL, or
[docs/labs/lab-13-reviewer-ui.md](docs/labs/lab-13-reviewer-ui.md) for
running it locally against a real Entra registration.

![Quote reviewer UI](assets/reviewer-app-ui.png)

## Deployment links

> [!NOTE]
> The production environment's underlying Azure resource and `azd`
> environment names carry a historical `-poc` suffix (for example
> `cosmos-desjardins-quote-preparation-poc`,
> `aif-desjardins-quote-preparation-poc`). Despite that suffix, **these are
> the production resources**, not a separate proof-of-concept deployment --
> the wiki's Deployment Links table labels each row `(production)` or
> `(staging)` explicitly, so trust that label over any `-poc` text you spot
> in a resource name or URL.

This repository does not hardcode a "live demo" URL here, because the
underlying Container Apps hostnames and Foundry project name are
environment-specific and can be re-provisioned. Instead, the
[wiki Home page](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home)
carries the **Deployment Links** table, published from retained deployment
artifacts after
[`Deploy and Evaluate (Staging -> Production)`](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/workflows/deploy-and-evaluate.yml)
when wiki publication succeeds. Check its source run and the current release
evidence before treating links as live. It includes both pilot UIs:

* **the reviewer app** (case approval queue) and **the web chatbot** (applicant-facing chat UI)
* the hosted agent's Foundry project (Azure Portal, sign-in required)
* the agent's Responses API endpoint
* the `application-server` and `rulebook-server` MCP endpoints
* the resource group and container registry
* the published workshop site on GitHub Pages

Always follow the [wiki Home page](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home)
for published UI URLs rather than copying old hostnames. Both container apps
can be re-provisioned with a new hostname; a failed or delayed wiki publication
does not update an older table.

See also the
[Continuous Test Trends](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Continuous-Test-Trends)
wiki page for the latest offline-test, deterministic-gate, and LLM-judge
evaluation results.

Judge scores are advisory, but a failed live invocation or a missing answer
blocks production promotion. HTTP 200 error bodies do not count as successful
agent responses. Confirm a valid synthetic case reaches employee review before
declaring the rebuilt environment ready for a demo.

**Web chatbot pilot**: `apps/web-chat/` (a browser-based chat UI in front
of the hosted agent) is deployed out of band rather than by
`deploy-and-evaluate.yml`. Its template is
[infra/web-chat.bicep](infra/web-chat.bicep), applied with a direct
`az deployment group create` into the Container Apps environment that
`infra/main.bicep` already provisioned, and its Entra app registration comes
from [scripts/setup-web-chat-identity.ps1](scripts/setup-web-chat-identity.ps1).
Because the managed environment is recreated whenever its network
configuration changes, redeploy the chat and rerun the identity script after
any network rebuild. Its URL is not an `azd` output, so
`deploy-and-evaluate.yml`'s `promote-production` job reads it from the
`WEB_CHAT_APP_NAME`/`WEB_CHAT_URL` repository variables (production
environment) to include it in the wiki's Deployment Links table -- update
those variables after redeploying the chat to a new hostname.

## Restore the demo after a full teardown

The [current release evidence](docs/showcase-evidence.md#current-approved-release)
records the successful retained release. [Issue #7](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/7)
preserves the earlier teardown/rebuild incident, not the current readiness
verdict. The recovery procedure below applies only after a separately
approved future teardown; do not run it against the retained demo.

> [!IMPORTANT]
> A successful past deployment does not mean the demo is currently live.
> A full teardown deletes the shared resource group, registry, Foundry
> projects, case stores, and pilot UIs. Wiki links from before the teardown
> remain historical until the corresponding resources are restored.
> Use synthetic data only; deleted case data is not recreated by deployment.

1. Confirm the release approvals and the target subscription and region.
   Read the configuration in the repository and its `staging` and
   `production` GitHub environments.
2. Recreate the resource group named by `AZURE_RESOURCE_GROUP` and the
   registry named by `MCP_ACR_NAME`. The
   [deployment workflow](.github/workflows/deploy-and-evaluate.yml)
   requires both to exist before it can deploy the network and build
   images. Restore the deployment identity's required permissions at
   resource-group scope, including role-assignment and Foundry access.
   Do not enable registry admin credentials.
3. Remove stale `AGENT_PRINCIPAL_ID` and `WEB_CHAT_URL` values for deleted
   resources, checking repository variables and environment overrides.
   Keep the existing Entra app registrations and pilot/reviewer groups.
4. Run [Continuous Validation](.github/workflows/continuous-validation.yml),
   [Web Chat Build](.github/workflows/web-chat-build.yml), and
   [Reviewer App Build](.github/workflows/reviewer-app-build.yml) against
   the release revision. Manual UI build runs test and compile the apps;
   they do not deploy them.
   After a merge to `main`, app build workflows publish images tagged
   `v<VERSION>-<full-source-SHA>` and `latest`, without committing version
   bumps or pushing to protected `main`. Change `VERSION` through a linked
   feature PR when a semantic release increment is needed. Image publication
   is not application deployment; use a digest-pinned image for deployment.
5. Dispatch [Deploy and Evaluate](.github/workflows/deploy-and-evaluate.yml)
   for that revision. It restores staging, evaluates the deployed agent,
   and waits for the required human approval before production promotion.
   The reviewer app is included when `REVIEWER_CLIENT_ID` is configured.
   CI must authenticate both Azure CLI and `azd` with GitHub OIDC:
   Foundry extensions require the native `azd` login even when
   `auth.useAzCliAuth` is enabled.
   The workflow refreshes native `azd` OIDC authentication immediately before
   each agent deployment, after potentially long infrastructure provisioning.
6. The workflow invokes a synthetic case after each agent deployment,
   materializing the runtime identity on its first token request. It
   verifies the exact runtime principal in Cosmos authorization errors,
   applies [the existing RBAC module](infra/modules/cosmos-rbac.bicep)
   when needed, and verifies live access before continuing. Cached
   `AGENT_PRINCIPAL_ID` variables are not used by CI. Do not substitute
   the project's managed identity. If an agent retained after teardown
   fails with `invalid_scope`, recover its stale identity or replace only
   that agent while preserving its project and Cosmos case data.
7. Build and deploy the chatbot separately into each restored Container
   Apps environment with [web-chat.bicep](infra/web-chat.bicep), supplying
   that environment's Foundry project, deployment label, and a
   digest-pinned image. Refresh the actual UI redirect URLs with
   [setup-web-chat-identity.ps1](scripts/setup-web-chat-identity.ps1) and
   [setup-reviewer-identity.ps1](scripts/setup-reviewer-identity.ps1).
   Update `WEB_CHAT_APP_NAME` and `WEB_CHAT_URL` in the corresponding
   GitHub environment and refresh the wiki deployment links.
8. Verify both Foundry projects and active agents, both MCP services, UI
   health and sign-in, bilingual agent responses, and a synthetic
   submission reaching the reviewer queue. Confirm that no
   applicant-facing amount is released without employee approval.
   Passing offline tests alone does not establish live demo readiness.
