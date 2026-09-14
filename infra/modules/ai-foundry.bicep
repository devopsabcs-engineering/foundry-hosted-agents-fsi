// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
//
// Model name/version/SKU defaults below are placeholders pending Gate G2
// (platform/security) and G3 (reproducible compatibility) discovery -- do
// not treat them as an approved model selection.
// ============================================================================

@description('Azure region for the Foundry account and project')
param location string = resourceGroup().location

@description('Name of the Microsoft.CognitiveServices/accounts (Foundry) resource')
param accountName string

@description('Name of the Foundry project')
param projectName string

@description('Display name shown in the Foundry portal for the project')
param projectDisplayName string = projectName

@description('Description of the Foundry project')
param projectDescription string = 'Desjardins synthetic auto-insurance quote-preparation workshop project (synthetic data only, non-binding, no regulatory endorsement)'

@description('Model deployment name (referenced by azure.yaml AZURE_AI_MODEL_DEPLOYMENT_NAME). Placeholder pending Gate G2/G3 sign-off.')
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
param modelSkuCapacity int = 10

@description('MCP endpoint URL for the application-server tool server (get_application). Leave empty to skip creating the connection.')
param applicationMcpUrl string = ''

@description('MCP endpoint URL for the rulebook-server tool server (get_rulebook). Leave empty to skip creating the connection.')
param rulebookMcpUrl string = ''

@description('Application Insights resource associated with this project')
param applicationInsightsResourceId string

@secure()
@description('Application Insights ingestion connection string')
param applicationInsightsConnectionString string

// Basic Agent Setup: Microsoft-managed conversation/file/vector storage — no capabilityHosts.
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: modelDeploymentName
  sku: {
    name: modelSkuName
    capacity: modelSkuCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectDisplayName
    description: projectDescription
  }
}

resource telemetryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'application-insights'
  properties: {
    category: 'AppInsights'
    target: applicationInsightsResourceId
    authType: 'ApiKey'
    credentials: {
      key: applicationInsightsConnectionString
    }
    isSharedToAll: true
    metadata: {
      ResourceId: applicationInsightsResourceId
    }
  }
}

// Placeholder so the project can reference the account's model deployment via AAD;
// category/metadata shape to be refined once agent-specific connection needs are known.
resource modelConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: '${modelDeploymentName}-connection'
  properties: {
    category: 'AzureOpenAI'
    target: account.properties.endpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: account.id
      DeploymentName: modelDeploymentName
    }
  }
  dependsOn: [
    modelDeployment
  ]
}

output accountId string = account.id
output accountName string = account.name
output accountEndpoint string = account.properties.endpoint
output accountPrincipalId string = account.identity.principalId
output projectId string = project.id
output projectName string = project.name
output projectPrincipalId string = project.identity.principalId
output modelDeploymentName string = modelDeployment.name
// Foundry v2 project endpoint (not derivable from account.properties.endpoint's .cognitiveservices.azure.com domain)
output projectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'

// azd's azure.ai.connection host (azure.yaml: application-conn/rulebook-conn) treats connections whose
// endpoint resolves from a bicep output as infrastructure-managed and skips creating them itself
// during `azd deploy` -- so these MCP Toolbox connections must be created here instead.
resource applicationConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (!empty(applicationMcpUrl)) {
  parent: project
  name: 'application-conn'
  properties: {
    category: 'RemoteTool'
    target: applicationMcpUrl
    authType: 'None'
    isSharedToAll: true
  }
}

resource rulebookConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (!empty(rulebookMcpUrl)) {
  parent: project
  name: 'rulebook-conn'
  properties: {
    category: 'RemoteTool'
    target: rulebookMcpUrl
    authType: 'None'
    isSharedToAll: true
  }
}
