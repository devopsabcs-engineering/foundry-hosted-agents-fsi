<!-- markdownlint-disable-file -->
# Reviewer App Infrastructure Research — Existing Bicep Codebase

Date: 2026-09-15
Status: **Complete** (research only; no files modified)
Repository root: c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents-fsi

## Research Topics and Questions

1. Deployment topology (scope, azd conventions, main vs web-chat relationship)
2. Parameter conventions and naming/uniqueness strategy
3. Container Apps pattern (verbatim resource definitions, image flow)
4. Identity and RBAC model
5. Monitoring module and how telemetry is wired
6. Idempotency patterns
7. Outputs and their consumers
8. Gaps for new work: Cosmos DB, second (reviewer) Container App, Cosmos data-plane RBAC

Files read in full: infra/main.bicep, infra/main.parameters.json, infra/web-chat.bicep, infra/modules/ai-foundry.bicep, infra/modules/mcp-container-apps.bicep, infra/modules/monitoring.bicep, infra/modules/rbac.bicep, infra/README.md, azure.yaml. Supporting evidence also pulled from .github/workflows/deploy-and-evaluate.yml, .github/workflows/web-chat-build.yml, apps/web-chat/app.py, src/quote-preparation-agent/approval_repository.py.

---

## 0. Overarching Gate Constraint (read this first)

Every `.bicep` file and `azure.yaml` carries an identical AUTHOR-ONLY banner in lines 1-9 (for `azure.yaml`, lines 3-9) stating the template is gated behind **G2 (platform/security)**, **G3 (reproducible compatibility)**, and **G6 (regulatory/privacy)** sign-off, and that `azd provision` / `azd deploy` / `azd up` / `az deployment group create` must not be run until those gates clear.

Evidence:

* infra/main.bicep lines 1-9
* infra/web-chat.bicep lines 1-19
* infra/modules/ai-foundry.bicep lines 1-13
* infra/modules/mcp-container-apps.bicep lines 1-25
* infra/modules/monitoring.bicep lines 1-9
* infra/modules/rbac.bicep lines 1-9
* azure.yaml lines 3-9
* infra/README.md lines 1-14 ("Status: **authored, not deployed, not reviewed.**")

**Implication for the new work:** any new file added to `infra/` must carry the same banner block, and the implementing agent must not run an apply command. However, note the contradiction below (Section 6, Non-idempotency / inconsistency notes): `.github/workflows/deploy-and-evaluate.yml` *does* run real `azd provision`/`azd deploy` against staging and production, and its own banner (lines 5-8) acknowledges this. So the repository is in a mixed state: the templates claim "never deployed" while CI has demonstrably deployed them.

---

## 1. Deployment Topology

### 1.1 Scope of main.bicep

**`targetScope = 'resourceGroup'`** — infra/main.bicep line 11.

This is *not* a subscription-scoped template. There is no `resourceGroup` resource creation, no `subscription()` scoping, and no `az deployment sub create` anywhere. The resource group is supplied externally.

Confirmed by CI: `.github/workflows/deploy-and-evaluate.yml` line 151-157 runs `az deployment group what-if --resource-group "$AZURE_RESOURCE_GROUP" --template-file infra/main.bicep`, and line 204 does `azd env set AZURE_RESOURCE_GROUP "${{ vars.AZURE_RESOURCE_GROUP }}"` — i.e. the RG is a pre-existing, externally-owned resource passed in as an azd environment variable.

### 1.2 What web-chat.bicep does and how it relates to main.bicep

infra/web-chat.bicep is a **separate, standalone, out-of-band deployment — NOT a module referenced by main.bicep**.

Evidence — its own header comment, infra/web-chat.bicep lines 10-18:

```text
// Standalone Container App hosting the internal pilot web-chat frontend
// (apps/web-chat). Deliberately NOT wired into infra/main.bicep or
// azure.yaml -- it is deployed out-of-band via a manual
// `az deployment group create` against this file, into the *existing*
// Container Apps environment, ACR, and Foundry project that
// infra/main.bicep already provisions. See infra/README.md and
// scripts/setup-web-chat-identity.ps1 for the associated Entra app
// registration.
```

Corroborating evidence:

* infra/main.bicep contains exactly four `module` declarations (lines 74, 83, 102, 111) — `monitoring`, `aiFoundry`, `rbac`, `mcpContainerApps`. No reference to `web-chat.bicep`.
* infra/README.md lines 16-31 enumerate "What exists here" and list only `main.bicep` + the four modules. `web-chat.bicep` is **not listed at all** in the README — it was added later (see .copilot-tracking/changes/2026-09-14/hosted-agents-sibling-parity-changes.md line 43) and the README was never updated.
* azure.yaml contains no `infra:` block and no service with a container-app host; `web-chat` appears nowhere in it.
* `.github/workflows/web-chat-build.yml` builds and tests the web-chat app but performs **no** Azure deployment (line 76: `'No Azure deployment or local npm policy changes were performed.'`).

**Coupling model:** web-chat.bicep consumes main.bicep's outputs *by convention, not by reference*. It re-declares the same names as `existing` resources with hardcoded-default parameters that mirror main.bicep's naming expressions:

| web-chat.bicep param | line | default | mirrors |
| --- | --- | --- | --- |
| `environmentName` (Container Apps env) | 27 | `'mcp-staging-mcp-env'` | mcp-container-apps.bicep line 72 `'${namePrefix}-mcp-env'` |
| `foundryAccountName` | 45 | `'aif-desjardins-quote-preparation-staging'` | main.bicep line 20 `'aif-${environmentName}'` |
| `foundryProjectName` | 48 | `'proj-desjardins-quote-preparation-staging'` | main.bicep line 23 `'proj-${environmentName}'` |

This string-duplication coupling is fragile and is the single most likely place for the new work to break (see Section 8.4).

### 1.3 azd convention status

azd **is** in play for main.bicep, but **only partially**, and **the standard azd resource-tagging convention is entirely absent**.

What is present:

* `azure.yaml` at repo root (schema: `https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json`, line 1; `name: desjardins-quote-preparation-workshop`, line 11).
* `infra/main.parameters.json` uses azd token substitution: `${AZURE_ENV_NAME}` (line 6), `${AZURE_LOCATION}` (line 9), `${MCP_ACR_NAME}` (line 12), `${MCP_NAME_PREFIX=}` (line 15 — note the `=` suffix meaning "default to empty if unset"), `${APPLICATION_MCP_IMAGE}` (line 18), `${RULEBOOK_MCP_IMAGE}` (line 21).
* No `infra:` block in azure.yaml → azd falls back to its default of `./infra/main.bicep` + `./infra/main.parameters.json`.
* Outputs deliberately named in azd/env-var style so they land in the azd environment: `FOUNDRY_PROJECT_ENDPOINT` (line 126), `AZURE_AI_PROJECT_ID` (line 129), `APPLICATION_MCP_URL` (line 132), `RULEBOOK_MCP_URL` (line 133).

