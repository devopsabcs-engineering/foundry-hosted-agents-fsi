// ============================================================================
// Container App hosting the reviewer approval surface (apps/reviewer-app).
// Shape follows web-chat.bicep -- the repository's only user-facing Container
// App -- but this is a module wired into main.bicep rather than a standalone
// template, so the reviewer identity's principalId is available in-template for
// the Cosmos data-plane grant in modules/cosmos-rbac.bicep.
//
// The managed environment arrives as a resource ID, not a name. web-chat.bicep
// calls its managed-environment parameter `environmentName`, which collides with
// main.bicep's azd-base-name `environmentName`; that ambiguity is deliberately
// not carried over here.
//
// Every env var below is read by apps/reviewer-app. ENTRA_TENANT_ID and
// REVIEWER_CLIENT_ID are parsed with uuid.UUID() in Settings.from_env, so a
// malformed or empty value is a startup crash, not a degraded mode.
// REVIEWER_CLIENT_ID is the reviewer app registration from
// scripts/setup-reviewer-identity.ps1 and is NOT web-chat's ENTRA_CLIENT_ID.
// COSMOS_ENDPOINT selects the Cosmos backend in build_case_store(); the store
// silently falls back to SQLite when it is unset, which for a multi-replica
// reviewer surface would be a data-loss bug rather than a fallback.
// ============================================================================

@description('Azure region for the reviewer Container App and its identity')
param location string = resourceGroup().location

@description('Container App name for the reviewer approval surface. Container App names are limited to 32 characters.')
@minLength(2)
@maxLength(32)
param appName string

@description('Resource ID of the existing Container Apps managed environment (from modules/mcp-container-apps.bicep\'s containerAppsEnvironmentId output)')
param containerAppsEnvironmentId string

@description('Name of the existing Azure Container Registry hosting the built reviewer image. Leave empty to use the public placeholder image.')
param acrName string = ''

@description('Fully digest-pinned image reference for the reviewer container (e.g. <acr>.azurecr.io/reviewer-app@sha256:...); never a floating tag')
param image string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Entra tenant ID authorized to sign in to the reviewer surface')
param tenantId string

@description('Entra application (client) ID of the reviewer app registration (created via scripts/setup-reviewer-identity.ps1; distinct from the web-chat registration)')
param reviewerClientId string

@description('App role value required to use the reviewer surface')
param reviewerRole string = 'Reviewer'

@description('Delegated scope required on the reviewer access token')
param reviewerScope string = 'Review.Access'

@description('Value surfaced as the ENVIRONMENT env var and returned by /api/config')
param environment string = 'staging'

@description('Cosmos DB documentEndpoint backing the shared case store (from modules/cosmos-db.bicep)')
param cosmosEndpoint string

@description('Application Insights connection string (from modules/monitoring.bicep); empty skips telemetry wiring')
param applicationInsightsConnectionString string = ''

@description('Port the reviewer container listens on (matches EXPOSE/uvicorn in apps/reviewer-app/Dockerfile)')
param containerPort int = 8000

var useAcr = !empty(acrName)

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (useAcr) {
  name: acrName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-identity'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useAcr) {
  name: guid(acr!.id, identity.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource reviewer 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    environment: environment
    purpose: 'reviewer-approval-surface'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [pullRole]
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: containerPort
        transport: 'http'
      }
      registries: useAcr
        ? [
            {
              server: acr!.properties.loginServer
              identity: identity.id
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'reviewer-app'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'ENTRA_TENANT_ID'
              value: tenantId
            }
            {
              name: 'REVIEWER_CLIENT_ID'
              value: reviewerClientId
            }
            {
              name: 'REVIEWER_ROLE'
              value: reviewerRole
            }
            {
              name: 'REVIEWER_SCOPE'
              value: reviewerScope
            }
            {
              name: 'ENVIRONMENT'
              value: environment
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identity.properties.clientId
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsightsConnectionString
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: containerPort
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: containerPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = reviewer.properties.configuration.ingress.fqdn
output url string = 'https://${reviewer.properties.configuration.ingress.fqdn}'
output principalId string = identity.properties.principalId
output identityClientId string = identity.properties.clientId
