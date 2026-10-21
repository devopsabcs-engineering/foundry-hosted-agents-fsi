// Opt-in, additive deployment. This file is deliberately not referenced by main.bicep.
targetScope = 'resourceGroup'

@description('Globally unique NEW Search service name. Never supply a baseline resource name.')
@minLength(2)
@maxLength(60)
param searchServiceName string

@description('Region verified by the operator to support agentic retrieval and semantic ranking.')
param location string

@description('Explicit acknowledgement of regional availability and additional ongoing Search charges.')
@allowed([true])
param prerequisitesConfirmed bool

@description('Optional existing Log Analytics workspace resource ID. No workspace is changed.')
param logAnalyticsWorkspaceResourceId string = ''

@description('Object IDs of operators permitted to create the showcase index, source, and knowledge base.')
param operatorPrincipalIds array = []

@description('Object IDs permitted to upload the synthetic corpus.')
param ingestionPrincipalIds array = []

@description('Object IDs permitted to query the synthetic corpus.')
param queryPrincipalIds array = []

@allowed(['User', 'Group', 'ServicePrincipal'])
param principalType string = 'User'

@description('Query identity type; use ServicePrincipal for Foundry project managed identities.')
@allowed(['User', 'Group', 'ServicePrincipal'])
param queryPrincipalType string = principalType

var operatorRoles = [for id in operatorPrincipalIds: {
  principalId: id
  principalType: principalType
  roleDefinitionIdOrName: 'Search Service Contributor'
}]
var ingestionRoles = [for id in ingestionPrincipalIds: {
  principalId: id
  principalType: principalType
  roleDefinitionIdOrName: 'Search Index Data Contributor'
}]
var queryRoles = [for id in queryPrincipalIds: {
  principalId: id
  principalType: queryPrincipalType
  roleDefinitionIdOrName: 'Search Index Data Reader'
}]

module search 'br/public:avm/res/search/search-service:0.13.0' = {
  name: 'native-knowledge-showcase'
  params: {
    name: searchServiceName
    location: location
    sku: 'basic'
    replicaCount: 1
    partitionCount: 1
    disableLocalAuth: true
    enableTelemetry: false
    semanticSearch: 'free'
    managedIdentities: {
      systemAssigned: true
    }
    publicNetworkAccess: 'Enabled'
    tags: {
      purpose: 'synthetic-native-knowledge-showcase'
      issue: '8'
      regionalPrerequisitesConfirmed: string(prerequisitesConfirmed)
    }
    roleAssignments: concat(operatorRoles, ingestionRoles, queryRoles)
    diagnosticSettings: empty(logAnalyticsWorkspaceResourceId) ? [] : [{
      name: 'showcase-search-diagnostics'
      workspaceResourceId: logAnalyticsWorkspaceResourceId
      logCategoriesAndGroups: [{
        categoryGroup: 'allLogs'
      }]
      metricCategories: [{
        category: 'AllMetrics'
      }]
    }]
  }
}

output searchResourceId string = search.outputs.resourceId
output searchEndpoint string = 'https://${searchServiceName}.search.windows.net'
output searchPrincipalId string = search.outputs.?systemAssignedMIPrincipalId ?? ''