What is **absent**:

* **No `azd-service-name` tag on any resource.** Grep for `azd-service-name` across `infra/` returns nothing.
* **No `azd-env-name` tag on any resource.**
* **No `resourceToken` / `uniqueString()` / abbreviation-file convention** (the usual `azd` starter-template pattern).
* Only two resources carry tags at all — the web-chat Container App (infra/web-chat.bicep lines 95-98: `environment: 'staging'`, `purpose: 'internal-pilot-web-chat'`). Every other resource in the repo is untagged.

**azure.yaml services are all Foundry-plane, not compute-plane** (azure.yaml lines 12-84):

| service | host | notes |
| --- | --- | --- |
| `ai-project` | `azure.ai.project` | gpt-4o-mini deployment, GlobalStandard cap 10 |
| `rulebook-conn` | `azure.ai.connection` | `endpoint: ${RULEBOOK_MCP_URL}`, `type: remote-tool` |
| `application-conn` | `azure.ai.connection` | `endpoint: ${APPLICATION_MCP_URL}`, `type: remote-tool` |
| `quote-tools` | `azure.ai.toolbox` | MCP tool bindings |
| `quote-preparation-agent` | `azure.ai.agent` | `kind: hosted`, `project: ./src/quote-preparation-agent`, `runtime: python_3_13` |

**Critical consequence:** `azd deploy` deploys *only the hosted agent and Foundry connections*. It does **not** deploy Container Apps. Container App images are supplied as **Bicep parameters** and therefore change only on `azd provision`. Any new Container App added to `main.bicep` inherits this — it will be updated by `azd provision`, not `azd deploy`.

---

## 2. Parameter Conventions

### 2.1 infra/main.bicep — full parameter list

| Line | Param | Type | Default | Decorators |
| --- | --- | --- | --- | --- |
| 14 | `location` | string | `resourceGroup().location` | `@description('Azure region for all resources')` (line 13) |
| 17 | `environmentName` | string | *(required, no default)* | `@description('Base name used to derive resource names (e.g. dev, poc)')` (line 16) |
| 20 | `accountName` | string | `'aif-${environmentName}'` | `@description('Foundry account (Microsoft.CognitiveServices/accounts) name')` (line 19) |
| 23 | `projectName` | string | `'proj-${environmentName}'` | `@description('Foundry project name')` (line 22) |
| 26 | `modelDeploymentName` | string | `'gpt-4o-mini'` | line 25, flagged "Placeholder pending Gate G2/G3 sign-off." |
| 29 | `modelName` | string | `'gpt-4o-mini'` | line 28, placeholder |
| 32 | `modelFormat` | string | `'OpenAI'` | line 31 |
| 35 | `modelVersion` | string | `'2024-07-18'` | line 34, placeholder |
| 38 | `modelSkuName` | string | `'GlobalStandard'` | line 37 |
| 41 | `modelSkuCapacity` | int | `endsWith(environmentName, '-staging') ? 50 : 10` | line 40 |
| 44 | `principalIds` | array | `[]` | line 43 — "Leave empty to skip role assignment." |
| 52 | `principalType` | string | `'ServicePrincipal'` | line 46 `@description`, lines 47-51 `@allowed(['ServicePrincipal','User','Group'])` |
| 55 | `logAnalyticsWorkspaceName` | string | `'log-${environmentName}'` | line 54 |
| 58 | `applicationInsightsName` | string | `'appi-${environmentName}'` | line 57 |
| 61 | `mcpAcrName` | string | `''` | line 60 — "Leave empty to use the public placeholder image." |
| 64 | `applicationMcpImage` | string | `'mcr.microsoft.com/k8se/quickstart:latest'` | line 63 |
| 67 | `rulebookMcpImage` | string | `'mcr.microsoft.com/k8se/quickstart:latest'` | line 66 |
| 70 | `mcpNamePrefix` | string | `''` | line 69 — "staging must not share production tool apps." |

Single `var`, infra/main.bicep line 72:

```bicep
var effectiveMcpNamePrefix = !empty(mcpNamePrefix) ? mcpNamePrefix : (endsWith(environmentName, '-staging') ? 'mcp-staging' : 'mcp')
```

### 2.2 infra/web-chat.bicep — full parameter list

| Line | Param | Type | Default | Notes from `@description` |
| --- | --- | --- | --- | --- |
| 21 | `location` | string | `resourceGroup().location` | line 20 |
| 24 | `appName` | string | `'foundry-quote-chat-staging'` | line 23 |
| 27 | `environmentName` | string | `'mcp-staging-mcp-env'` | line 26 — **this is the Container Apps managed environment name, NOT the azd env name** |
| 30 | `acrName` | string | *(required)* | line 29 — "no default; must be supplied at deploy time, matching the env-var-driven MCP_ACR_NAME convention" |
| 33 | `image` | string | *(required)* | line 32 — "Fully digest-pinned image reference ...; never a floating tag" |
| 36 | `tenantId` | string | *(required)* | line 35 |
| 39 | `clientId` | string | *(required)* | line 38 — from scripts/setup-web-chat-identity.ps1 |
| 42 | `pilotGroupId` | string | *(required)* | line 41 |
| 45 | `foundryAccountName` | string | `'aif-desjardins-quote-preparation-staging'` | line 44 |
| 48 | `foundryProjectName` | string | `'proj-desjardins-quote-preparation-staging'` | line 47 |

No `targetScope` is declared in web-chat.bicep → it defaults to `resourceGroup`.

### 2.3 Naming uniqueness strategy — exact expressions

**There is no `uniqueString()`, no `resourceToken`, and no abbreviations file anywhere in `infra/`.** Uniqueness is achieved purely by requiring `environmentName` to be unique and suffixing it.

Reproduce these exact patterns:

```bicep
// infra/main.bicep:20
param accountName string = 'aif-${environmentName}'
// infra/main.bicep:23
param projectName string = 'proj-${environmentName}'
// infra/main.bicep:55
param logAnalyticsWorkspaceName string = 'log-${environmentName}'
// infra/main.bicep:58
param applicationInsightsName string = 'appi-${environmentName}'
```

```bicep
// infra/main.bicep:72 -- environment differentiation by SUFFIX, not by token
var effectiveMcpNamePrefix = !empty(mcpNamePrefix) ? mcpNamePrefix : (endsWith(environmentName, '-staging') ? 'mcp-staging' : 'mcp')
// infra/main.bicep:41 -- same suffix test drives capacity
param modelSkuCapacity int = endsWith(environmentName, '-staging') ? 50 : 10
```

