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

// Provider-registered invocation operations only; no memory, agent-management,
// model-deployment, or user-identity impersonation permissions.
resource invoker 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'quote-preparation-responses-invoker')
  properties: {
    roleName: 'Quote Preparation Responses Invoker (${resourceGroup().name})'
    description: 'Invoke hosted Foundry Responses endpoints without memory or management access.'
    type: 'CustomRole'
    assignableScopes: [resourceGroup().id]
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.CognitiveServices/accounts/AIServices/endpoints/invoke/action'
          'Microsoft.CognitiveServices/accounts/AIServices/applications/invoke/action'
          'Microsoft.CognitiveServices/accounts/AIServices/responses/write'
        ]
        notDataActions: []
      }
    ]
  }
}

resource assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, principalId, invoker.id)
  scope: project
  properties: {
    roleDefinitionId: invoker.id
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
