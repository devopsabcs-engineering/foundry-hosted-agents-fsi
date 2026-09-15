<!-- markdownlint-disable-file -->
# Private Networking Research: ACA VNet + Cosmos Private Endpoint + Foundry Agent Network Injection

Research date: 2026-09-15
Region under evaluation: `eastus2`
Scope: Reaching a Cosmos DB account with `publicNetworkAccess: Disabled` (forced by tenant-root Azure Policy `modify` effect) from (1) Azure Container Apps workloads and (2) an Azure AI Foundry hosted agent.

## Legend

- **[VERIFIED]** — stated explicitly in a cited Microsoft Learn page or ARM schema reference.
- **[INFERRED]** — a reasonable conclusion drawn from verified facts, but not stated verbatim anywhere found.
- **[UNVERIFIED]** — could not be confirmed from authoritative sources; must be tested before relying on it.

## Executive Answers to the Two Critical Questions

| Question | Answer | Confidence |
| --- | --- | --- |
| Q12: Can network injection be added to an EXISTING Foundry account/project? | **NO for hosted agents.** The Foundry account must be recreated. | [VERIFIED] |
| Q13: Can a network-injected agent reach our own Cosmos private endpoint in the same VNet? | **YES**, this is the documented purpose of subnet integration, provided private DNS zones are linked to the VNet and RBAC is in place. | [VERIFIED] for the general mechanism; [INFERRED] for an arbitrary (non-BYO-dependency) Cosmos account. |

---

## A. Azure Container Apps VNet Integration

### A.1 Bicep shape for `Microsoft.App/managedEnvironments` with VNet integration

**[VERIFIED]** Source: <https://learn.microsoft.com/en-us/azure/templates/microsoft.app/managedenvironments>

`properties.vnetConfiguration` object (type `VnetConfiguration`) fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `infrastructureSubnetId` | string | Resource ID of the subnet for infrastructure components. Must not overlap with any other provided IP range. |
| `internal` | bool | `true` = environment only has an internal load balancer; no public static IP resource. **Requires `infrastructureSubnetId` when `true`.** |
| `dockerBridgeCidr` | string | CIDR for the Docker bridge network. Size between `/28` and `/12`. |
| `platformReservedCidr` | string | CIDR reserved for environment infrastructure IPs. Size between `/23` and `/12`. |
| `platformReservedDnsIP` | string | IP from `platformReservedCidr` reserved for the internal DNS server. Cannot be the network address or the first usable address. |

**[VERIFIED]** `dockerBridgeCidr` / `platformReservedCidr` / `platformReservedDnsIP` apply only to the **legacy Consumption-only** environment type. The default workload-profiles environment type does not require them. Source: <https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom> ("These parameters are only applicable to the legacy Consumption-only environment type. The default workload profiles environment type doesn't require these parameters.")

**[VERIFIED]** You must either provide values for all three of those properties or none of them; if omitted they are generated automatically. Source: same page.

Minimal workload-profiles VNet-integrated environment:

```bicep
// API version: 2025-07-01 (stable). Latest available is 2026-01-01.
resource env 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnet.id
      internal: false   // true => internal-only ILB, no public ingress
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}
```

**[VERIFIED]** `properties.publicNetworkAccess` (`'Enabled'` | `'Disabled'`) is a separate top-level property from `vnetConfiguration`. Source: ARM schema reference above.

**[VERIFIED]** `internal` and `publicNetworkAccess` interact as follows. Source: <https://learn.microsoft.com/en-us/azure/container-apps/networking>

| Virtual IP | Supported `publicNetworkAccess` | Notes |
| --- | --- | --- |
| External (`internal: false`) | `Enabled`, `Disabled` | Can be changed after environment creation. |
| Internal (`internal: true`) | `Disabled` only | Cannot be changed to accept internet traffic. |

**[VERIFIED]** To create private endpoints *into* your Container Apps environment, `publicNetworkAccess` must be `Disabled`. Source: same page.

### A.2 Minimum subnet size and required delegation

**[VERIFIED]** Source: <https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks> and <https://learn.microsoft.com/en-us/azure/container-apps/networking>

| Environment type | Minimum subnet size | Delegation |
| --- | --- | --- |
| **Workload profiles** (default) | `/27` | **Required**: delegate the subnet to `Microsoft.App/environments` |
| **Consumption-only** (legacy) | `/23` | **Must NOT be delegated to any service**, including `Microsoft.App/environments` |

Exact delegation service name: **`Microsoft.App/environments`**.

**[VERIFIED]** CLI form: `az network vnet subnet update --delegations Microsoft.App/environments`. Source: <https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom>

**[VERIFIED]** Workload-profiles IP accounting: Container Apps reserves 12 IP addresses for subnet integration; the published capacity table subtracts 14 (12 platform + reserved). Source: custom-virtual-networks.

| Subnet size | Available IPs | Max nodes (Dedicated) | Max replicas (Consumption profile) |
| --- | --- | --- | --- |
| `/23` | 498 | 249 | 2,490 |
| `/24` | 242 | 121 | 1,210 |
| `/25` | 114 | 57 | 570 |
| `/26` | 50 | 25 | 250 |
| `/27` | 18 | 9 | 90 |

**[VERIFIED]** Reserved ranges that the subnet must not overlap (AKS-reserved): `169.254.0.0/16`, `172.30.0.0/16`, `172.31.0.0/16`, `192.0.2.0/24`. A workload-profile environment additionally reserves `100.100.0.0/17`, `100.100.128.0/19`, `100.100.160.0/19`, `100.100.192.0/19`. Source: custom-virtual-networks.

Bicep for the subnet with the delegation:

```bicep
// API version: 2024-05-01
resource acaSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-aca'
  properties: {
    addressPrefix: '10.20.0.0/23'
    delegations: [
      {
        name: 'aca-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}
```

### A.3 Can VNet configuration be added to an EXISTING managed environment?