```bicep
// infra/modules/mcp-container-apps.bicep:71-72
var logAnalyticsWorkspaceName = '${namePrefix}-mcp-logs'
var environmentName = '${namePrefix}-mcp-env'
// infra/modules/mcp-container-apps.bicep:57  (user-assigned identity)
name: '${namePrefix}-image-pull'
// infra/modules/mcp-container-apps.bicep:100
name: '${namePrefix}-application-server'
// infra/modules/mcp-container-apps.bicep:154
name: '${namePrefix}-rulebook-server'
```

```bicep
// infra/web-chat.bicep:68  (user-assigned identity)
name: '${appName}-identity'
```

Global-uniqueness note: the only globally-unique-name resource today is the Foundry account (`customSubDomainName: accountName`, infra/modules/ai-foundry.bicep line 76). The repo relies on `environmentName` being globally distinct. **A Cosmos DB account name is also globally unique — the same reliance carries over, and there is no `uniqueString()` safety net in this codebase to fall back on.**

---

## 3. Container Apps Pattern

### 3.1 Container Apps Environment (verbatim)

infra/modules/mcp-container-apps.bicep lines 74-97:

```bicep
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}
```

Note: this module provisions **its own second Log Analytics workspace** (`${namePrefix}-mcp-logs`), entirely separate from `monitoring.bicep`'s `log-${environmentName}`. Also note there is **no VNet / `vnetConfiguration`** — this is a public (Basic Agent Setup) environment, deliberately, per the header comment at infra/modules/mcp-container-apps.bicep lines 17-23.

### 3.2 MCP Container App (verbatim — the `application-server` app)

infra/modules/mcp-container-apps.bicep lines 99-151:

```bicep
resource applicationContainerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-application-server'
  location: location
  identity: isolatedPullIdentity ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity!.id}': {}
    }
  } : {
    type: 'SystemAssigned'
  }
  dependsOn: [pullRole]
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
      }
      registries: useAcr
        ? [
            {
              server: acr.properties.loginServer
              identity: isolatedPullIdentity ? pullIdentity!.id : 'system'
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'application-server'
          image: applicationImage
          env: [
            {
              name: 'PORT'
              value: string(containerPort)
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}
```

`rulebookContainerApp` (lines 153-205) is byte-for-byte identical apart from `name: '${namePrefix}-rulebook-server'`, `name: 'rulebook-server'`, and `image: rulebookImage`.

### 3.3 web-chat Container App (verbatim)

infra/web-chat.bicep lines 92-138:

```bicep
resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    environment: 'staging'
    purpose: 'internal-pilot-web-chat'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [pullRole, invokeRole]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'http'
      }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'web-chat'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_CLIENT_ID', value: clientId }
          { name: 'PILOT_GROUP_ID', value: pilotGroupId }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'AGENT_ENDPOINT', value: 'https://${foundryAccountName}.services.ai.azure.com/api/projects/${foundryProjectName}/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1' }
        ]
        probes: [
          { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 15, periodSeconds: 30 }
          { type: 'Readiness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}
```

### 3.4 Pattern summary table

| Aspect | MCP apps (module) | web-chat (standalone) |
| --- | --- | --- |
| API version | `Microsoft.App/containerApps@2024-03-01` | same |
| Env API version | `Microsoft.App/managedEnvironments@2024-03-01` (created) | same (`existing`, line 50) |
| Identity | conditional: UserAssigned `${namePrefix}-image-pull` if ACR supplied, else SystemAssigned | always UserAssigned `${appName}-identity` |
| `activeRevisionsMode` | **not set** (ARM default `Single`) | explicitly `'Single'` |
| Ingress | `external: true`, `targetPort: containerPort`, `transport: 'http'` | `external: true`, `allowInsecure: false`, `targetPort: 8000`, `transport: 'http'` |
| Registry | conditional array, `identity: pullIdentity.id` or `'system'` | unconditional, `identity: identity.id` |
| **Secrets** | **none — no `secrets` block anywhere in the repo** | **none** |
| Env vars | `PORT` only, via `string(containerPort)` | 5 plain-value vars, no `secretRef` |
| Resources | `cpu: json('0.5')`, `memory: '1Gi'` | identical |
| Probes | **none** | Liveness + Readiness on `/healthz`:8000 |
| Scale | `minReplicas: 0`, `maxReplicas: 1` (scale-to-zero) | `minReplicas: 1`, `maxReplicas: 1` |
| **Scale rules** | **none — only min/max, no HTTP/custom rules anywhere** | **none** |
| Tags | none | `environment` / `purpose` |
| `dependsOn` | `[pullRole]` (explicit, for RBAC propagation) | `[pullRole, invokeRole]` |

**No `secrets` block, no `secretRef`, and no Key Vault reference exists anywhere in this repository's Bicep.** Every configuration value is a plain-text env var or a Bicep parameter. The only `@secure()` parameter in the whole codebase is `applicationInsightsConnectionString` at infra/modules/ai-foundry.bicep line 58-59.

### 3.5 Image reference lifecycle

1. **First deploy / no ACR:** defaults are the public placeholder `mcr.microsoft.com/k8se/quickstart:latest` (infra/main.bicep lines 64, 67; module lines 37, 40). `var useAcr = !empty(acrName)` (module line 45) then yields an empty `registries: []`.
2. **CI build:** `.github/workflows/deploy-and-evaluate.yml` lines 209-221 runs `az acr build`, resolves the digest with `az acr repository show ... --query digest`, validates it against `^sha256:[a-f0-9]{64}$`, then `azd env set "${SERVER^^}_MCP_IMAGE" "${REGISTRY}/staging/${SERVER}-mcp@${DIGEST}"`.
3. **Parameter plumbing:** `APPLICATION_MCP_IMAGE` / `RULEBOOK_MCP_IMAGE` flow through infra/main.parameters.json lines 17-22 into main.bicep params → module params → `image:` property.
4. **Update mechanism:** a subsequent code deploy updates the image by re-running **`azd provision`** (workflow lines 226-234), **not `azd deploy`**. `azd deploy` (line 240) only touches the Foundry hosted agent.
5. **web-chat:** `image` is a required param with no default, documented as "Fully digest-pinned ...; never a floating tag" (line 32), and is applied by a hand-run `az deployment group create`.

**Implication for the reviewer app:** if it goes into `main.bicep`, its image must follow the same digest-pinned param → `azd provision` path, and CI must be extended to build/push/pin it. If it goes standalone like web-chat, it is manual-operator-only and outside CI entirely.

---

## 4. Identity and RBAC

### 4.1 Identity inventory

