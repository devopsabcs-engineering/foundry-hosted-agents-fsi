---
title: Infrastructure
description: Bicep templates for retained pilot environments and isolated opt-in showcases.
---

Bicep source for the quote preparation pilot. Deployment runs from
`.github/workflows/deploy-and-evaluate.yml` against a single shared resource
group that holds both the staging and production environments.

See the [architecture](../docs/architecture.md)
([French](../docs/fr/architecture.md)) for component and identity boundaries.
The [approved release evidence](../docs/showcase-evidence.md#current-approved-release)
records runtime `42c627c`, staging v7 and production v8 in release `40567253202`.
These are recorded release versions, not a fresh health check. Preserve these retained
environments; compiling a template is not permission to deploy or tear it down.

> [!NOTE]
> The production `azd` environment's name (and every resource name derived
> from it -- e.g. `cosmos-desjardins-quote-preparation-poc`,
> `aif-desjardins-quote-preparation-poc`) carries a historical `-poc` suffix.
> Despite that suffix, **`-poc` resources are production**, not a separate
> proof-of-concept deployment -- do not confuse them when reading resource
> names, Azure Portal listings, or CI logs. The wiki's Deployment Links table
> labels rows `(production)`/`(staging)` explicitly for this reason; trust
> that label over any `-poc`/`-staging` suffix you see in a URL or resource
> name.

## Templates

The primary foundation uses two templates, and the split is deliberate.

* `network.bicep` — virtual network, five subnets, the Cosmos private DNS
  zone, and its virtual network link. Deployed once for the whole resource
  group under the fixed deployment name `network-foundation`.
* `main.bicep` / `main.parameters.json` — everything else. Deployed twice,
  once per environment, with `environmentName` driving every derived name.

A virtual network is a single resource whose subnets are properties, so an
ARM write that omits `subnets` deletes the ones it does not name. Declaring
the network inside `main.bicep` would mean the staging deployment deletes
production's subnets and the production deployment deletes staging's. Keeping
it in its own template removes that failure mode entirely.

`web-chat.bicep` is deployed out of band with a direct
`az deployment group create --template-file infra/web-chat.bicep` against the
environment `main.bicep` already provisioned, rather than by the main graph.

`memory-showcase.bicep` / `memory-showcase.json` is another opt-in, additive
template outside the primary environment graph. It creates only the isolated
`showcase-memory-embedding` deployment on an existing staging Foundry account:
`text-embedding-3-small` version `1`, regional `Standard`, capacity `1`.
It does not create a memory store or attach memory to the hosted agent.
Obtain separate target/artifact approval and preview in incremental mode;
do not reprovision `main.bicep` or the whole azd project for this prerequisite.
See the [native runbook](../docs/native-showcase.md#isolated-memory-embedding-prerequisite)
for compatibility, quota, retention and authorization boundaries.

The existing staging store `showcase-synthetic-memory` is a separate service
resource, not an output of this template. Its verified configuration uses
`gpt-4o-mini`, `showcase-memory-embedding`, a 3600-second default TTL, disabled
user-profile/chat-summary extraction and service-default procedural extraction.
Positive and cross-scope checks and the reviewer workload's HTTP 403 are
distinct retrieval and caller-role controls, not a per-agent ACL. Memory is
not attached to the quote agent and does not replace the Cosmos approval store.

## Isolated Langfuse pilot

[`langfuse-pilot.bicep`](langfuse-pilot.bicep) and its
[cloud-init](langfuse-pilot/cloud-init.yaml)/[Compose](langfuse-pilot/docker-compose.yml)
files are outside the main deployment graph. The template defaults to
`Standard_D4s_v5`; the captured pilot inventory records `Standard_D4s_v6`.
The six-service, digest-pinned Langfuse 4.70.1 stack publishes only web on
`127.0.0.1:3000`. Follow the [English integration guide](../docs/langfuse-integration.md)
or [French guide](../docs/fr/langfuse-integration.md) for separate approval,
cost, onboarding, operator access and explicit post-onboarding
`AUTH_DISABLE_SIGNUP=true` hardening on a new instance.

The [captured pilot evidence](../docs/langfuse-pilot-evidence.md)
([French](../docs/fr/langfuse-pilot-evidence.md)) proves VM-local synthetic
ingestion and retained account/project state. The last captured power check
confirmed deallocation at `2026-10-28T20:34:18Z`. Operator SSH remains blocked
in the recorded access evidence; do not restore governance-removed rules.
Remote Foundry delivery and matching Azure backend receipt are unverified.
Production export remains disabled. No pilot deployment or startup is part of
documentation generation.

## Modules

| Module | Provisions |
| --- | --- |
| `modules/monitoring.bicep` | Log Analytics workspace and Application Insights component |
| `modules/ai-foundry.bicep` | Foundry account and project, model deployment, and the `application-conn` and `rulebook-conn` MCP toolbox connections |
| `modules/mcp-container-apps.bicep` | VNet-integrated Container Apps environment and the `*-application-server` and `*-rulebook-server` apps |
| `modules/cosmos-db.bicep` | Cosmos account, database, container, and the SQL private endpoint |
| `modules/cosmos-rbac.bicep` | Data-plane role assignments on the Cosmos account |
| `modules/rbac.bicep` | Foundry control-plane role assignments |
| `modules/reviewer-app.bicep` | Reviewer Container App, deployed only when `reviewerClientId` is supplied |

## Network posture

Cosmos is unreachable from the public internet. An Azure Policy assignment at
the tenant root applies a `modify` effect that forces
`publicNetworkAccess: 'Disabled'` on every Cosmos account, so the template
declares `Disabled` to match what the platform enforces regardless. A template
that declares `Enabled` produces permanent drift and, in practice, HTTP 500
responses from every workload that reads the case store.

Reachability comes from the private endpoint plus the
`privatelink.documents.azure.com` zone, which together give callers inside the
virtual network an address the Cosmos firewall accepts. The Container Apps
environments are VNet-integrated for the same reason, and the Foundry accounts
use `networkInjections` so the agent runtime resolves the same private address.

Both `vnetConfiguration` on a managed environment and `networkInjections` on a
Foundry account are creation-time only. Moving an existing environment onto the
network requires deleting and recreating it, which is what
`.github/workflows/network-rebuild-teardown.yml` exists to do.

## Runtime identity and case-store access

The hosted agent's Entra principal is distinct from the Foundry project identity.
`agentPrincipalId` optionally grants Cosmos access in Bicep, but CI does not
trust a cached `AGENT_PRINCIPAL_ID`. After deployment, a synthetic invocation
materializes the runtime principal; `eval/ensure_agent_cosmos_access.py` checks it,
and the workflow applies the existing Cosmos RBAC module when needed before
rechecking live access. Private DNS/network reachability and data-plane
authorization must both succeed. The reviewer workload has its own identity;
browser role claims authorize reviewer commands, not direct Cosmos access.

## Working on these templates

`main.json` and `network.json` are committed build artifacts. Regenerate and
commit them alongside any Bicep edit:

```powershell
az bicep build --file infra/network.bicep --outfile infra/network.json
az bicep build --file infra/main.bicep --outfile infra/main.json
```

Deployment target identities and endpoints are parameterized or derived from
resources; service URLs, resource-name defaults and placeholder images are not
credentials. Review environment parameters and digest-pinned images before an
approved deployment.