**NO — the environment must be recreated.** **[VERIFIED]**

> "By default, Container Apps is integrated with the Azure network, which is publicly accessible over the internet... You also have the option to provide an existing virtual network as you create your environment instead. **After you create an environment with either the default Azure network or an existing virtual network, you can't change the network type.**"

Source: <https://learn.microsoft.com/en-us/azure/container-apps/networking> (section "Virtual network type")

**[VERIFIED]** Additionally, subnet size is immutable: "Select your subnet size carefully. You can't modify subnet sizes after you create a Container Apps environment." Source: <https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks>

**[INFERRED]** Both existing managed environments in this workspace (`vnetConfiguration: null`) must be deleted and recreated with `vnetConfiguration` populated. The container apps within them must be redeployed, and their ingress FQDNs will change because the environment `defaultDomain` and `staticIp` are regenerated.

### A.4 API version for workload profiles

**[VERIFIED]** Available API versions for `Microsoft.App/managedEnvironments` include (newest first): `2026-01-01`, `2025-10-02-preview`, `2025-07-01`, `2025-02-02-preview`, `2025-01-01`, `2024-10-02-preview`, `2024-08-02-preview`, `2024-03-01`, `2024-02-02-preview`, `2023-11-02-preview`, `2023-08-01-preview`, `2023-05-02-preview`, `2023-05-01`, `2023-04-01-preview`, `2022-11-01-preview`, `2022-10-01`, `2022-06-01-preview`, `2022-03-01`, `2022-01-01-preview`. Source: <https://learn.microsoft.com/en-us/azure/templates/microsoft.app/managedenvironments>

**[VERIFIED]** The `workloadProfiles` array is present in the current (`2026-01-01`) schema with required members `name` and `workloadProfileType`, plus optional `minimumCount` / `maximumCount`.

**Recommendation [INFERRED]**: use **`2025-07-01`** or **`2026-01-01`** (both stable/GA). Avoid preview API versions for a workshop. `2023-05-01` is the earliest stable version that carries workload profiles, but newer stable versions add `ingressConfiguration`, `publicNetworkAccess`, and `peerTrafficConfiguration`.

### A.5 Does the ACA environment actually need VNet integration to reach the Cosmos private endpoint?

**[INFERRED — high confidence]** Yes. A non-VNet-integrated Container Apps environment egresses over the public Azure network. It has no route into a customer VNet and no visibility of the private DNS zone, so a Cosmos account with `publicNetworkAccess: Disabled` is unreachable.

Supporting **[VERIFIED]** statement: "Use an existing virtual network when you need Azure networking features like... **Access to resources behind private endpoints in your virtual network.**" Source: <https://learn.microsoft.com/en-us/azure/container-apps/networking>

---

## B. Cosmos DB Private Endpoint

### B.1 Private endpoint Bicep and `groupIds`

**[VERIFIED]** For the Cosmos DB **NoSQL (SQL) API**, the private-link sub-resource / group ID is **`Sql`** (capital S, lowercase "ql"). Source: <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints>

Full mapping table **[VERIFIED]** (same page):

| Cosmos account API type | Group ID | Private DNS zone |
| --- | --- | --- |
| NoSQL | `Sql` | `privatelink.documents.azure.com` |
| NoSQL (dedicated gateway) | `SqlDedicated` | `privatelink.sqlx.cosmos.azure.com` |
| Cassandra | `Cassandra` | `privatelink.cassandra.cosmos.azure.com` |
| Mongo | `MongoDB` | `privatelink.mongo.cosmos.azure.com` |
| Gremlin | `Gremlin` | `privatelink.gremlin.cosmos.azure.com` |
| Gremlin (via NoSQL) | `Sql` | `privatelink.documents.azure.com` |
| Table | `Table` | `privatelink.table.cosmos.azure.com` |
| Table (via NoSQL) | `Sql` | `privatelink.documents.azure.com` |

```bicep
// API version: 2024-05-01 (Microsoft.Network). Learn's sample still uses 2019-04-01;
// 2024-05-01 is current stable and schema-compatible for this shape.
resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${cosmosAccountName}'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos-sql-connection'
        properties: {
          privateLinkServiceId: cosmosAccount.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}
```

**[VERIFIED]** Multiple private IPs are allocated per private endpoint: one for the global region-agnostic endpoint, plus one per region the Cosmos account is deployed in. Source: same page.

### B.2 Private DNS zone, VNet link, and DNS zone group

**[VERIFIED]** Zone name for Cosmos SQL API: **`privatelink.documents.azure.com`**. Public forwarder: `documents.azure.com`. Sources: Cosmos private endpoints page and <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks> ("DNS zone configurations summary" table).

```bicep
// API version: 2024-06-01 (Microsoft.Network/privateDnsZones)
resource cosmosDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource cosmosDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cosmosDnsZone
  name: '${vnet.name}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// API version: 2024-05-01 (sub-resource of the private endpoint)
resource cosmosDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: cosmosPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-documents-azure-com'
        properties: {
          privateDnsZoneId: cosmosDnsZone.id
        }
      }
    ]
  }
}
```

**[VERIFIED]** Using a `privateDnsZoneGroups` sub-resource is strongly recommended: "If you use a private DNS zone group, the private DNS zone is automatically updated when the private endpoint is updated... after adding a new region, the private DNS zone is automatically updated." Without it, adding or removing a Cosmos region requires manual DNS record maintenance, and stale records cause data-plane outages. Source: Cosmos private endpoints page, sections "Update a private endpoint when you add or remove a region" and "Limitations to private DNS zone integration".

**[VERIFIED]** `registrationEnabled: false` is the documented value for the VNet link on a `privatelink.*` zone (`--registration-enabled false` in the CLI sample). Source: same page.

**[VERIFIED]** Private Link does **not** prevent the public Cosmos DNS name from being resolvable publicly: "Private Link doesn't prevent your Azure Cosmos DB endpoints from being resolved by public DNS. Filtering of incoming requests happens at application level, not at transport or network level." The private DNS zone is what causes in-VNet resolution to return the private IP. Source: same page.