| Identity | Type | Where created | Consumed by |
| --- | --- | --- | --- |
| Foundry account MI | SystemAssigned | infra/modules/ai-foundry.bicep lines 71-73 | output `accountPrincipalId` (line 150) — **unused by main.bicep** |
| Foundry project MI | SystemAssigned | infra/modules/ai-foundry.bicep lines 100-102 | output `projectPrincipalId` (line 153) — **unused by main.bicep** |
| `${namePrefix}-image-pull` | UserAssigned | infra/modules/mcp-container-apps.bicep lines 56-59 (`if (isolatedPullIdentity)`) | both MCP apps' `identity` + `registries[].identity` |
| `${appName}-identity` | UserAssigned | infra/web-chat.bicep lines 67-70 | web-chat app identity, ACR pull, Foundry invoke; output `principalId` (line 141) |

Note the MCP module comment, infra/modules/mcp-container-apps.bicep lines 46-49, explaining *why* a dedicated user-assigned identity per environment exists:

```text
// Every environment (staging and production) gets its own pull identity with an
// automatically granted, idempotent AcrPull role assignment -- relying on an
// out-of-band manual grant for a shared system-assigned identity left production
// with no ACR permission and revisions that never provisioned ("Operation expired").
```

### 4.2 infra/modules/rbac.bicep — full structure (verbatim, lines 11-58)

```bicep
@description('Name of the existing Foundry (Microsoft.CognitiveServices/accounts) resource to scope role assignments to')
param accountName string

@description('Principal IDs to receive the Foundry roles in roleDefinitionIds')
param principalIds array

@description('Principal type applied to every entry in principalIds')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

@description('Foundry role definition GUIDs to assign to every principal in principalIds')
param roleDefinitionIds array = [
  '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
  'eadc314b-1a2d-4efa-be10-5d325db5065e' // Foundry Project Manager
  'eed3b665-ab3a-47b6-8f48-c9382fb1dad6' // Foundry Agent Consumer
]

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

var principalRolePairs = map(
  principalIds,
  principalId =>
    map(roleDefinitionIds, roleDefinitionId => {
      principalId: principalId
      roleDefinitionId: roleDefinitionId
    })
)
var assignmentPairs = reduce(principalRolePairs, [], (cur, next) => concat(cur, next))

resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for pair in assignmentPairs: {
    name: guid(account.id, pair.principalId, pair.roleDefinitionId)
    scope: account
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', pair.roleDefinitionId)
      principalId: pair.principalId
      principalType: principalType
    }
  }
]
```

Key conventions to replicate:

* Role definitions are **bare GUID string constants with an inline `// role name` comment**, never `resourceId()` lookups by name.
* `roleDefinitionId` is always built with `subscriptionResourceId('Microsoft.Authorization/roleDefinitions', <guid>)`.
* Role assignment `name` is always `guid(<scopeResource>.id, <principalId>, <discriminator>)` — deterministic, so re-deploy is a no-op.
* The scope resource is pulled in via `existing` and attached with `scope:`.
* Cartesian product of principals × roles is built with `map` + `reduce(..., [], (cur, next) => concat(cur, next))` and iterated with a `for` loop.

### 4.3 Complete role assignment inventory

| # | Role | GUID | Scope | Principal | Assignment name expression | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Foundry User | `53ca6127-db72-4b80-b1b0-d745d6d5456d` | CognitiveServices **account** | each `principalIds[]` entry | `guid(account.id, pair.principalId, pair.roleDefinitionId)` | rbac.bicep 27, 47-55 |
| 2 | Foundry Project Manager | `eadc314b-1a2d-4efa-be10-5d325db5065e` | CognitiveServices **account** | each `principalIds[]` entry | same | rbac.bicep 28 |
| 3 | Foundry Agent Consumer | `eed3b665-ab3a-47b6-8f48-c9382fb1dad6` | CognitiveServices **account** | each `principalIds[]` entry | same | rbac.bicep 29 |
| 4 | AcrPull | `7f951dda-4ed3-4680-a7ca-43fe172d538d` | **ACR** | `${namePrefix}-image-pull` | `guid(acr!.id, pullIdentity!.id, 'AcrPull')` | mcp-container-apps.bicep 61-69 |
| 5 | AcrPull | `7f951dda-4ed3-4680-a7ca-43fe172d538d` | **ACR** | `${appName}-identity` | `guid(registry.id, identity.id, 'AcrPull')` | web-chat.bicep 72-80 |
| 6 | Foundry User | `53ca6127-db72-4b80-b1b0-d745d6d5456d` | Foundry **project** (child resource) | `${appName}-identity` | `guid(project.id, identity.id, 'FoundryUser')` | web-chat.bicep 82-90 |

**Critical finding — roles 1-3 are effectively never assigned.** `principalIds` defaults to `[]` (main.bicep line 44), the `rbac` module is guarded by `if (!empty(principalIds))` (main.bicep line 102), and **`principalIds` is not supplied in `infra/main.parameters.json` (lines 4-23) nor in the CI `what-if`/`azd provision` parameterization (`.github/workflows/deploy-and-evaluate.yml` lines 154-157, 200-205)**. So in every real deployment path today, `modules/rbac.bicep` is skipped entirely. Any new work that assumes the rbac module runs is building on a path that has never executed.

**Also note:** neither `accountPrincipalId` nor `projectPrincipalId` (ai-foundry.bicep outputs at lines 150, 153) is consumed anywhere. The hosted agent's runtime identity is therefore **not currently granted anything by this Bicep** — see clarifying question Q1.

---

## 5. Monitoring

infra/modules/monitoring.bicep, full resource definitions (lines 23-41):

```bicep
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
  }
}
```

* **Log Analytics:** SKU `PerGB2018`, `retentionInDays` param default `30` (line 21).
* **App Insights:** `kind: 'web'`, `Application_Type: 'web'`, **`IngestionMode: 'LogAnalytics'`** (workspace-based) — line 40.
* **`DisableLocalAuth` is NOT set** anywhere. It therefore defaults to `false`, so connection-string / instrumentation-key ingestion works without a managed-identity credential. (Relevant: with workspace-based AI, `az monitor app-insights query` returns empty — you must query the Log Analytics workspace directly.)
* Foundry account also sets `disableLocalAuth: false` explicitly (ai-foundry.bicep line 77).

### 5.1 How the connection string flows

```text
monitoring.bicep:50  output applicationInsightsConnectionString
   |
   +--> main.bicep:90   applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
   |        -> ai-foundry.bicep:58-59 @secure() param
   |        -> ai-foundry.bicep:109-124 telemetryConnection
   |             category: 'AppInsights', authType: 'ApiKey', credentials.key = <connection string>
   |             target / metadata.ResourceId = applicationInsightsResourceId
   |
   +--> main.bicep:131  output applicationInsightsConnectionString
            -> azure.yaml:63-64  APPLICATIONINSIGHTS_CONNECTION_STRING: ${applicationInsightsConnectionString}
               (injected into the hosted agent container)
```

