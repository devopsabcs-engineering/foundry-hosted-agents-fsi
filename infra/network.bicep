// ============================================================================
// Shared network foundation for the private-networking architecture.
//
// Deployed ONCE per resource group, out-of-band, ahead of infra/main.bicep:
//
//   az deployment group create -g <rg> --template-file infra/network.bicep
//
// It is deliberately NOT part of main.bicep. main.bicep is deployed twice into
// the same resource group (once per azd environment, staging and production),
// and a virtual network declared in both deployments would be written twice.
// An ARM PUT of a virtual network that omits `subnets` removes the subnets that
// the other deployment created, so the address space is owned here and consumed
// downstream through `existing` references.
//
// Subnet layout is driven by three hard constraints from the platform:
//   * A Container Apps workload-profiles environment needs its own subnet
//     delegated to Microsoft.App/environments, and the network type cannot be
//     changed after the environment is created.
//   * A Foundry agent subnet cannot be shared between Foundry accounts, so
//     staging and production each get one.
//   * Private endpoint subnets must disable private endpoint network policies.
// ============================================================================

targetScope = 'resourceGroup'

@description('Azure region for the virtual network. Must match the Foundry account region.')
param location string = resourceGroup().location

@description('Virtual network name')
param vnetName string = 'vnet-desjardins-quote-preparation'

// RFC 1918 space. Foundry rejects public ranges outright, and both Container
// Apps and the agent runtime reserve 169.254.0.0/16, 172.30.0.0/16,
// 172.31.0.0/16, 192.0.2.0/24 and several 100.100.0.0/17 blocks, none of which
// this range overlaps.
@description('Address space for the virtual network')
param vnetAddressPrefix string = '10.20.0.0/16'

@description('Subnet prefix for the production Container Apps environment')
param acaProductionSubnetPrefix string = '10.20.0.0/23'

@description('Subnet prefix for the staging Container Apps environment')
param acaStagingSubnetPrefix string = '10.20.2.0/23'

@description('Subnet prefix for the production Foundry agent injection subnet')
param agentProductionSubnetPrefix string = '10.20.4.0/24'

@description('Subnet prefix for the staging Foundry agent injection subnet')
param agentStagingSubnetPrefix string = '10.20.5.0/24'

@description('Subnet prefix hosting every private endpoint in this resource group')
param privateEndpointSubnetPrefix string = '10.20.6.0/24'

var containerAppsDelegation = 'Microsoft.App/environments'

// Subnets are declared inline rather than as standalone child resources because
// this template is the single owner of the address space. Standalone subnet
// resources race against each other when two deployments touch one virtual
// network, which is the failure mode this file exists to avoid.
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-aca-production'
        properties: {
          addressPrefix: acaProductionSubnetPrefix
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: containerAppsDelegation
              }
            }
          ]
        }
      }
      {
        name: 'snet-aca-staging'
        properties: {
          addressPrefix: acaStagingSubnetPrefix
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: containerAppsDelegation
              }
            }
          ]
        }
      }
      {
        name: 'snet-agent-production'
        properties: {
          addressPrefix: agentProductionSubnetPrefix
          delegations: [
            {
              name: 'agent-delegation'
              properties: {
                serviceName: containerAppsDelegation
              }
            }
          ]
        }
      }
      {
        name: 'snet-agent-staging'
        properties: {
          addressPrefix: agentStagingSubnetPrefix
          delegations: [
            {
              name: 'agent-delegation'
              properties: {
                serviceName: containerAppsDelegation
              }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Linked here rather than alongside each private endpoint so that both the
// staging and production endpoints, and the agent subnets, resolve the same
// zone. Without the link the agent resolves the public address and the
// connection is refused by the account firewall.
resource cosmosPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource cosmosPrivateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cosmosPrivateDnsZone
  name: '${vnetName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output acaProductionSubnetId string = vnet.properties.subnets[0].id
output acaStagingSubnetId string = vnet.properties.subnets[1].id
output agentProductionSubnetId string = vnet.properties.subnets[2].id
output agentStagingSubnetId string = vnet.properties.subnets[3].id
output privateEndpointSubnetId string = vnet.properties.subnets[4].id
output cosmosPrivateDnsZoneId string = cosmosPrivateDnsZone.id
