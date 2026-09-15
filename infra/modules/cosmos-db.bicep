// ============================================================================
// AUTHOR-ONLY / NOT DEPLOYED.
// Gated behind G2 (platform/security), G3 (reproducible compatibility), and
// G6 (regulatory/privacy) sign-off. Do not run `azd provision`, `azd deploy`,
// `azd up`, `az deployment group create`, or any apply command against this
// template until all three gates are explicitly cleared by their owners.
// This file has only been authored and lint/compile-checked with
// `bicep build` / `az bicep build`. See infra/README.md.
//
// Serverless Cosmos DB account backing the shared approval case store that the
// hosted agent writes and the reviewer app reads and decides on
// (src/quote-preparation-agent/cosmos_case_store.py). The database, container,
// and partition key below must stay in lockstep with COSMOS_DATABASE_ID,
// COSMOS_CONTAINER_ID, and COSMOS_PARTITION_KEY_PATH in
// src/quote-preparation-agent/case_store.py.
//
// Data-plane role assignments deliberately live in modules/cosmos-rbac.bicep
// rather than here: the reviewer Container App consumes this module's
// documentEndpoint output, so granting its principal from inside this module
// would create a dependency cycle.
// ============================================================================

@description('Azure region for the Cosmos DB account')
param location string = resourceGroup().location

@description('Cosmos DB account name. Globally unique across Azure, lowercase letters/digits/hyphens only, 3-44 characters.')
@minLength(3)
@maxLength(44)
param accountName string

@description('SQL database holding the approval case store (matches COSMOS_DATABASE_ID in src/quote-preparation-agent/case_store.py)')
param databaseName string = 'quote-preparation'

@description('SQL container holding one document per case (matches COSMOS_CONTAINER_ID in src/quote-preparation-agent/case_store.py)')
param containerName string = 'cases'

@description('Partition key path for the cases container (matches COSMOS_PARTITION_KEY_PATH in src/quote-preparation-agent/case_store.py)')
param partitionKeyPath string = '/caseId'

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    // Serverless accounts are single-region: adding a second locations entry is rejected.
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    // The case store authenticates with DefaultAzureCredential only and no code path
    // accepts an account key, so key-based access is switched off at the account.
    // This intentionally diverges from the Foundry account's disableLocalAuth: false.
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: 'Tls12'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          partitionKeyPath
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
        // Serves list_cases_by_state's cross-partition
        // `WHERE c.state = @state ORDER BY c.updatedAt DESC`.
        compositeIndexes: [
          [
            {
              path: '/state'
              order: 'ascending'
            }
            {
              path: '/updatedAt'
              order: 'descending'
            }
          ]
        ]
      }
    }
  }
}

output accountId string = account.id
output accountName string = account.name
output documentEndpoint string = account.properties.documentEndpoint
output databaseName string = database.name
output containerName string = container.name
