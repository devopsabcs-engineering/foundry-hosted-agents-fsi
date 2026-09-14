// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
// ============================================================================

@description('Azure region for the monitoring resources')
param location string = resourceGroup().location

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string

@description('Application Insights component name')
param applicationInsightsName string

@description('Log Analytics data retention in days')
param retentionInDays int = 30

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

output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name
output applicationInsightsId string = applicationInsights.id
output applicationInsightsName string = applicationInsights.name
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