Also: `main.bicep:89 applicationInsightsResourceId: monitoring.outputs.applicationInsightsId`, and `main.bicep:130 output logAnalyticsWorkspaceId`.

**Gap:** the Container Apps environment does **not** consume `monitoring.bicep`'s workspace. It creates and uses its own (`${namePrefix}-mcp-logs`, mcp-container-apps.bicep lines 71, 74-83, 88-96). There are **two** Log Analytics workspaces per environment, and Container App console/system logs land in the MCP one, not `log-${environmentName}`.

---

## 6. Idempotency Patterns

### 6.1 `existing` keyword usage

| File | Line | Resource | Guard |
| --- | --- | --- | --- |
| infra/modules/rbac.bicep | 32 | `Microsoft.CognitiveServices/accounts@2025-06-01` | none (module itself is conditional) |
| infra/modules/mcp-container-apps.bicep | 52 | `Microsoft.ContainerRegistry/registries@2023-07-01` | `if (useAcr)` |
| infra/web-chat.bicep | 50 | `Microsoft.App/managedEnvironments@2024-03-01` | none |
| infra/web-chat.bicep | 54 | `Microsoft.ContainerRegistry/registries@2023-07-01` | none |
| infra/web-chat.bicep | 58 | `Microsoft.CognitiveServices/accounts@2025-06-01` | none |
| infra/web-chat.bicep | 62 | `Microsoft.CognitiveServices/accounts/projects@2025-06-01` | `parent: account` |

### 6.2 Conditional deployment `if (...)`

| File | Line | Target | Condition |
| --- | --- | --- | --- |
| infra/main.bicep | 102 | `module rbac` | `if (!empty(principalIds))` |
| infra/modules/mcp-container-apps.bicep | 52 | `resource acr` | `if (useAcr)` |
| infra/modules/mcp-container-apps.bicep | 56 | `resource pullIdentity` | `if (isolatedPullIdentity)` |
| infra/modules/mcp-container-apps.bicep | 61 | `resource pullRole` | `if (isolatedPullIdentity)` |
| infra/modules/ai-foundry.bicep | 161 | `resource applicationConnection` | `if (!empty(applicationMcpUrl))` |
| infra/modules/ai-foundry.bicep | 172 | `resource rulebookConnection` | `if (!empty(rulebookMcpUrl))` |

Ternary-in-property idempotency is also used inline (not `if`): `identity:` and `registries:` in both MCP apps (module lines 102-108, 113-122; 156-162, 167-176).

**Bicep safe-dereference operator `!`** is used for conditional resources: `acr!.id`, `pullIdentity!.id`, `pullIdentity!.properties.principalId` (module lines 62, 66, 105, 118, 159, 172). This requires a reasonably current Bicep CLI. Any new conditional resource must use the same `!` form or the build breaks.

### 6.3 Deterministic naming

All role assignment names are `guid(...)` of stable inputs (see table in 4.3). All resource names are deterministic string interpolations of parameters — no `newGuid()`, no `utcNow()`, no `uniqueString(deployment().name)`.

### 6.4 What-if validation

`.github/workflows/deploy-and-evaluate.yml` lines 121-157 — a dedicated `bicep-validate` job:

```yaml
      - name: az bicep build (full module graph)
        run: az bicep build --file infra/main.bicep

      - name: az deployment group what-if (staging resource group; preview only, no apply)
        ...
          az deployment group what-if \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --template-file infra/main.bicep \
            --parameters environmentName="$STAGING_AZD_ENV_NAME" location="$AZURE_LOCATION" \
              mcpAcrName="$MCP_ACR_NAME" applicationMcpImage="$APPLICATION_MCP_IMAGE" \
              rulebookMcpImage="$RULEBOOK_MCP_IMAGE"
```

Note the what-if parameterization is a **hand-maintained list** that does not read `main.parameters.json`. **Any new required parameter added to `main.bicep` must be added to this `--parameters` list too, or the `bicep-validate` job fails.** This is the easiest thing to miss.

### 6.5 Things that are NOT idempotent (or are idempotency hazards)

1. **`logAnalyticsWorkspace.listKeys().primarySharedKey`** — infra/modules/mcp-container-apps.bicep line 93. A `list*()` call inside a template property means every `what-if` reports this as a potential change and the deployment always re-reads a secret. It is functionally idempotent but produces perpetual what-if noise.
2. **`azd provision` needs a retry loop for ARM 409.** `.github/workflows/deploy-and-evaluate.yml` lines 226-234 wrap "Provision staging infrastructure (idempotent)" in a 3-attempt/60s-backoff loop precisely because a re-deploy can hit `A resource with this name already exists or is in a conflicting state`. Documented in .copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md line 43. **Re-deploy is not cleanly idempotent in practice.**
3. **Container App first-revision provisioning can hang.** .copilot-tracking/plans/logs/2026-09-13/...-log.md line 151 (WI-13) records a production first revision stuck `ActivationFailed` for 20+ minutes until "Operation expired", where repeat runs did not reproduce it. **A new Container App added to `main.bicep` risks reintroducing this on its very first deploy** — especially with `minReplicas: 0` and no probes.
4. **`modelSkuCapacity` and `effectiveMcpNamePrefix` branch on `endsWith(environmentName, '-staging')`** (main.bicep lines 41, 72). Renaming the azd environment silently changes resource names and capacity — a "rename = recreate everything" hazard.
5. **web-chat.bicep's hardcoded default names** (lines 27, 45, 48) drift silently if `environmentName`/`mcpNamePrefix` change in main.bicep. Nothing validates the match.
6. **RBAC propagation races** are mitigated only by explicit `dependsOn: [pullRole]` / `dependsOn: [pullRole, invokeRole]` (module lines 109, 163; web-chat line 105). A new app with a new role assignment must do the same.

---

## 7. Outputs

### 7.1 infra/main.bicep outputs (lines 122-133)

