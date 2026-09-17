// ============================================================================
// Per-environment stack for the quote-preparation workshop. Deployed twice into
// one resource group, once for staging and once for production.
//
// The VNet, its subnets, and the Cosmos private DNS zone are NOT declared here.
// They live in infra/network.bicep and are deployed once for the whole resource
// group, because an ARM write of a VNet that omits `subnets` deletes the subnets
// it does not name, so a template that runs twice cannot own that resource.
// Deploy infra/network.bicep first; this template consumes it with `existing`.
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

// Cosmos account names are globally unique across Azure and accept only lowercase
// letters, digits, and hyphens, 3-44 characters. 'cosmos-' costs 7 of that budget,
// leaving 37 for environmentName: staging's 'desjardins-quote-preparation-staging'
// (36) resolves to 43 and production's 'desjardins-quote-preparation' (28) to 35.
// There is no uniqueString() convention in this repository to fall back on, so the
// @maxLength below is what turns an over-long environmentName into a parameter
// validation failure instead of a mid-deployment ARM error.
@description('Cosmos DB account name backing the shared approval case store. Globally unique, lowercase, 3-44 characters.')
@minLength(3)
@maxLength(44)
param cosmosAccountName string = toLower('cosmos-${environmentName}')

// Container App names are capped at 32 characters, so unlike every other name in this
// template the reviewer app cannot interpolate environmentName: 'reviewer-' plus
// staging's 36-character name is 45. The repository already handles this by branching
// on the '-staging' suffix (see effectiveMcpNamePrefix) and by giving web-chat a short
// literal name; this follows both, as the sibling of 'foundry-quote-chat-staging'.
@description('Container App name for the reviewer approval surface. Container App names are limited to 32 characters.')
@minLength(2)
@maxLength(32)
param reviewerAppName string = endsWith(environmentName, '-staging') ? 'foundry-quote-reviewer-staging' : 'foundry-quote-reviewer'

@description('Container image reference for the reviewer app (apps/reviewer-app); digest-pinned by CI')
param reviewerAppImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// Empty is the pre-Phase-6 default and deliberately skips the reviewer module rather
// than deploying a Container App that would crash-loop: Settings.from_env parses this
// value with uuid.UUID(), so an empty string is a startup failure, not a degraded mode.
@description('Entra application (client) ID of the reviewer app registration from scripts/setup-reviewer-identity.ps1. Leave empty to skip deploying the reviewer app.')
param reviewerClientId string = ''

@description('Entra tenant ID authorized to sign in to the reviewer surface')
param reviewerTenantId string = subscription().tenantId

@description('App role value required to use the reviewer surface')
param reviewerRole string = 'Reviewer'

@description('Delegated scope required on the reviewer access token')
param reviewerScope string = 'Review.Access'

// A hosted agent gets its own dedicated per-agent Microsoft Entra identity, created by
// Foundry at `azd deploy` time -- after this template runs -- and it is explicitly NOT
// the Foundry project or account system-assigned identity. It therefore cannot be
// resolved here and must be supplied after the first agent deployment. Leaving this
// empty skips the grant, and the agent cannot write cases until it is supplied.
@description('Object ID of the hosted agent\'s Entra agent identity, to receive Cosmos data-plane write access. Leave empty to skip the grant.')
param agentPrincipalId string = ''

@description('Name of the shared virtual network deployed by infra/network.bicep')
param vnetName string = 'vnet-desjardins-quote-preparation'

@description('Name of the private DNS zone for Cosmos SQL private endpoints, linked to the shared VNet by infra/network.bicep')
param cosmosPrivateDnsZoneName string = 'privatelink.documents.azure.com'

var isStaging = endsWith(environmentName, '-staging')
var effectiveMcpNamePrefix = !empty(mcpNamePrefix) ? mcpNamePrefix : (isStaging ? 'mcp-staging' : 'mcp')
var reviewerEnvironment = isStaging ? 'staging' : 'production'
var deployReviewerApp = !empty(reviewerClientId)
var acaSubnetName = isStaging ? 'snet-aca-staging' : 'snet-aca-production'
var agentSubnetName = isStaging ? 'snet-agent-staging' : 'snet-agent-production'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName

  resource acaSubnet 'subnets' existing = {
    name: acaSubnetName
  }

  resource agentSubnet 'subnets' existing = {
    name: agentSubnetName
  }

  resource privateEndpointSubnet 'subnets' existing = {
    name: 'snet-private-endpoints'
  }
}

resource cosmosPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' existing = {
  name: cosmosPrivateDnsZoneName
}

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
    agentSubnetId: vnet::agentSubnet.id
  }
}

// The project's own system-assigned identity must hold Foundry User on its
// account to write hosted-evaluation artifacts back to the project's storage
// (POST .../datasets/{name}/versions/{version}/startPendingUpload): without
// it, `azd deploy`'s hosted evaluation run fails with ClientAuthenticationError
// PermissionDenied on Microsoft.CognitiveServices/accounts/AIServices/assets/write.
// Always included; principalIds only adds extra (e.g. CI/CD) principals on top.
module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    accountName: aiFoundry.outputs.accountName
    principalIds: concat([aiFoundry.outputs.projectPrincipalId], principalIds)
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
    infrastructureSubnetId: vnet::acaSubnet.id
  }
}

module cosmos 'modules/cosmos-db.bicep' = {
  name: 'cosmos-db'
  params: {
    location: location
    accountName: cosmosAccountName
    privateEndpointSubnetId: vnet::privateEndpointSubnet.id
    privateDnsZoneId: cosmosPrivateDnsZone.id
  }
}

module reviewerApp 'modules/reviewer-app.bicep' = if (deployReviewerApp) {
  name: 'reviewer-app'
  params: {
    location: location
    appName: reviewerAppName
    containerAppsEnvironmentId: mcpContainerApps.outputs.containerAppsEnvironmentId
    acrName: mcpAcrName
    image: reviewerAppImage
    tenantId: reviewerTenantId
    reviewerClientId: reviewerClientId
    reviewerRole: reviewerRole
    reviewerScope: reviewerScope
    environment: reviewerEnvironment
    cosmosEndpoint: cosmos.outputs.documentEndpoint
  }
}

// Two single-principal instantiations rather than one module over a combined array:
// building that array would mean a ternary over a conditional module's output, and
// ARM evaluates both branches of if() eagerly. Each condition here stands alone.
module cosmosReviewerRbac 'modules/cosmos-rbac.bicep' = if (deployReviewerApp) {
  name: 'cosmos-rbac-reviewer'
  params: {
    accountName: cosmos.outputs.accountName
    principalIds: [reviewerApp!.outputs.principalId]
  }
}

module cosmosAgentRbac 'modules/cosmos-rbac.bicep' = if (!empty(agentPrincipalId)) {
  name: 'cosmos-rbac-agent'
  params: {
    accountName: cosmos.outputs.accountName
    principalIds: [agentPrincipalId]
  }
  // Serialized: concurrent sqlRoleAssignments writes against one account return 409.
  dependsOn: [cosmosReviewerRbac]
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
output cosmosAccountName string = cosmos.outputs.accountName
// Consumed as the COSMOS_ENDPOINT env var: the case store falls back to SQLite when unset.
output COSMOS_ENDPOINT string = cosmos.outputs.documentEndpoint
output REVIEWER_APP_URL string = deployReviewerApp ? reviewerApp!.outputs.url : ''
output REVIEWER_APP_NAME string = deployReviewerApp ? reviewerAppName : ''
output reviewerAppPrincipalId string = deployReviewerApp ? reviewerApp!.outputs.principalId : ''
