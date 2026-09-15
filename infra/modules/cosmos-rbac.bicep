// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
//
// Cosmos DB SQL *data-plane* role assignments.
//
// READ THIS BEFORE EDITING. Every other role assignment in this repository uses
// Microsoft.Authorization/roleAssignments with
// subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ...)
// -- see modules/rbac.bicep, modules/mcp-container-apps.bicep, web-chat.bicep.
// That pattern does NOT grant Cosmos data-plane access. Cosmos read/write
// permission is a separate RBAC system: the role definition is a child of the
// account (Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions) and the
// assignment is a child of the account
// (Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments) whose data-plane
// scope is carried as a string *property*, not the Bicep `scope:` keyword.
// Using the control-plane pattern here deploys successfully and then fails at
// runtime with 403 on the first read or write.
// ============================================================================

@description('Name of the existing Cosmos DB account to scope the data-plane role assignments to')
param accountName string

@description('Principal IDs to receive the Cosmos data-plane role')
param principalIds array

@description('Built-in Cosmos DB SQL role definition GUID. Not an Azure RBAC role definition GUID.')
param roleDefinitionId string = '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: accountName
}

resource roleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = [
  for principalId in principalIds: {
    parent: account
    name: guid(account.id, principalId, roleDefinitionId)
    properties: {
      roleDefinitionId: resourceId(
        'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions',
        accountName,
        roleDefinitionId
      )
      principalId: principalId
      scope: account.id
    }
  }
]
