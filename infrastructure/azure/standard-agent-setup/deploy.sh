#!/bin/bash
# Standard Agent Setup Deployment Script for Azure AI Foundry
# This script provisions enterprise-ready agent infrastructure with BYO resources

set -e

# Configuration
SUBSCRIPTION_ID="10f3a1a0-7334-4df9-878b-ca03178af6f3"
RESOURCE_GROUP="rg-production"
LOCATION="swedencentral"
FOUNDRY_ACCOUNT="fleet-agent-resource"
PROJECT_NAME="fleet-agent"

# BYO Resource IDs (existing resources)
COSMOS_DB_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-fleet"
STORAGE_ACCOUNT_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/w7otstorage"
AI_SEARCH_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Search/searchServices/w7otsearch"

# Key Vault Name (will be created)
KEY_VAULT_NAME="kv-fleet-agents"

echo "🚀 Standard Agent Setup for Azure AI Foundry"
echo "============================================"
echo ""
echo "Configuration:"
echo "  Subscription: ${SUBSCRIPTION_ID}"
echo "  Resource Group: ${RESOURCE_GROUP}"
echo "  Location: ${LOCATION}"
echo "  Foundry Account: ${FOUNDRY_ACCOUNT}"
echo "  Project: ${PROJECT_NAME}"
echo ""

# Step 1: Set subscription context
echo "📋 Step 1: Setting subscription context..."
az account set --subscription "${SUBSCRIPTION_ID}"

# Step 2: Verify existing resources
echo "📋 Step 2: Verifying existing resources..."

echo "  ✓ Checking Cosmos DB..."
az cosmosdb show --name "cosmos-fleet" --resource-group "${RESOURCE_GROUP}" --query "name" -o tsv > /dev/null

echo "  ✓ Checking Storage Account..."
az storage account show --name "w7otstorage" --resource-group "${RESOURCE_GROUP}" --query "name" -o tsv > /dev/null

echo "  ✓ Checking AI Search..."
az search service show --name "w7otsearch" --resource-group "${RESOURCE_GROUP}" --query "name" -o tsv > /dev/null

echo "  ✓ Checking Foundry Account..."
az cognitiveservices account show --name "${FOUNDRY_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" --query "name" -o tsv > /dev/null