### B.3 `privateEndpointNetworkPolicies` requirement

**[VERIFIED]** **No action is required by default.** Current guidance: "By default, network policies are **disabled** for a subnet in a virtual network. To use network policies like user-defined routes and network security group support, network policy support must be **enabled** for the subnet." Source: <https://learn.microsoft.com/en-us/azure/private-link/disable-private-endpoint-network-policy>

Allowed values for `privateEndpointNetworkPolicies`: `Disabled`, `NetworkSecurityGroupEnabled`, `RouteTableEnabled`, `Enabled`. Source: same page.

**[VERIFIED — but stale]** The Cosmos DB private-endpoints article still contains legacy steps such as `az network vnet subnet update --disable-private-endpoint-network-policies true` and `PrivateEndpointNetworkPolicies = "Disabled"`. These are no-ops against the current default and are safe but unnecessary. Source: <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints>

**[INFERRED]** Explicitly setting `privateEndpointNetworkPolicies: 'Disabled'` on the private-endpoint subnet in Bicep is harmless and makes intent explicit. Only set it to `Enabled` / `NetworkSecurityGroupEnabled` / `RouteTableEnabled` if you intend to apply NSGs or UDRs to private-endpoint traffic (for example, forcing PE traffic through a firewall).

```bicep
resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-pe'
  properties: {
    addressPrefix: '10.20.4.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
}
```

### B.4 Control plane vs data plane with `publicNetworkAccess: Disabled`

**[VERIFIED]** The `publicNetworkAccess: Disabled` flag is described purely in terms of *traffic* to the account: "All public and virtual network **traffic** is blocked when the flag is set to `Disabled`, even if the source IP or virtual network is allowed in the firewall configuration." It "takes precedence over any IP or virtual network rule." Source: <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints> (section "Blocking public network access during account creation")

**[VERIFIED]** The same article documents setting `publicNetworkAccess` to `Disabled` **during ARM account creation**, and separately documents adding private endpoints to an existing account via ARM/PowerShell/CLI — all of which are ARM control-plane operations executed from outside the VNet. Source: same page.

**[VERIFIED]** Firewall/ACL rejections are explicitly described as application-layer `403 Forbidden` responses to *data* requests, not connection-layer blocks: "When IP firewall or virtual network access rules are added, only requests from allowed sources get valid responses. Other requests are rejected with a 403 (Forbidden)." Source: <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-vnet-service-endpoint>

**Conclusion [INFERRED — high confidence]:**

| Operation | Plane | Works with `publicNetworkAccess: Disabled` and no private path? |
| --- | --- | --- |
| `az deployment group create` / Bicep deploying `Microsoft.DocumentDB/databaseAccounts` | Control | **Yes** |
| Creating `sqlDatabases` / `containers` via ARM/Bicep | Control | **Yes** |
| Creating `sqlRoleAssignments` (data-plane RBAC grants) via ARM | Control | **Yes** |
| `az cosmosdb show` | Control | **Yes** |
| `CosmosClient` document read/write/query (`azure-cosmos` SDK) | Data | **No** — requires the private endpoint path |
| Portal Data Explorer document browsing | Data | **No** |
| Seed scripts (`scripts/seed_review_queue.py`) | Data | **No** |

**[UNVERIFIED]** No Microsoft Learn page found that states verbatim "control plane operations are unaffected by publicNetworkAccess". The conclusion is drawn from the consistent framing across the cited pages plus the fact that the tenant-root policy with a `modify` effect is itself successfully performing control-plane writes on the account. **Recommend empirical confirmation** with a no-op Bicep redeploy before committing to the design.

**[VERIFIED — operational caveat]** Adding a private endpoint to an existing Cosmos account causes roughly five minutes of downtime unless you pre-stage firewall rules:

1. Add IP or VNet rules explicitly allowing your client connections.
2. Wait 10 minutes for the configuration to propagate.
3. Configure the private endpoint.
4. Remove the firewall rules from step 1.

Source: <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints> (section "Add private endpoints to an existing Azure Cosmos DB account with no downtime")

**[VERIFIED]** When using Private Link with Cosmos in **direct mode**, the full TCP port range `0–65535` must be open. Source: same page. **[INFERRED]** If NSGs are applied to the ACA or agent subnets, gateway mode (HTTPS/443 only) is far simpler to secure; the Python `azure-cosmos` SDK defaults to gateway mode.

**[VERIFIED]** Limit: maximum 200 private endpoints per Cosmos account. Rejected private endpoint connections cannot be re-approved — the endpoint must be recreated. Source: same page.

---

## C. Azure AI Foundry Agent Service Network Injection

Primary source for this section: <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks>
Secondary: <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/standard-agent-setup>, <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/limits-quotas-regions>

### C.9 Current supported mechanism for agent egress into a customer VNet

**[VERIFIED]** The supported feature is **"Standard Setup with private networking"**, implemented through **network injection** — the `properties.networkInjections` array on `Microsoft.CognitiveServices/accounts`.

Documented guarantees of the feature:

> - **No public egress**: Foundational infrastructure provides the right authentication and security for your agents and tools, without requiring trusted service bypass.
> - **Subnet integration**: You provide a delegated subnet from your virtual network. The platform connects agent compute to this subnet, enabling local communication with your Azure resources within the same virtual network.
> - **Private resource access**: If your resources are marked as private and nondiscoverable from the internet, the platform network can still access them when the necessary credentials and authorization are in place.

Source: virtual-networks page, introduction.

**[VERIFIED]** Portal flow confirms the shape: after configuring an inbound private endpoint to the Foundry account, "a new dropdown appears for setting **Virtual network injection**. Select your **virtual network** in the first dropdown, then select your **subnet** that is delegated to `Microsoft.App/environments` with a subnet size of /27 or larger."

