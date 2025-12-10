// Standard Agent Setup for Azure AI Foundry - Enterprise Ready Configuration
// This template provisions the capability hosts and connections required for
// standard agent setup with BYO (Bring Your Own) resources

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the existing Azure AI Foundry account')
param foundryAccountName string = 'fleet-agent-resource'

@description('Name of the project')
param projectName string = 'fleet-agent'

@description('Resource ID of existing Cosmos DB account')
param cosmosDBResourceId string = '/subscriptions/10f3a1a0-7334-4df9-878b-ca03178af6f3/resourceGroups/rg-production/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-fleet'

@description('Resource ID of existing Storage account')
param storageAccountResourceId string = '/subscriptions/10f3a1a0-7334-4df9-878b-ca03178af6f3/resourceGroups/rg-production/providers/Microsoft.Storage/storageAccounts/w7otstorage'

@description('Resource ID of existing Azure AI Search service')
param aiSearchResourceId string = '/subscriptions/10f3a1a0-7334-4df9-878b-ca03178af6f3/resourceGroups/rg-production/providers/Microsoft.Search/searchServices/w7otsearch'

@description('Name for the Key Vault')
param keyVaultName string = 'kv-fleet-agents'

@description('Tags for resources')
param tags object = {
  environment: 'production'
  project: 'agentic-fleet'
  setup: 'standard-agent'
}

// Variables
var subscriptionId = subscription().subscriptionId
var resourceGroupName = resourceGroup().name
var cosmosDbAccountName = last(split(cosmosDBResourceId, '/'))
var storageAccountName = last(split(storageAccountResourceId, '/'))
var searchServiceName = last(split(aiSearchResourceId, '/'))

// Key Vault for Standard Setup (required for enterprise security)
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Reference existing Foundry Account
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

// Reference existing project
resource project 'Microsoft.CognitiveServices/accounts/projects@2024-10-01' existing = {
  name: projectName
  parent: foundryAccount
}

// Connection to Cosmos DB for thread storage
resource cosmosDbConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2024-10-01' = {
  name: 'cosmos-fleet-connection'
  parent: project
  properties: {
    category: 'CosmosDB'
    target: cosmosDBResourceId
    authType: 'ManagedIdentity'
    isSharedToAll: true
    metadata: {
      resourceId: cosmosDBResourceId
      databaseName: 'enterprise_memory'
    }
  }
}

// Connection to Storage Account for file storage
resource storageConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2024-10-01' = {
  name: 'storage-fleet-connection'
  parent: project
  properties: {
    category: 'AzureBlobStorage'
    target: 'https://${storageAccountName}.blob.${environment().suffixes.storage}/'
    authType: 'ManagedIdentity'
    isSharedToAll: true
    metadata: {
      resourceId: storageAccountResourceId
    }
  }
}

// Connection to Azure AI Search for vector stores
resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2024-10-01' = {
  name: 'search-fleet-connection'
  parent: project
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net/'
    authType: 'ManagedIdentity'
    isSharedToAll: true
    metadata: {
      resourceId: aiSearchResourceId
    }
  }
}

// Connection to Key Vault
resource keyVaultConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2024-10-01' = {
  name: 'keyvault-fleet-connection'
  parent: project
  properties: {
    category: 'AzureKeyVault'
    target: keyVault.properties.vaultUri
    authType: 'ManagedIdentity'
    isSharedToAll: true
    metadata: {
      resourceId: keyVault.id
    }
  }
}

// Account-level Capability Host for Agents
resource accountCapabilityHost 'Microsoft.CognitiveServices/accounts/capabilityHosts@2024-10-01' = {
  name: 'default'
  parent: foundryAccount
  properties: {
    capabilityHostKind: 'Agents'
  }
}

// Project-level Capability Host with BYO resources
resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2024-10-01' = {
  name: 'default'
  parent: project
  dependsOn: [
    accountCapabilityHost
    cosmosDbConnection
    storageConnection
    searchConnection
    keyVaultConnection
  ]
  properties: {
    capabilityHostKind: 'Agents'
    storageConnections: [
      storageConnection.name
    ]
    vectorStoreConnections: [
      searchConnection.name
    ]
    aiSearchConnections: [
      searchConnection.name
    ]
    cosmosDbConnections: [
      cosmosDbConnection.name
    ]
  }
}

// Outputs
output foundryAccountId string = foundryAccount.id
output projectId string = project.id
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
output cosmosDbConnectionName string = cosmosDbConnection.name
output storageConnectionName string = storageConnection.name
output searchConnectionName string = searchConnection.name
