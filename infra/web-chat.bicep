// ============================================================================
// DEPLOYED OUT-OF-BAND.
//
// Standalone Container App hosting the internal pilot web-chat frontend
// (apps/web-chat). Deliberately NOT wired into infra/main.bicep or
// azure.yaml -- it is deployed via a manual `az deployment group create`
// against this file, into the *existing* Container Apps environment, ACR,
// and Foundry project that infra/main.bicep already provisions. See
// infra/README.md and scripts/setup-web-chat-identity.ps1 for the
// associated Entra app registration.
// ============================================================================

@description('Azure region for the web-chat Container App and its identity')
param location string = resourceGroup().location

@description('Container App name for the web-chat frontend')
param appName string = 'foundry-quote-chat-staging'

@description('Existing Container Apps managed environment name (shared with the MCP servers; matches modules/mcp-container-apps.bicep\'s <namePrefix>-mcp-env pattern)')
param environmentName string = 'mcp-staging-mcp-env'

@description('Existing Azure Container Registry hosting the built web-chat image (no default; must be supplied at deploy time, matching the env-var-driven MCP_ACR_NAME convention used elsewhere in this repo)')
param acrName string

@description('Fully digest-pinned image reference for the web-chat container (e.g. <acr>.azurecr.io/foundry-web-chat@sha256:...); never a floating tag')
param image string

@description('Entra tenant ID authorized to sign in to the pilot (no default; operator must supply the real Desjardins tenant ID)')
param tenantId string

@description('Entra application (client) ID of the web-chat app registration (no default; created via scripts/setup-web-chat-identity.ps1)')
param clientId string

@description('Entra security group ID for the pilot user cohort (no default; operator must supply the real Desjardins pilot group ID)')
param pilotGroupId string

@description('Existing Foundry account (Microsoft.CognitiveServices/accounts) name (matches infra/main.bicep\'s accountName = aif-<environmentName> pattern)')
param foundryAccountName string = 'aif-desjardins-quote-preparation-staging'

@description('Existing Foundry project name (matches infra/main.bicep\'s projectName = proj-<environmentName> pattern)')
param foundryProjectName string = 'proj-desjardins-quote-preparation-staging'

@description('Deployment label reported by /api/config and used as the resource tag; distinct from environmentName, which is the Container Apps managed environment')
@allowed(['staging', 'production'])
param deploymentLabel string = 'staging'

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: environmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: foundryProjectName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-identity'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'AcrPull')
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource invokeRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, identity.id, 'FoundryUser')
  scope: project
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    environment: deploymentLabel
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
          { name: 'ENVIRONMENT', value: deploymentLabel }
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

output url string = 'https://${web.properties.configuration.ingress.fqdn}'
output principalId string = identity.properties.principalId
