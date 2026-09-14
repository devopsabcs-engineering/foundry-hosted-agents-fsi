// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
//
// Container Apps environment and two apps hosting the decoupled, read-only
// MCP tool servers (application-server: get_application, rulebook-server:
// get_rulebook). Self-contained: this module provisions its own Log
// Analytics workspace and does not reference infra/modules/ai-foundry.bicep
// or any other module, so it compiles and (once gates clear) could be
// deployed independently.
//
// Ingress is external (public HTTPS) for both apps: this workshop targets
// Basic (public, no-VNet) Foundry Agent Setup, so the Foundry-managed
// hosted-agent runtime has no private path into an internal-only Container
// Apps FQDN. Standard Agent Setup with VNet integration would allow
// internal-only ingress instead -- revisit if/when Gate G2 requires network
// isolation.
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

output containerAppsEnvironmentId string = containerAppsEnvironment.id
output applicationContainerAppFqdn string = applicationContainerApp.properties.configuration.ingress.fqdn
output rulebookContainerAppFqdn string = rulebookContainerApp.properties.configuration.ingress.fqdn