**[VERIFIED]** Required resource providers must be registered: `Microsoft.KeyVault`, `Microsoft.CognitiveServices`, `Microsoft.Storage`, `Microsoft.MachineLearningServices`, `Microsoft.Search`, `Microsoft.Network`, `Microsoft.App`, `Microsoft.ContainerService` (plus `Microsoft.Bing` only for the Bing Search tool). Source: virtual-networks page, Prerequisites.

### C.10 Exact Bicep shape, delegation, subnet size, API version

**[VERIFIED]** Schema of the `NetworkInjection` object. Source: <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts>

| Field | Type | Description (verbatim from schema) |
| --- | --- | --- |
| `scenario` | `'agent'` \| `'none'` | "Specifies what features in AI Foundry network injection applies to. Currently only supports 'agent' for agent scenarios. 'none' means no network injection." |
| `subnetArmId` | string | "Specify the subnet for which your Agent Client is injected into." |
| `useMicrosoftManagedNetwork` | bool | "Boolean to enable Microsoft Managed Network for subnet delegation" |

**API version support [VERIFIED]:** `networkInjections` is present in the **stable** API version **`2025-06-01`**, and also in `2025-04-01-preview`, `2025-09-01`, `2025-12-01`, `2026-03-01`, `2026-05-01`, and `2026-05-15-preview`. It is **not** present in `2024-10-01` or earlier. Sources:

- <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/2025-06-01/accounts>
- <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/2025-04-01-preview/accounts>

**Recommendation [INFERRED]:** use **`2025-06-01`** (earliest stable version carrying `networkInjections`) or a newer stable version such as `2026-05-01`.

```bicep
// API version: 2025-06-01 (stable; earliest stable version supporting networkInjections)
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryAccountName
  location: location            // MUST equal the VNet region
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${foundryUami.id}': {}
    }
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryAccountName
    publicNetworkAccess: 'Disabled'      // see note in C.13 — this is a SEPARATE knob from injection
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    networkInjections: [
      {
        scenario: 'agent'
        subnetArmId: agentSubnet.id
        useMicrosoftManagedNetwork: false
      }
    ]
  }
}
```

**Agent subnet delegation [VERIFIED]:** the delegation service name is **`Microsoft.App/environments`** — the same delegation used by Container Apps. Confirmed twice:

1. Portal instructions: "select your **subnet** that is delegated to `Microsoft.App/environments`".
2. Troubleshooting error text: `"Subnet requires any of the following delegation(s) [Microsoft.App/environments] to reference service association link ...serviceAssociationLinks/legionservicelink."`

**Agent subnet size [VERIFIED]:**

- Portal minimum: **`/27` or larger**.
- Documented recommendation: **`/24` (256 addresses)** — "The recommended size of the delegated Agent subnet is /24 (256 addresses) due to the delegation of the subnet to `Microsoft.App/environments`."
- Reference deployment uses Agent Subnet `192.168.0.0/24` and Private Endpoint Subnet `192.168.1.0/24` inside a `192.168.0.0/16` VNet.

**Agent subnet address-space restrictions [VERIFIED]:**

- Must be RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) **or** RFC 6598 CGNAT (`100.64.0.0/10`, excluding `100.100.0.0/17`, `100.100.192.0/19`, `100.100.224.0/19`).
- **Public IP ranges such as `44.x.x.x` are rejected.**
- Neither the VNet nor any peered VNet may overlap `169.254.0.0/16`, `172.30.0.0/16`, `172.31.0.0/16`, `192.0.2.0/24`, `0.0.0.0/8`, `127.0.0.0/8`, `100.100.0.0/17`, `100.100.192.0/19`, `100.100.224.0/19`.
- Error signature when violated: `"Provided subnet must be of the proper address space. Please provide a subnet which has address space in the range of 172 or 192."`

**Agent subnet exclusivity [VERIFIED]:** "The agent subnet can't be shared by multiple Foundry resources. Each Foundry resource must use a dedicated agent subnet." Multiple Foundry resources may share the same **VNet** but not the same **subnet**.

```bicep
resource agentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-agent'
  properties: {
    addressPrefix: '10.20.2.0/24'   // /24 recommended; /27 is the hard minimum
    delegations: [
      {
        name: 'agent-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}
```

### C.11 Bring-your-own dependent resources and required role assignments

**[VERIFIED] All three BYO resources are MANDATORY** for a network-injected (standard) agent:

> "Standard setups require you to Bring Your Own (BYO) resources so that all agent data stays in your Azure tenant. BYO resources include: **Azure Storage, Azure AI Search, and Azure Cosmos DB**."

And explicitly for VNet injection: "If you're using virtual network injection, you must bring your own Storage, Azure AI Search, and Azure Cosmos DB resources to create a Standard Agent with end-to-end virtual network isolation."

**[VERIFIED]** Attempting to omit any one of them produces deployment failures:

- `"Agents CapabilityHost supports a single, non empty value for vectorStoreConnections property."`
- `"Agents CapabilityHost supports a single, non empty value for storageConnections property."`
- `"Agents CapabilityHost supports a single, non empty value for threadStorageConnections property."`

> "Providing all connections to all Bring-your-Own (BYO) resources, requires connections to all BYO resources. You can't create a secured standard agent in Foundry without all three resources provided."

**[VERIFIED]** Azure Key Vault is also listed in the prerequisites for standard agent setup ("used for managing secrets and connection strings for the agent infrastructure"). Source: <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/standard-agent-setup>

| BYO resource | Stores |
| --- | --- |
| Azure Storage | Files uploaded by developers and end users |
| Azure AI Search | Vector stores created by the agent |
| Azure Cosmos DB | Messages, conversation history, agent metadata |

**[VERIFIED] Cosmos DB throughput requirement:** the Cosmos for NoSQL account must have a total throughput limit of **at least 3000 RU/s**. Both Provisioned Throughput and Serverless are supported. Standard setup provisions **five containers**, each requiring 1000 RU/s:

