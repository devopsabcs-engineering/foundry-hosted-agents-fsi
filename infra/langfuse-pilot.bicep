@description('Standalone synthetic-data pilot only. Deployment requires separate cost and security approval.')
param location string = resourceGroup().location

@minLength(3)
@maxLength(30)
param name string = 'langfuse-synthetic-pilot'

@description('Operator public IPv4 address, without a CIDR suffix. SSH is restricted to this address as /32.')
@minLength(7)
@maxLength(15)
param operatorIpv4Address string

@description('Operator SSH public key. Never provide a private key.')
@minLength(80)
param sshPublicKey string

param adminUsername string = 'pilotadmin'

@allowed(['Standard_D4s_v5', 'Standard_D4s_v6'])
param vmSize string = 'Standard_D4s_v5'

var tags = {
  purpose: 'langfuse-synthetic-pilot'
  environment: 'disposable-nonproduction'
}
var cloudInit = replace(
  loadTextContent('langfuse-pilot/cloud-init.yaml'),
  '__COMPOSE_BASE64__',
  base64(loadTextContent('langfuse-pilot/docker-compose.yml'))
)

resource securityGroup 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${name}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [{
      name: 'operator-ssh-only'
      properties: {
        priority: 100
        direction: 'Inbound'
        access: 'Allow'
        protocol: 'Tcp'
        sourceAddressPrefix: '${operatorIpv4Address}/32'
        sourcePortRange: '*'
        destinationAddressPrefix: '*'
        destinationPortRange: '22'
      }
    }]
  }
}

resource network 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${name}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.90.0.0/24']
    }
    subnets: [{
      name: 'pilot'
      properties: {
        addressPrefix: '10.90.0.0/24'
        networkSecurityGroup: { id: securityGroup.id }
      }
    }]
  }
}

resource publicIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: '${name}-ip'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource networkInterface 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: '${name}-nic'
  location: location
  tags: tags
  properties: {
    ipConfigurations: [{
      name: 'primary'
      properties: {
        privateIPAllocationMethod: 'Dynamic'
        publicIPAddress: { id: publicIp.id }
        subnet: { id: network.properties.subnets[0].id }
      }
    }]
  }
}

resource virtualMachine 'Microsoft.Compute/virtualMachines@2024-11-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    hardwareProfile: { vmSize: vmSize }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: {
        secureBootEnabled: true
        vTpmEnabled: true
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        diskSizeGB: 128
        deleteOption: 'Detach'
        managedDisk: { storageAccountType: 'Premium_LRS' }
      }
    }
    osProfile: {
      computerName: name
      adminUsername: adminUsername
      customData: base64(cloudInit)
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        ssh: {
          publicKeys: [{
            path: '/home/${adminUsername}/.ssh/authorized_keys'
            keyData: sshPublicKey
          }]
        }
        patchSettings: {
          patchMode: 'AutomaticByPlatform'
          assessmentMode: 'AutomaticByPlatform'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [{ id: networkInterface.id }]
    }
    diagnosticsProfile: {
      bootDiagnostics: { enabled: true }
    }
  }
}

output virtualMachineName string = virtualMachine.name
output publicIpv4Address string = publicIp.properties.ipAddress
output sshTunnelCommand string = 'ssh -N -o ExitOnForwardFailure=yes -L 3000:127.0.0.1:3000 ${adminUsername}@${publicIp.properties.ipAddress}'
