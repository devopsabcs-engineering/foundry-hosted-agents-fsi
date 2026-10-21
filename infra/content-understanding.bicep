// Opt-in dedicated CU deployments. Never patch shared account/analyzer defaults.
targetScope = 'resourceGroup'

@description('Existing Foundry account. Deploy to staging first; never replace baseline deployments.')
param accountName string

@description('Confirm supported regional models, quota, and additional metered charges before apply.')
@allowed([true])
param prerequisitesConfirmed bool

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource completion 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'fsi-showcase-cu-completion'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
  tags: {
    purpose: 'synthetic-content-understanding'
    prerequisitesConfirmed: string(prerequisitesConfirmed)
    issue: '45'
  }
}

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'fsi-showcase-cu-embedding'
  dependsOn: [
    completion
  ]
  sku: {
    name: 'Standard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
  tags: {
    purpose: 'synthetic-content-understanding'
    prerequisitesConfirmed: string(prerequisitesConfirmed)
    issue: '45'
  }
}

output modelDeployments object = {
  'prebuilt-analyzer-completion': completion.name
  'prebuilt-analyzer-embedding': embedding.name
}