| Container | Purpose | Runtime |
| --- | --- | --- |
| `thread-message-store` | End-user conversations | Classic |
| `system-thread-message-store` | Internal system messages | Classic |
| `agent-entity-store` | Agent metadata | Classic |
| `agent-definitions-v1` | Agent metadata incl. versions | New |
| `run-state-v1` | Internal messages and conversations | New |

> "Insufficient RU/s capacity in the Cosmos DB account results in capability host provisioning failures during deployment."

These containers live in a database named **`enterprise_memory`**.

**[VERIFIED] Required role assignments** (source: standard-agent-setup, Phases 3 and 5):

Phase 3 — project **system-assigned** managed identity, before capability host creation:

| Role | Scope |
| --- | --- |
| **Cosmos DB Operator** | Cosmos DB account |
| **Storage Account Contributor** | Storage account |

Phase 5 — project managed identity (**both SMI and UMI**), granular:

| Role | Scope |
| --- | --- |
| **Search Index Data Contributor** | Azure AI Search service |
| **Search Service Contributor** | Azure AI Search service |
| **Storage Blob Data Contributor** | Blob container `<workspaceId>-azureml-blobstore` |
| **Storage Blob Data Owner** | Blob container `<workspaceId>-azureml-agent` |
| **Cosmos DB Built-in Data Contributor** | Cosmos **database** `enterprise_memory` (database-level scope covers all containers; no per-container assignment needed) |

Phase 6 — developers: **Foundry User** role at project scope. Minimum permission set: `agents/*/read`, `agents/*/action`, `agents/*/delete`.

**[VERIFIED]** The deploying principal needs **Foundry Account Owner** at subscription scope plus **Role Based Access Administrator** (or **Owner**), because `Microsoft.Authorization/roleAssignments/write` is required.

**[VERIFIED]** For network-injected template deployments, two extra assignments are called out post-deployment:

- **Managed Identity Operator** on the user-assigned managed identity.
- **Network Contributor** on the remote VNet (for cross-tenant scenarios).

**[VERIFIED — critical]** "Private endpoints to Azure AI Search, Azure Storage, and Azure Cosmos DB are **NOT auto-created** when you deploy your Foundry resource. Please ensure to create private endpoints to these resources separately."

**[VERIFIED] DNS zones required** (source: virtual-networks, "DNS zone configurations summary"):

| Private link resource | Sub-resource | Private DNS zone |
| --- | --- | --- |
| Foundry | `account` | `privatelink.cognitiveservices.azure.com`, `privatelink.openai.azure.com`, `privatelink.services.ai.azure.com` |
| Azure AI Search | `searchService` | `privatelink.search.windows.net` |
| Azure Cosmos DB | `Sql` | `privatelink.documents.azure.com` |
| Azure Storage | `blob` | `privatelink.blob.core.windows.net` |

Azure DNS virtual server IP for conditional forwarders: **`168.63.129.16`**.

### C.12 CRITICAL: Can network injection be added to an EXISTING Foundry account/project?

**NO for hosted agents. The account must be recreated.** **[VERIFIED]**

Direct quote from the Limitations section of <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks>:

> **"Hosted agent virtual network injection**: For Hosted agents, the virtual network configuration (network injection) must be included when you first create the Foundry account. Adding network injection to an existing Foundry account after creation isn't supported for Hosted agents."

**[VERIFIED]** A second, independent immutability constraint compounds this — **capability hosts cannot be updated after creation**:

> "You can't update the capability host after it's set for a project or account."

And in the troubleshooting table:

> "Update request to capability host returns `400 BadRequest` — Update not supported — **Capability hosts can't be updated after creation. Delete and recreate the project if configuration changes are needed.**"

Sources: <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/standard-agent-setup> (sections "Capability hosts → Limitations" and "Troubleshoot common issues")

**[VERIFIED] Deletion ordering trap:** "If you want to delete your Foundry resource and Standard Agent with secured network setup, delete your Foundry resource and virtual network **last**. Before deleting the virtual network, delete and **purge** your Foundry resource."

Failure signature if you get the order wrong **[VERIFIED]**:

> `"Subnet requires any of the following delegation(s) [Microsoft.App/environments] to reference service association link /subscriptions/.../serviceAssociationLinks/legionservicelink."`

Remedy: Azure portal → Foundry resource → **Manage deleted resources** → purge; or run the `deleteCaphost.sh` script from the secured-standard template.

**[INFERRED] Practical impact on this workspace:** the existing Foundry account, project, capability hosts, model deployments, connections, and the deployed hosted agent must all be torn down and rebuilt. The Foundry project endpoint (`FOUNDRY_PROJECT_ENDPOINT`) and agent IDs will change, invalidating any hardcoded values in `infra/`, `azure.yaml`, CI variables, and lab documentation.

### C.13 CRITICAL: Can a network-injected agent reach OUR OWN Cosmos private endpoint?

**YES — this is precisely the stated purpose of the feature.** **[VERIFIED for the mechanism]**

Two verbatim statements from <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks>:

> **"Subnet integration**: You provide a delegated subnet from your virtual network. The platform connects agent compute to this subnet, **enabling local communication with your Azure resources within the same virtual network.**"

> **"Private resource access**: If your resources are marked as private and nondiscoverable from the internet, **the platform network can still access them when the necessary credentials and authorization are in place.**"

Supporting evidence that private Cosmos connectivity from agent compute is a first-class, exercised path **[VERIFIED]** — from the troubleshooting guide:

> `"Timeout of 60000ms exceeded"` error when loading the Agent pages in the Foundry project
> **Solution**: The Foundry project has issues communicating with Azure Cosmos DB to create Agents. **Verify connectivity to Azure Cosmos DB (Private Endpoint and DNS).**

And from the verification steps:

> "Validate private endpoint DNS resolution: From a machine connected to the VNet, run `nslookup` against each endpoint listed in the DNS zone configurations summary."

**What is explicitly VERIFIED:**

1. Agent compute is injected into your delegated subnet in your VNet.
2. Agent compute can reach Azure resources in that same VNet.
3. Agent compute can reach resources that are private and non-discoverable from the internet, given credentials and authorization.
4. Agent compute reaching **Cosmos DB over a private endpoint** is the normal, documented operating mode for the BYO thread store, and is a diagnosed failure mode when DNS/PE is misconfigured.

**What is [INFERRED] rather than stated verbatim:** the docs frame private Cosmos access in terms of the **BYO dependency** Cosmos account (thread storage). They do not contain a sentence of the form "your agent's own Python code can call an arbitrary third Cosmos account over a private endpoint." However, the network path is identical: agent compute has a NIC in your delegated subnet, so any private endpoint in that VNet (or a peered VNet with correctly linked private DNS zones) is routable and resolvable. There is no documented per-destination allowlist for agent egress within the VNet.

**Prerequisites for this to actually work [VERIFIED, assembled from the same page]:**

| Requirement | Detail |
| --- | --- |
| Private endpoint exists | For the Cosmos account, `groupIds: ['Sql']`, placed in a subnet in the same VNet (or a peered VNet). |
| Private DNS zone linked | `privatelink.documents.azure.com` must have a virtual network link to the **VNet containing the agent subnet**. Without the link, the agent resolves the public IP and fails. |
| DNS zone group on the PE | Keeps records current as Cosmos regions change. |
| RBAC | The agent's managed identity needs Cosmos **data-plane** RBAC (`Cosmos DB Built-in Data Contributor` or `Data Reader`) scoped appropriately — control-plane roles like `Cosmos DB Operator` do **not** grant document access. |
| No blocking NSG/firewall | If an NSG or Azure Firewall is applied to the agent subnet, outbound to the PE subnet must be permitted. |

**[VERIFIED] Firewall/NSG caveat on the agent subnet:**

> "If you integrate an Azure Firewall with your private network secured standard agent, add to the allow list the FQDNs listed under **Managed Identity** in the Integrate with Azure Firewall article, or add the Service Tag **AzureActiveDirectory**. If you apply Network Security Groups (NSGs) to the delegated agent subnet or related subnets, configure matching outbound allow rules for required dependencies, including the AzureActiveDirectory service tag for Microsoft Entra ID authentication. **If either firewall or NSG rules block required dependencies, agent provisioning and runtime operations can fail.** Verify that no TLS inspection happens in the Firewall that could add a self-signed certificate."

**[VERIFIED] Peered VNets are supported:** "Peered virtual networks are supported, but data transfer costs can increase." The Cosmos account, Search, and Storage may live in different regions from the Foundry account (with cost implications) — only the **VNet** must be co-regional with the Foundry account.

**[UNVERIFIED — recommend testing]** Whether `publicNetworkAccess: 'Enabled'` on the Foundry account is compatible with `networkInjections` being set. The ARM schema treats them as independent properties, and the portal flow happens to set both together. If they are independent, a hybrid posture is possible: agent **egress** injected into the VNet (reaching the private Cosmos) while the Foundry account **inbound** endpoint stays public, so `azd`, portal, and public CI runners keep working. This would dramatically reduce workshop complexity. **This is the single highest-value thing to validate experimentally.**

### C.14 Region availability — is eastus2 supported?

**[VERIFIED] Yes.** `East US 2` shows **Yes** in all three columns of the support matrix: Responses API, Agents, and **Private VNet**. Source: <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/limits-quotas-regions>

**[VERIFIED] Same-region constraint:** "**The Foundry resource must be deployed in the same region as the virtual network (VNet)**. Other Azure resources, such as Azure Cosmos DB, Azure AI Search, and Azure Storage, can be deployed in different regions. Consider the cost implications of cross-region deployments."

**[VERIFIED] Class A address space:** "Every region where Agent Service is available supports private Class A address space (`10.0.0.0/8`)." So a `10.x.x.x` VNet is valid in `eastus2`.

**[VERIFIED] Session quota:** `East US 2` is in the higher tier — **2,000** concurrent hosted agent sessions per subscription per region (vs 1,000 elsewhere).

**[VERIFIED] Tool availability in East US 2** — all listed tools show `yes`, including Azure AI Search, Code Interpreter, Computer Use, File Search, Function, MCP, OpenAPI, SharePoint, Web Search, and Grounding with Bing Search. East US 2 is also in the Bing-grounding supported region list.

**[VERIFIED] Foundry resource / VNet resource group:** "No. The virtual network and Foundry resource don't need to be in the same resource group, but they must be in the same region."

---

## D. Risks, Limitations, and Preview Status

### D.15 Known limitations and gotchas for the combined design

#### D.15.1 Blocking / recreate-required items

| # | Item | Impact | Source |
| --- | --- | --- | --- |
| 1 | **Foundry account cannot gain network injection after creation (hosted agents)** | Account + project + capability hosts + model deployments + connections + agent must be recreated. Endpoint and agent IDs change. | [VERIFIED] virtual-networks, Limitations |
| 2 | **Capability hosts are immutable** | Any later change to storage/search/thread connections requires deleting and recreating the project. | [VERIFIED] standard-agent-setup |
| 3 | **Container Apps environment network type cannot be changed** | Both managed environments must be deleted and recreated; ingress FQDNs and static IPs change. | [VERIFIED] container-apps/networking |
| 4 | **ACA subnet size is immutable** | Size the subnet correctly on the first attempt. | [VERIFIED] custom-virtual-networks |
| 5 | **All three BYO resources are mandatory** | Must stand up Azure AI Search and a Storage account even if the workshop does not otherwise use them. Adds cost and surface area. | [VERIFIED] virtual-networks / standard-agent-setup |
| 6 | **Cosmos must have ≥3000 RU/s** | Capability host provisioning fails otherwise. Multiply by project count. | [VERIFIED] standard-agent-setup |
| 7 | **Private endpoints for Search/Storage/Cosmos are NOT auto-created** | Must be authored explicitly in Bicep, each with its own DNS zone and zone group. | [VERIFIED] virtual-networks |

