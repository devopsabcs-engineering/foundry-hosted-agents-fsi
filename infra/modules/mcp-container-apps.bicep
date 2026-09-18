// ============================================================================
// Container Apps environment and two apps hosting the decoupled, read-only
// MCP tool servers (application-server: get_application, rulebook-server:
// get_rulebook). Self-contained: this module provisions its own Log
// Analytics workspace and does not reference infra/modules/ai-foundry.bicep
// or any other module, so it compiles and deploys independently.
//
// Ingress stays external (public HTTPS) even though the environment is now
// VNet-integrated: the Foundry account keeps publicNetworkAccess enabled, and
// the agent runtime reaches these FQDNs the same way a browser does. The VNet
// exists so workloads in this environment can resolve and reach the Cosmos
// private endpoint, which tenant policy makes the only reachable path.
// Images are intended to be built and pushed via `az acr build` (see
// acrName param) rather than the public placeholder image below.
// ============================================================================

@description('Location for the MCP Container Apps environment and apps.')
param location string = resourceGroup().location

@description('Base name used to derive resource names.')
param namePrefix string = 'mcp'

@description('Name of the existing Azure Container Registry hosting the built MCP server images.')
param acrName string = ''

@description('Container image for the application-server MCP server (get_application).')
param applicationImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Container image for the rulebook-server MCP server (get_rulebook).')
param rulebookImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Port exposed by each MCP server container (matches PORT env var in mcp/*/main.py).')
param containerPort int = 8000

@description('Resource ID of the delegated infrastructure subnet for this environment (infra/network.bicep output acaStagingSubnetId or acaProductionSubnetId)')
param infrastructureSubnetId string

var useAcr = !empty(acrName)
// Every environment (staging and production) gets its own pull identity with an
// automatically granted, idempotent AcrPull role assignment -- relying on an
// out-of-band manual grant for a shared system-assigned identity left production
// with no ACR permission and revisions that never provisioned ("Operation expired").
var isolatedPullIdentity = useAcr

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (useAcr) {
  name: acrName
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (isolatedPullIdentity) {
  name: '${namePrefix}-image-pull'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (isolatedPullIdentity) {
  name: guid(acr!.id, pullIdentity!.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: pullIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

var logAnalyticsWorkspaceName = '${namePrefix}-mcp-logs'
var environmentName = '${namePrefix}-mcp-env'

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
    // internal: false keeps ingress on a public FQDN; only egress moves into the VNet.
    // This whole block is immutable, so switching it on an existing environment
    // requires deleting and recreating the environment and every app inside it.
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    // The infrastructure subnet is delegated to Microsoft.App/environments, which
    // Consumption-only environments reject; a workload profile environment is the
    // shape that accepts a delegated subnet.
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

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
        // minReplicas: 1 keeps this MCP server warm so the hosted agent's
        // first tool call after idle does not hit a multi-minute cold start.
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource rulebookContainerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-rulebook-server'
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
          name: 'rulebook-server'
          image: rulebookImage
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
        // minReplicas: 1 keeps this MCP server warm so the hosted agent's
        // first tool call after idle does not hit a multi-minute cold start.
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output containerAppsEnvironmentId string = containerAppsEnvironment.id
output applicationContainerAppFqdn string = applicationContainerApp.properties.configuration.ingress.fqdn
output rulebookContainerAppFqdn string = rulebookContainerApp.properties.configuration.ingress.fqdn