| Line | Output | Source | Consumed by |
| --- | --- | --- | --- |
| 122 | `accountName` | `aiFoundry.outputs.accountName` | azd env; referenced conceptually by web-chat.bicep `foundryAccountName` |
| 123 | `accountEndpoint` | `aiFoundry.outputs.accountEndpoint` | azure.yaml line 70 `AZURE_OPENAI_ENDPOINT: ${accountEndpoint}` |
| 124 | `projectName` | `aiFoundry.outputs.projectName` | azd env; mirrored by web-chat.bicep `foundryProjectName` |
| 125 | `modelDeploymentName` | `aiFoundry.outputs.modelDeploymentName` | azd env |
| 126 | `FOUNDRY_PROJECT_ENDPOINT` | `aiFoundry.outputs.projectEndpoint` | azure.yaml line 68 `AZURE_AI_PROJECT_ENDPOINT`; workflow line 241 `jq -er '.FOUNDRY_PROJECT_ENDPOINT'` |
| 129 | `AZURE_AI_PROJECT_ID` | `aiFoundry.outputs.projectId` | azd `azure.ai.agent` host — comment lines 127-128: "ARM resource ID of the Foundry project -- required by azd's azure.ai.agent host target to publish/deploy hosted agents" |
| 130 | `logAnalyticsWorkspaceId` | `monitoring.outputs.logAnalyticsWorkspaceId` | azd env only; no in-template consumer |
| 131 | `applicationInsightsConnectionString` | `monitoring.outputs.applicationInsightsConnectionString` | azure.yaml line 64 `APPLICATIONINSIGHTS_CONNECTION_STRING` |
| 132 | `APPLICATION_MCP_URL` | `'https://${mcpContainerApps.outputs.applicationContainerAppFqdn}/mcp'` | azure.yaml lines 30 (`application-conn` endpoint) and 76 |
| 133 | `RULEBOOK_MCP_URL` | `'https://${mcpContainerApps.outputs.rulebookContainerAppFqdn}/mcp'` | azure.yaml lines 26 (`rulebook-conn` endpoint) and 78 |

Note: outputs 132/133 are also fed **back into** the `aiFoundry` module as `applicationMcpUrl`/`rulebookMcpUrl` (main.bicep lines 96-97), creating an intentional intra-template dependency `aiFoundry -> mcpContainerApps`. The comment at ai-foundry.bicep lines 158-160 explains why the connections must be created in Bicep rather than by azd:

```text
// azd's azure.ai.connection host (azure.yaml: application-conn/rulebook-conn) treats connections whose
// endpoint resolves from a bicep output as infrastructure-managed and skips creating them itself
// during `azd deploy` -- so these MCP Toolbox connections must be created here instead.
```

### 7.2 infra/web-chat.bicep outputs (lines 140-141)

| Line | Output | Value | Consumed by |
| --- | --- | --- | --- |
| 140 | `url` | `'https://${web.properties.configuration.ingress.fqdn}'` | operator runbook only (printed after `az deployment group create`) |
| 141 | `principalId` | `identity.properties.principalId` | **nothing today** — no automated consumer |

### 7.3 Module outputs

* monitoring.bicep lines 43-48: `logAnalyticsWorkspaceId`, `logAnalyticsWorkspaceName`, `applicationInsightsId`, `applicationInsightsName`, `applicationInsightsConnectionString`, `applicationInsightsInstrumentationKey`.
* ai-foundry.bicep lines 147-156: `accountId`, `accountName`, `accountEndpoint`, `accountPrincipalId`, `projectId`, `projectName`, `projectPrincipalId`, `modelDeploymentName`, `projectEndpoint`.
* mcp-container-apps.bicep lines 207-209: `containerAppsEnvironmentId`, `applicationContainerAppFqdn`, `rulebookContainerAppFqdn` — **note it outputs the environment *ID*, not the environment *name***.
* rbac.bicep: **no outputs**.

---

## 8. Gaps for the New Work

### 8.0 Current-state context

* **There is no Cosmos DB anywhere in this repository.** A file search for `**/cosmos*` returns zero files; the only mentions are in `.copilot-tracking/research/**` prose. Note that .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md line 2599 claims this repo has an `infra/modules/cosmos-db.bicep` — **that claim is false**; no such file exists. Do not trust it.
* The approval state store is currently **SQLite**: src/quote-preparation-agent/approval_repository.py lines 1-2 ("SQLite-backed ApprovalRepository"), line 52 `import sqlite3`. Its documented semantics (state machine DRAFT → PENDING_REVIEW → APPROVED|REJECTED, idempotent replay of approve/reject, optimistic `WHERE state=... AND revision=...` guard, single-connection `threading.Lock` serialization — lines 4-30) are what a Cosmos port must preserve. The optimistic-concurrency guard maps naturally to a Cosmos ETag / `If-Match` precondition.
* src/quote-preparation-agent/state.py line 11 explicitly notes "no equivalent to the sibling's optional Cosmos DB checkpointer here."

### 8.1 (a) Cosmos DB serverless account + database + container

**Where it slots in:** new file `infra/modules/cosmos-db.bicep`, invoked as a fifth `module` in infra/main.bicep after line 119 (i.e. after `mcpContainerApps`), before the `output` block at line 122.

Follow these conventions:

