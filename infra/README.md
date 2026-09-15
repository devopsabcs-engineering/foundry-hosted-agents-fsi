# Infrastructure

Bicep source for the quote preparation pilot. Deployment runs from
`.github/workflows/deploy-and-evaluate.yml` against a single shared resource
group that holds both the staging and production environments.

## Templates

Two templates deploy into that resource group, and the split is deliberate.

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

`web-chat.bicep` is deployed out of band by `scripts/deploy-web-chat.ps1`
rather than by the main graph.

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

## Working on these templates

`main.json` and `network.json` are committed build artifacts. Regenerate and
commit them alongside any Bicep edit:

```powershell
az bicep build --file infra/network.bicep --outfile infra/network.json
az bicep build --file infra/main.bicep --outfile infra/main.json
```

No tenant ID, subscription ID, credential, or endpoint is hard-coded in any
template here. All of them arrive as parameters.