# Step 3: Get Project Managed Identity
echo "📋 Step 3: Getting project managed identity..."
PROJECT_PRINCIPAL_ID=$(az cognitiveservices account show \
  --name "${FOUNDRY_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "identity.principalId" -o tsv 2>/dev/null || echo "")

if [ -z "$PROJECT_PRINCIPAL_ID" ]; then
  echo "  ⚠️  Managed identity not found. Enabling system-assigned identity..."
  az cognitiveservices account identity assign \
    --name "${FOUNDRY_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP}"

  PROJECT_PRINCIPAL_ID=$(az cognitiveservices account show \
    --name "${FOUNDRY_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "identity.principalId" -o tsv)
fi
echo "  ✓ Project Principal ID: ${PROJECT_PRINCIPAL_ID}"

# Step 4: Create Key Vault (if not exists)
echo "📋 Step 4: Creating Key Vault..."
if az keyvault show --name "${KEY_VAULT_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
  echo "  ✓ Key Vault already exists"
else
  az keyvault create \
    --name "${KEY_VAULT_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --enable-rbac-authorization \
    --retention-days 90 \
    --enable-purge-protection
  echo "  ✓ Key Vault created"
fi

KEY_VAULT_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}"

# Step 5: Assign RBAC roles
echo "📋 Step 5: Assigning RBAC roles..."

# Cosmos DB Operator (account level)
echo "  Assigning Cosmos DB Operator..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Cosmos DB Operator" \
  --scope "${COSMOS_DB_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Storage Account Contributor
echo "  Assigning Storage Account Contributor..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Account Contributor" \
  --scope "${STORAGE_ACCOUNT_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Storage Blob Data Contributor
echo "  Assigning Storage Blob Data Contributor..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "${STORAGE_ACCOUNT_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Storage Blob Data Owner
echo "  Assigning Storage Blob Data Owner..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Owner" \
  --scope "${STORAGE_ACCOUNT_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Search Index Data Contributor
echo "  Assigning Search Index Data Contributor..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Search Index Data Contributor" \
  --scope "${AI_SEARCH_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Search Service Contributor
echo "  Assigning Search Service Contributor..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Search Service Contributor" \
  --scope "${AI_SEARCH_RESOURCE_ID}" \
  2>/dev/null || echo "  (role may already exist)"

# Key Vault Secrets Officer
echo "  Assigning Key Vault Secrets Officer..."
az role assignment create \
  --assignee-object-id "${PROJECT_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets Officer" \
  --scope "${KEY_VAULT_ID}" \
  2>/dev/null || echo "  (role may already exist)"

echo "  ✓ RBAC roles assigned"

# Step 6: Create Cosmos DB database and containers (if not exists)
echo "📋 Step 6: Setting up Cosmos DB containers for agent storage..."

# Create database
echo "  Creating database 'enterprise_memory'..."
az cosmosdb sql database create \
  --account-name "cosmos-fleet" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "enterprise_memory" \
  2>/dev/null || echo "  (database may already exist)"

# Create containers with required throughput
echo "  Creating container 'thread-message-store'..."
az cosmosdb sql container create \
  --account-name "cosmos-fleet" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "enterprise_memory" \
  --name "thread-message-store" \
  --partition-key-path "/threadId" \
  2>/dev/null || echo "  (container may already exist)"

echo "  Creating container 'system-thread-message-store'..."
az cosmosdb sql container create \
  --account-name "cosmos-fleet" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "enterprise_memory" \
  --name "system-thread-message-store" \
  --partition-key-path "/threadId" \
  2>/dev/null || echo "  (container may already exist)"

echo "  Creating container 'agent-entity-store'..."
az cosmosdb sql container create \
  --account-name "cosmos-fleet" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "enterprise_memory" \
  --name "agent-entity-store" \
  --partition-key-path "/agentId" \
  2>/dev/null || echo "  (container may already exist)"

echo "  ✓ Cosmos DB containers ready"

# Step 7: Assign Cosmos DB SQL Role (Data Contributor at database level)
echo "📋 Step 7: Assigning Cosmos DB SQL role..."
COSMOS_DB_DATA_CONTRIBUTOR_ROLE_ID="00000000-0000-0000-0000-000000000002"

az cosmosdb sql role assignment create \
  --account-name "cosmos-fleet" \
  --resource-group "${RESOURCE_GROUP}" \
  --scope "/dbs/enterprise_memory" \
  --principal-id "${PROJECT_PRINCIPAL_ID}" \
  --role-definition-id "${COSMOS_DB_DATA_CONTRIBUTOR_ROLE_ID}" \
  2>/dev/null || echo "  (SQL role may already exist)"

echo "  ✓ Cosmos DB SQL role assigned"

# Step 8: Create storage containers for agents
echo "📋 Step 8: Creating storage containers..."
STORAGE_KEY=$(az storage account keys list \
  --account-name "w7otstorage" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[0].value" -o tsv)

# Get workspace ID (using Foundry account internal ID as proxy)
WORKSPACE_ID=$(az cognitiveservices account show \
  --name "${FOUNDRY_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "properties.internalId" -o tsv)

echo "  Creating blobstore container..."
az storage container create \
  --name "${WORKSPACE_ID}-azureml-blobstore" \
  --account-name "w7otstorage" \
  --account-key "${STORAGE_KEY}" \
  2>/dev/null || echo "  (container may already exist)"

echo "  Creating agents-blobstore container..."
az storage container create \
  --name "${WORKSPACE_ID}-agents-blobstore" \
  --account-name "w7otstorage" \
  --account-key "${STORAGE_KEY}" \
  2>/dev/null || echo "  (container may already exist)"

echo "  ✓ Storage containers ready"

echo ""
echo "============================================"
echo "✅ Standard Agent Setup Complete!"
echo "============================================"
echo ""
echo "Your enterprise-ready agent infrastructure is configured with:"
echo "  • Cosmos DB: cosmos-fleet (thread storage)"
echo "  • Storage: w7otstorage (file storage)"
echo "  • AI Search: w7otsearch (vector stores)"
echo "  • Key Vault: ${KEY_VAULT_NAME} (secrets)"
echo ""
echo "Next Steps:"
echo "  1. Configure capability hosts via Azure Portal or REST API"
echo "  2. Create project connections in the Foundry portal"
echo "  3. Assign 'Azure AI User' role to developers who need agent access"
echo ""
echo "Portal URL: https://ai.azure.com/resource/projects/${PROJECT_NAME}"