* Add the AUTHOR-ONLY banner (copy infra/modules/monitoring.bicep lines 1-9 verbatim).
* `param location string = resourceGroup().location` with an `@description`.
* Naming: main.bicep should declare `param cosmosAccountName string = 'cosmos-${environmentName}'` at ~line 59 (alongside `logAnalyticsWorkspaceName`/`applicationInsightsName`), matching the `<abbrev>-${environmentName}` pattern exactly.
* Serverless is expressed as `capabilities: [{ name: 'EnableServerless' }]` on `Microsoft.DocumentDB/databaseAccounts`, with `databaseAccountOfferType: 'Standard'` and a single `locations` entry.
* Database: `Microsoft.DocumentDB/databaseAccounts/sqlDatabases`; container: `.../sqlDatabases/containers`. Use `parent:` nesting (the repo's existing style — see ai-foundry.bicep lines 81, 97, 110, 129 and web-chat.bicep line 63), **not** the `name: '${a}/${b}'` slash form.
* Outputs to add to the module and then re-export from main.bicep: account `name`, `documentEndpoint`, database name, container name, and `id` (needed for RBAC scoping).

**Constraints / conflicts observed:**

* **Global name uniqueness.** Cosmos account names are globally unique and lowercase-only (3-44 chars, letters/digits/hyphens). `environmentName` in staging resolves to `desjardins-quote-preparation-staging` (inferred from web-chat.bicep lines 45/48 defaults) → `cosmos-desjardins-quote-preparation-staging` is **43 characters**, which fits but only just. Production (`...-preparation`) is 35. **Verify length before committing to the prefix; there is no `uniqueString()` fallback convention in this repo to lean on.**
* **Serverless + multi-region is invalid** — keep a single `locations` entry.
* If you set `disableLocalAuth: true` on the Cosmos account (recommended for a data-plane-RBAC-only posture), note it diverges from the repo's existing explicit `disableLocalAuth: false` on the Foundry account (ai-foundry.bicep line 77). That is a deliberate posture decision that likely needs Gate G2 sign-off.
* Do **not** add a new required parameter to main.bicep without also updating `.github/workflows/deploy-and-evaluate.yml` lines 154-157 **and** lines 487-491 (the production what-if/provision parameterization) — those are hand-maintained.

### 8.2 (b) Second Container App for the reviewer web app

Two viable slots; they have materially different consequences.

**Option A — new module wired into `main.bicep`** (e.g. `infra/modules/reviewer-app.bicep`, added as a fifth/sixth `module`).

* Pros: can consume `mcpContainerApps.outputs.containerAppsEnvironmentId` directly (no name-string duplication); its identity `principalId` is available in-template for the Cosmos RBAC module; participates in `azd provision`, `what-if`, and CI.
* Cons: requires a new required `image` param → CI must be extended to `az acr build` + digest-pin the reviewer image (mirror workflow lines 209-221), and the what-if `--parameters` list must be extended. Also inherits idempotency hazard #3 above (first-revision hang).
* **This is the option that makes requirement (c) tractable.**

**Option B — standalone `infra/reviewer-app.bicep`, mirroring `web-chat.bicep`.**

* Pros: matches the existing precedent for a *web UI* app exactly; zero risk to the `azd provision` path; deployable by operator runbook.
* Cons: its managed identity is created in a **separate deployment**, so `main.bicep` cannot reference its `principalId`. Cosmos RBAC would have to be split out or parameterized (see 8.3). Also inherits the hardcoded-name-drift hazard (#5).

**Pattern to copy either way** — start from infra/web-chat.bicep lines 67-138, because it is the only Container App in the repo that has:

* an explicitly UserAssigned identity created alongside the app (lines 67-70),
* `activeRevisionsMode: 'Single'` (line 108),
* `allowInsecure: false` (line 111),
* liveness/readiness probes on `/healthz` (lines 129-132),
* `minReplicas: 1` (line 135) — **use 1, not 0**, for a user-facing app; the MCP `minReplicas: 0` causes cold-start.

The reviewer app should expose port 8000 and a `/healthz` endpoint to match (apps/web-chat/app.py line 195 `@application.get("/healthz")`, and the `AZURE_CLIENT_ID` → `managed_identity_client_id` wiring at apps/web-chat/app.py lines 46, 105).

**Naming:** follow `${appName}-identity` for the identity (web-chat.bicep line 68). If placed in `main.bicep`, prefer a derived name like `param reviewerAppName string = 'reviewer-${environmentName}'` for consistency with the `<prefix>-${environmentName}` convention; if standalone, follow web-chat's literal-default style.

### 8.3 (c) Cosmos data-plane RBAC for the agent identity + the reviewer app identity

**Yes, this is expressible in this Bicep structure — but NOT with `Microsoft.Authorization/roleAssignments`.**

Cosmos DB SQL data-plane access is a **separate, Cosmos-specific RBAC system**:

* Resource type: `Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments` (a **child of the Cosmos account**, not an `Microsoft.Authorization` extension resource).
* `roleDefinitionId` must be a **Cosmos** SQL role definition resource ID, e.g.
  `resourceId('Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions', cosmosAccountName, '00000000-0000-0000-0000-000000000002')` for the built-in **Cosmos DB Built-in Data Contributor**, or `...0001` for **Data Reader**.
* `scope` is a **Cosmos data-plane scope string** (`cosmosAccount.id`, or narrowed to `'${cosmosAccount.id}/dbs/<db>'` / `'${cosmosAccount.id}/dbs/<db>/colls/<container>'`), passed as a *property*, not the Bicep `scope:` keyword.
* The assignment `name` must be a GUID — so the repo's existing `guid(<scope>, <principalId>, <roleDefinitionId>)` convention (rbac.bicep line 48) transfers cleanly.

**The classic mistake to avoid:** assigning the ARM control-plane role *"Cosmos DB Built-in Data Contributor"* via `Microsoft.Authorization/roleAssignments` + `subscriptionResourceId(...)` — the pattern used everywhere else in this repo (rbac.bicep line 51, web-chat.bicep lines 78/88, mcp-container-apps.bicep line 65). That pattern **does not grant Cosmos data-plane access** and will fail silently at runtime with a 403 on the first read/write. The implementer must deviate from the repo's dominant RBAC idiom here.

**Scope constraint:** `sqlRoleAssignments` must be deployed at the **resource group containing the Cosmos account**, and the account must either be declared in the same module or pulled in with `existing`. Given main.bicep is `targetScope = 'resourceGroup'` (line 11), this is fine.

**The hard blocker — which principals?**

1. **Reviewer app identity:** trivially available *if* Option A (module in main.bicep) is chosen; requires plumbing a `principalId` parameter across deployments if Option B is chosen.
2. **"The existing agent identity" — this is ambiguous and is the biggest open risk.** The hosted agent runs under `azure.ai.agent` (azure.yaml lines 43-84); this Bicep never creates a managed identity for it. The only plausible principals are:
   * the Foundry **project** system-assigned MI — `aiFoundry.outputs.projectPrincipalId` (ai-foundry.bicep line 153), currently unused; or
   * the Foundry **account** system-assigned MI — `aiFoundry.outputs.accountPrincipalId` (line 150), currently unused.
   Both outputs already exist and are trivially wireable into a Cosmos RBAC module, so **no new plumbing is needed once the correct one is confirmed** — but which one the hosted agent runtime actually presents has not been verified anywhere in this repo. See Q1.

**Recommended shape:** a `infra/modules/cosmos-rbac.bicep` that mirrors `rbac.bicep`'s structure (param `cosmosAccountName`, param `principalIds array`, param `roleDefinitionId` defaulting to the Data Contributor GUID, `existing` account, `map`/`reduce` if multiple roles, `for` loop with `guid()` names) — so the codebase keeps one recognizable RBAC idiom even though the underlying resource type differs. Add it to `main.bicep` **unconditionally** (not `if (!empty(principalIds))`), because the existing conditional rbac module is dead code in practice (finding 4.3).

### 8.4 Conflicts and constraints summary

| # | Constraint | Evidence | Impact on new work |
| --- | --- | --- | --- |
| C1 | `environmentName` means two different things in two files | main.bicep:17 (azd base name) vs web-chat.bicep:27 (Container Apps env name) | Copying web-chat.bicep as a template for the reviewer app will import the wrong semantic. Rename to `containerAppsEnvironmentName` in any new standalone file. |
| C2 | `mcpContainerApps` outputs the env **ID**, not the **name** | mcp-container-apps.bicep:207 | A standalone reviewer template needs the *name*; add a `containerAppsEnvironmentName` output if you need it. |
| C3 | CI what-if `--parameters` is hand-maintained | deploy-and-evaluate.yml:154-157, 487-491 | Every new *required* main.bicep param breaks `bicep-validate` until the workflow is updated. Prefer params with defaults. |
| C4 | Container App images flow via `azd provision`, not `azd deploy` | main.parameters.json:17-22; workflow:209-234 | Reviewer app image needs an ACR build step + digest pinning in CI, or it stays on a placeholder forever. |
| C5 | `principalIds` is never supplied → `modules/rbac.bicep` never runs | main.bicep:44,102; main.parameters.json:4-23; workflow:154-157 | Do not model new RBAC on the conditional-module pattern. |
| C6 | No `secrets` / Key Vault convention exists | verified across all 6 .bicep files | A Cosmos connection string would be the first secret. Prefer AAD + `DefaultAzureCredential` (already the app pattern — apps/web-chat/app.py:12,46,105) and avoid introducing a secrets block. |
| C7 | Two Log Analytics workspaces already exist | monitoring.bicep:23 + mcp-container-apps.bicep:74 | Do not create a third; reuse `containerAppsEnvironment` for the reviewer app. |
| C8 | Gate banners required on every infra file | all 6 .bicep files, lines 1-9 | New files must carry the banner. |
| C9 | Cosmos account name global uniqueness, ≤44 chars, lowercase | Azure platform constraint vs. `environmentName` length | `cosmos-desjardins-quote-preparation-staging` = 43 chars. Verify. |
| C10 | Bicep `!` safe-dereference in use | mcp-container-apps.bicep:62,66,105,118,159,172 | Any new conditional resource reference must use `!`. |

---

## Evidence Index

| Topic | Primary evidence |
| --- | --- |
| Deployment scope | infra/main.bicep:11 |
| web-chat standalone | infra/web-chat.bicep:10-18; infra/main.bicep:74,83,102,111 |
| azd wiring | azure.yaml:1,11-84; infra/main.parameters.json:4-23 |
| No azd tags | absence across infra/**; only tags at infra/web-chat.bicep:95-98 |
| Naming expressions | infra/main.bicep:20,23,41,55,58,72; infra/modules/mcp-container-apps.bicep:57,71,72,100,154; infra/web-chat.bicep:68 |
| Container App (MCP) | infra/modules/mcp-container-apps.bicep:99-151, 153-205 |
| Container Apps Env | infra/modules/mcp-container-apps.bicep:74-97 |
| Container App (web-chat) | infra/web-chat.bicep:92-138 |
| Image lifecycle | infra/main.parameters.json:17-22; .github/workflows/deploy-and-evaluate.yml:209-234 |
| RBAC module | infra/modules/rbac.bicep:11-58 |
| Role GUIDs | infra/modules/rbac.bicep:27-29; infra/modules/mcp-container-apps.bicep:65; infra/web-chat.bicep:78,88 |
| Identities | infra/modules/ai-foundry.bicep:71-73,100-102; infra/modules/mcp-container-apps.bicep:56-59; infra/web-chat.bicep:67-70 |
| Monitoring | infra/modules/monitoring.bicep:23-48 |
| Telemetry wiring | infra/main.bicep:89-90,131; infra/modules/ai-foundry.bicep:58-59,109-124; azure.yaml:63-64 |
| `existing` usage | infra/modules/rbac.bicep:32; infra/modules/mcp-container-apps.bicep:52; infra/web-chat.bicep:50,54,58,62 |
| Conditionals | infra/main.bicep:102; infra/modules/mcp-container-apps.bicep:52,56,61; infra/modules/ai-foundry.bicep:161,172 |
| What-if | .github/workflows/deploy-and-evaluate.yml:121-157 |
| Provision retry (409) | .github/workflows/deploy-and-evaluate.yml:226-234 |
| Outputs | infra/main.bicep:122-133; infra/web-chat.bicep:140-141; module outputs at monitoring:43-48, ai-foundry:147-156, mcp-container-apps:207-209 |
| Current approval store | src/quote-preparation-agent/approval_repository.py:1-52 |
| No Cosmos today | file search `**/cosmos*` → 0 results |

---

## Recommended Next Research (not completed this session)

- [ ] Confirm which principal the **hosted Foundry agent** presents at runtime (project system-assigned MI vs account system-assigned MI vs a Foundry-managed identity not surfaced in Bicep) — this determines the Cosmos `sqlRoleAssignments` principal and cannot be resolved from the Bicep alone.
- [ ] Verify the exact resolved value of `environmentName` for staging and production azd environments (`vars.AZURE_ENV_NAME` / `STAGING_AZD_ENV_NAME` in GitHub repo variables) to compute the Cosmos account name length and confirm global-uniqueness headroom.
- [ ] Read `.github/workflows/deploy-and-evaluate.yml` lines 440-500 in full (the production `what-if`/`provision` block) to enumerate every place a new `main.bicep` parameter must be registered.
- [ ] Read `scripts/setup-web-chat-identity.ps1` to determine whether the reviewer app needs an equivalent Entra app registration + pilot group, and whether that script is parameterizable for a second app.
- [ ] Determine whether `azd` version in CI supports adding a Container App as an `azd` service (`host: containerapp`) — currently no compute services exist in `azure.yaml`, so the reviewer app image pipeline is unproven.
- [ ] Confirm the target Cosmos consistency level, partition key, and TTL requirements for the approval-case container from the `approval_repository.py` state-machine semantics (revision-invalidation, optimistic concurrency).

## Clarifying Questions

1. **Which identity is "the existing agent identity"?** The Bicep creates system-assigned MIs on both the Foundry account and project, and neither output is consumed today. The hosted agent is deployed by `azd` via `host: azure.ai.agent`, not by Bicep. Confirm the principal ID to grant Cosmos data-plane access to — this is the single highest-risk unknown.
2. **Should the reviewer app be a module in `main.bicep` (Option A) or a standalone template like `web-chat.bicep` (Option B)?** Option A is required for clean in-template Cosmos RBAC; Option B matches the existing precedent for web UIs but splits the identity across deployments.
3. **Is the AUTHOR-ONLY / G2-G3-G6 gate still binding?** The templates all say "never deployed", but `.github/workflows/deploy-and-evaluate.yml` runs real `azd provision`/`azd deploy` against staging and production. The implementer needs to know whether new resources are author-only or will actually deploy.
4. **Cosmos auth posture:** `disableLocalAuth: true` (AAD-only, matching the app's existing `DefaultAzureCredential` pattern) or leave local auth enabled? The repo has no secrets/Key Vault convention, which argues strongly for AAD-only — but this diverges from the Foundry account's explicit `disableLocalAuth: false`.
5. **Does the reviewer app replace or coexist with the SQLite `ApprovalRepository`?** A Cosmos-backed store changes `src/quote-preparation-agent/approval_repository.py`'s concurrency model (lock + `WHERE state=... AND revision=...` → ETag/`If-Match`). Is the SQLite path retained for local/offline workshop use?
6. **Should Cosmos RBAC scope be account-wide, database-wide, or container-wide?** Container-scoped is least-privilege but requires the RBAC module to depend on the container resource.
