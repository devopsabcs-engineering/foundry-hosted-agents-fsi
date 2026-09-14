// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
// ============================================================================

targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name used to derive resource names (e.g. dev, poc)')
param environmentName string

@description('Foundry account (Microsoft.CognitiveServices/accounts) name')
param accountName string = 'aif-${environmentName}'

@description('Foundry project name')
param projectName string = 'proj-${environmentName}'

@description('Model deployment name. Placeholder pending Gate G2/G3 sign-off.')
param modelDeploymentName string = 'gpt-4o-mini'

@description('Model name to deploy. Placeholder pending Gate G2/G3 sign-off.')
param modelName string = 'gpt-4o-mini'

@description('Model publisher format')
param modelFormat string = 'OpenAI'

@description('Model version. Placeholder pending Gate G3 sign-off.')
param modelVersion string = '2024-07-18'

@description('Model deployment SKU name')
param modelSkuName string = 'GlobalStandard'

@description('Model deployment SKU capacity (thousands of tokens-per-minute)')
param modelSkuCapacity int = endsWith(environmentName, '-staging') ? 50 : 10

@description('Principal IDs to receive Foundry RBAC roles (e.g. the CI/CD identity). Leave empty to skip role assignment.')
param principalIds array = []

@description('Principal type applied to every entry in principalIds')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string = 'log-${environmentName}'

@description('Application Insights component name')
param applicationInsightsName string = 'appi-${environmentName}'

@description('Name of the existing Azure Container Registry hosting the built MCP server images. Leave empty to use the public placeholder image.')
param mcpAcrName string = ''

@description('Container image reference for the application-server MCP server (get_application)')
param applicationMcpImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Container image reference for the rulebook-server MCP server (get_rulebook)')
param rulebookMcpImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('MCP resource prefix; staging must not share production tool apps.')
param mcpNamePrefix string = ''

var effectiveMcpNamePrefix = !empty(mcpNamePrefix) ? mcpNamePrefix : (endsWith(environmentName, '-staging') ? 'mcp-staging' : 'mcp')

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  params: {
    location: location
    accountName: accountName
    projectName: projectName
    applicationInsightsResourceId: monitoring.outputs.applicationInsightsId
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    modelDeploymentName: modelDeploymentName
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelSkuCapacity: modelSkuCapacity
    applicationMcpUrl: 'https://${mcpContainerApps.outputs.applicationContainerAppFqdn}/mcp'
    rulebookMcpUrl: 'https://${mcpContainerApps.outputs.rulebookContainerAppFqdn}/mcp'
  }
}

module rbac 'modules/rbac.bicep' = if (!empty(principalIds)) {
  name: 'rbac'
  params: {
    accountName: aiFoundry.outputs.accountName
    principalIds: principalIds
    principalType: principalType
  }
}

module mcpContainerApps 'modules/mcp-container-apps.bicep' = {
  name: 'mcp-container-apps'
  params: {
    location: location
    namePrefix: effectiveMcpNamePrefix
    acrName: mcpAcrName
    applicationImage: applicationMcpImage
    rulebookImage: rulebookMcpImage
  }
}

output accountName string = aiFoundry.outputs.accountName
output accountEndpoint string = aiFoundry.outputs.accountEndpoint
output projectName string = aiFoundry.outputs.projectName
output modelDeploymentName string = aiFoundry.outputs.modelDeploymentName
output FOUNDRY_PROJECT_ENDPOINT string = aiFoundry.outputs.projectEndpoint
// ARM resource ID of the Foundry project -- required by azd's azure.ai.agent host
// target to publish/deploy hosted agents (distinct from the v2 data-plane project endpoint above).
output AZURE_AI_PROJECT_ID string = aiFoundry.outputs.projectId
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output applicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString
output APPLICATION_MCP_URL string = 'https://${mcpContainerApps.outputs.applicationContainerAppFqdn}/mcp'
output RULEBOOK_MCP_URL string = 'https://${mcpContainerApps.outputs.rulebookContainerAppFqdn}/mcp'
