@description('Foundry account containing the hosted quote-preparation agent')
param accountName string

@description('Foundry project containing the hosted quote-preparation endpoint')
param projectName string

@description('Reviewer managed identity object ID')
param principalId string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: projectName
}

// Foundry Agent Consumer grants endpoints/interact/action, not agent authoring
// or memory access. Assignment propagation can take several minutes.
var consumerRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'eed3b665-ab3a-47b6-8f48-c9382fb1dad6')

resource assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, principalId, consumerRoleId)
  scope: project
  properties: {
    roleDefinitionId: consumerRoleId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
