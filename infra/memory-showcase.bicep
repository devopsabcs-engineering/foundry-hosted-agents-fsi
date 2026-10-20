// Additive, opt-in prerequisite; never include this in the primary environment deployment.
targetScope = 'resourceGroup'

@description('Existing staging Foundry account approved for the isolated synthetic memory demo.')
@minLength(2)
param accountName string

@description('Confirm regional model/version/SKU availability and at least one unit of unused quota.')
@allowed([true])
param regionalQuotaConfirmed bool

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'showcase-memory-embedding'
  sku: {
    name: 'Standard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
  tags: {
    purpose: 'synthetic-native-memory-showcase'
    issue: '20'
    regionalQuotaConfirmed: string(regionalQuotaConfirmed)
  }
}

output embeddingDeploymentName string = embedding.name
output embeddingDeploymentResourceId string = embedding.id