#### D.15.2 Operational and deployment-pipeline risks

| # | Item | Detail | Source |
| --- | --- | --- | --- |
| 8 | **Cannot deploy from a public workstation once Foundry public access is disabled** | "After you disable public network access, you can't run `azd up` or `azd deploy` from a public-internet workstation. The ARM control plane is reachable, but data-plane calls to Foundry and ACR push fail with `403` or connection-refused errors." Requires a self-hosted GitHub Actions runner / Azure DevOps agent in the VNet, or Bastion + jump host. | [VERIFIED] virtual-networks (azd pivot) |
| 9 | **Local development requires VPN / Bastion / ExpressRoute** | `azd ai agent run` and `invoke` need DNS resolution of the private Foundry endpoint. | [VERIFIED] same |
| 10 | **DNS is the most common failure mode** | "Confirm private DNS resolution end to end, for example with `nslookup <endpoint>` from the runner or development VM, before you assume the issue is RBAC." | [VERIFIED] same |
| 11 | **Cosmos PE on an existing account causes ~5 min downtime** | Unless the documented 4-step pre-staging procedure is followed. | [VERIFIED] cosmos how-to-configure-private-endpoints |
| 12 | **Deletion order trap** | Purge the Foundry resource before deleting the VNet, or the agent subnet is left with an orphaned service association link (`legionservicelink`) and cannot be deleted. | [VERIFIED] virtual-networks |
| 13 | **Agent subnet exhaustion** | HTTP 429 `subnet_exhausted` when the delegated subnet runs out of IPs. Remedy is a larger subnet — which, per item 4's analogue, means recreation. | [VERIFIED] limits-quotas-regions |
| 14 | **Agent subnet is single-tenant per Foundry resource** | Cannot share one agent subnet across multiple Foundry accounts — a problem for multi-attendee workshop deployments in one VNet. | [VERIFIED] virtual-networks |
| 15 | **Cosmos direct mode needs ports 0–65535** | If NSGs are applied, prefer gateway mode (443) for the `azure-cosmos` SDK. | [VERIFIED] cosmos how-to-configure-private-endpoints |
| 16 | **NSG/Firewall on agent subnet can break provisioning** | Must allow `AzureActiveDirectory` service tag; no TLS inspection with self-signed certs. | [VERIFIED] virtual-networks |

#### D.15.3 Feature limitations that affect the workshop content

| # | Item | Detail | Source |
| --- | --- | --- | --- |
| 17 | **Agent endpoint stays public** | "The deployed agent endpoint URL stays publicly addressable... If you need the agent endpoint itself to be private, that's a platform-side feature outside the scope of this extension today." Isolation is per-user identity, not network. | [VERIFIED] virtual-networks (azd pivot) |
| 18 | **Code Interpreter file operations break in private BYO config** | "In a private network (BYO) configuration, Code Interpreter only works in scenarios that don't involve file uploads or downloads." SDK-only workaround via explicit `container_id`; the portal UI does not support it. | [VERIFIED] virtual-networks |
| 19 | **Azure Blob Storage + File Search unsupported** | "Using Azure Blob Storage files with the File Search tool isn't supported." | [VERIFIED] virtual-networks |
| 20 | **Private ACR support is date-gated** | "Projects created after June 25, 2026 support a private ACR. Projects created before that date require the ACR to be reachable over its public endpoint." | [VERIFIED] virtual-networks |
| 21 | **No CLI flag for VNet integration** | "No first-class CLI flag. All VNet wiring is manual Bicep customization plus operational discipline for runner placement, DNS, and RBAC." | [VERIFIED] virtual-networks |
| 22 | **Added managed-resource cost** | ACA VNet integration creates an `ME_`-prefixed managed resource group billing one standard static public IP for egress (+ one for ingress if external) and one standard load balancer. Private endpoints, Search, and Cosmos 3000 RU/s add further cost. | [VERIFIED] custom-virtual-networks |

### D.16 Preview status

| Component | Status | Evidence |
| --- | --- | --- |
| **Foundry Agent Service** | **GA**, with caveats | [VERIFIED] "Foundry Agent Service is generally available (GA). **Some sub-features are in public preview and might have different constraints.**" — limits-quotas-regions |
| **`networkInjections` ARM property** | **Available in a STABLE API version** (`2025-06-01`) | [VERIFIED] ARM schema reference for `2025-06-01` |
| **Standard Setup with private networking (portal / Bicep / Terraform path)** | Not labelled preview; documented as a supported setup with a published limitations list | [VERIFIED] virtual-networks, Templates pivot |
| **`azd` hosted-agent VNet path** | **PREVIEW** | [VERIFIED] "The agent endpoint stays public **in this preview**." and "Agent endpoint itself — No, **in this preview**" — virtual-networks, azd pivot |
| **Container Apps VNet integration (workload profiles)** | **GA** | [INFERRED] Present in stable API versions from `2023-05-01`; documented without preview labels. |
| **Cosmos DB Private Link** | **GA** | [INFERRED] Long-standing GA feature; no preview markers on the how-to page. |

**Workshop recommendation [INFERRED]:** The individual building blocks are GA or stable-API, but the **`azd` hosted-agent VNet path is explicitly preview** and, more importantly, the operational consequences (item 8 — deployment must originate inside the VNet) fundamentally change the attendee experience. A workshop attendee on a laptop cannot run `azd up` against a Foundry account with public access disabled. This is the dominant practical blocker, above and beyond any preview labelling.

### D.17 Suggested target topology

**[INFERRED]** Based on the verified constraints above:

```text
VNet  10.20.0.0/16  (eastus2, same region as Foundry account)
├── snet-aca            10.20.0.0/23   delegated Microsoft.App/environments   (ACA env #1)
├── snet-aca-2          10.20.2.0/23   delegated Microsoft.App/environments   (ACA env #2)
├── snet-agent          10.20.4.0/24   delegated Microsoft.App/environments   (Foundry networkInjections — exclusive)
└── snet-pe             10.20.5.0/24   privateEndpointNetworkPolicies: Disabled
    ├── PE → Cosmos           groupIds ['Sql']          → privatelink.documents.azure.com
    ├── PE → Foundry account  groupIds ['account']      → privatelink.cognitiveservices.azure.com
    │                                                     + privatelink.openai.azure.com
    │                                                     + privatelink.services.ai.azure.com
    ├── PE → Storage          groupIds ['blob']         → privatelink.blob.core.windows.net
    └── PE → AI Search        groupIds ['searchService'] → privatelink.search.windows.net

All privatelink zones linked to the VNet via virtualNetworkLinks (registrationEnabled: false).
```

Notes:

- **[VERIFIED]** Each ACA environment needs its **own** dedicated subnet — "you need to provide a subnet dedicated exclusively to the Container Apps environment... This subnet isn't available to other services."
- **[VERIFIED]** The agent subnet must be separate from the ACA subnets and exclusive to one Foundry account.
- **[INFERRED]** ACA and Foundry agent injection share the same delegation service name but cannot share a subnet.
- **[INFERRED]** A single Cosmos account can serve double duty as the application store *and* the Foundry BYO thread store, but Foundry will create the `enterprise_memory` database with five containers alongside the application's own databases, and the RU/s floor of 3000 applies.

---

## Open Questions for the User

1. **Should the Foundry account's `publicNetworkAccess` remain `Enabled` while `networkInjections` is set?** (See C.13 UNVERIFIED note.) If viable, this preserves public `azd`/CI/portal access while still giving the agent private egress to Cosmos — a far better workshop story. This is the highest-value item to test.
2. **Is the existing Cosmos account intended to also serve as the Foundry BYO thread store**, or should a second Cosmos account be provisioned for Foundry? The 3000 RU/s floor and `enterprise_memory` database creation are the deciding factors.
3. **Is recreating the Foundry account and both Container Apps environments acceptable**, given the endpoint/FQDN churn across `infra/`, `azure.yaml`, CI variables, and all 15 lab documents?
4. **Where will `azd provision` / `azd deploy` run from** once private networking is in place — self-hosted runner, Bastion jump host, or is public Foundry access being retained (see item 1)?
5. **Does the tenant-root policy apply `modify` to other resource types** (Storage, AI Search, Cognitive Services)? If Storage and Search will also be forced to `publicNetworkAccess: Disabled`, additional private endpoints become mandatory rather than optional.

## Recommended Next Research (not completed in this session)

- [ ] Empirically verify that a Bicep `Microsoft.DocumentDB/databaseAccounts` redeploy succeeds against the policy-disabled Cosmos account from a public runner (confirms the control-plane conclusion in B.4).
- [ ] Empirically verify whether `networkInjections` + `publicNetworkAccess: 'Enabled'` is an accepted combination on `Microsoft.CognitiveServices/accounts@2025-06-01`.
- [ ] Retrieve `https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/agents-networking-deep-dive` — this page is referenced by the virtual-networks article for "network architecture, subnet sizing, and IP allocation model" but could not be extracted in this session (fetch returned no content on two attempts). It may contain the definitive statement about agent egress reachability to arbitrary private endpoints (Q13).
- [ ] Review the reference implementations for the exact wiring order of capability hosts, connections, and role assignments:
  - <https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup>
  - <https://github.com/Azure/azure-quickstart-templates/tree/master/quickstarts/microsoft.azure-ai-agent-service/network-secured-agent>
- [ ] Confirm whether the Azure Policy `modify` effect would also re-disable public access on a newly created Foundry account or Storage account mid-deployment, which could race with capability-host provisioning.
- [ ] Determine the current per-attendee cost delta (2 static public IPs + load balancer per ACA env, 4+ private endpoints, AI Search SKU, Cosmos 3000 RU/s) to judge workshop viability.

## Source Index

| Topic | URL |
| --- | --- |
| ACA networking concepts (env types, VNet immutability, public network access) | <https://learn.microsoft.com/en-us/azure/container-apps/networking> |
| ACA VNet configuration (subnet sizes, delegation, reserved ranges, managed resources) | <https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks> |
| ACA VNet how-to (CLI/portal, delegation command, networking parameters) | <https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom> |
| `Microsoft.App/managedEnvironments` ARM schema | <https://learn.microsoft.com/en-us/azure/templates/microsoft.app/managedenvironments> |
| Cosmos DB Private Link (group IDs, DNS zones, DNS zone groups, limitations) | <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints> |
| Cosmos DB IP firewall (403 semantics, publicNetworkAccess precedence) | <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-firewall> |
| Cosmos DB VNet service endpoints (403 vs connection-level behavior) | <https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-vnet-service-endpoint> |
| Private endpoint network policies (current default = Disabled) | <https://learn.microsoft.com/en-us/azure/private-link/disable-private-endpoint-network-policy> |
| Foundry Agent Service private networking (injection, limitations, DNS, troubleshooting) | <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks> |
| Foundry standard agent setup (BYO resources, RU/s, roles, capability hosts) | <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/standard-agent-setup> |
| Foundry limits / quotas / regions (eastus2, private VNet support, session quotas) | <https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/limits-quotas-regions> |
| `Microsoft.CognitiveServices/accounts` ARM schema (latest) | <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts> |
| `Microsoft.CognitiveServices/accounts` 2025-06-01 (stable, has networkInjections) | <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/2025-06-01/accounts> |
| `Microsoft.CognitiveServices/accounts` 2025-04-01-preview | <https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/2025-04-01-preview/accounts> |
