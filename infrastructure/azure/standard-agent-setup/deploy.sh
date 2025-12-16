#!/bin/bash
# Standard Agent Setup Deployment Script for Azure AI Foundry
# This script provisions enterprise-ready agent infrastructure with BYO resources

set -e

# Parameterize subscription ID: from env var or first argument
if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
  SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID"
elif [ -n "$1" ]; then
  SUBSCRIPTION_ID="$1"
else
  echo "❌ ERROR: Azure subscription ID not set."
  echo "Please set the AZURE_SUBSCRIPTION_ID environment variable or pass as the first argument:"
  echo "  export AZURE_SUBSCRIPTION_ID=<your-subscription-id>"
  echo "  ./deploy.sh <subscription-id>"
  exit 1
fi
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

# Track role assignment failures
ROLE_ASSIGNMENT_FAILURES=0

# Function to safely assign a role (idempotent with proper error handling)
assign_role() {
  local role_name="$1"
  local scope="$2"
  local assignee="$3"
  local display_name="$4"

  echo "  Assigning ${display_name}..."

  # Check if role assignment already exists
  existing=$(az role assignment list \
    --assignee "${assignee}" \
    --role "${role_name}" \
    --scope "${scope}" \
    --query "[0].id" \
    -o tsv 2>/dev/null)

  if [ -n "$existing" ]; then
    echo "    ✓ Role already assigned"
    return 0
  fi

  # Create the role assignment
  local error_output
  error_output=$(az role assignment create \
    --assignee-object-id "${assignee}" \
    --assignee-principal-type ServicePrincipal \
    --role "${role_name}" \
    --scope "${scope}" \
    -o json 2>&1)

  local exit_code=$?

  if [ $exit_code -ne 0 ]; then
    echo "    ❌ Failed to assign role '${role_name}'"
    echo "    Error: ${error_output}"

    # Check for common error patterns and provide actionable guidance
    if echo "$error_output" | grep -qi "does not exist in the directory"; then
      echo "    → The principal ID '${assignee}' was not found. Verify the managed identity exists."
    elif echo "$error_output" | grep -qi "authorization"; then
      echo "    → Insufficient permissions. Ensure you have Owner or User Access Administrator role on the scope."
    elif echo "$error_output" | grep -qi "InvalidPrincipalId"; then
      echo "    → Invalid principal ID format. Check PROJECT_PRINCIPAL_ID value."
    fi

    ROLE_ASSIGNMENT_FAILURES=$((ROLE_ASSIGNMENT_FAILURES + 1))
    return 1
  fi

  echo "    ✓ Role assigned successfully"
  return 0
}

# Cosmos DB Operator (account level)
assign_role "Cosmos DB Operator" "${COSMOS_DB_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Cosmos DB Operator"

# Storage Account Contributor
assign_role "Storage Account Contributor" "${STORAGE_ACCOUNT_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Storage Account Contributor"

# Storage Blob Data Contributor
assign_role "Storage Blob Data Contributor" "${STORAGE_ACCOUNT_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Storage Blob Data Contributor"

# Storage Blob Data Owner
assign_role "Storage Blob Data Owner" "${STORAGE_ACCOUNT_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Storage Blob Data Owner"

# Search Index Data Contributor
assign_role "Search Index Data Contributor" "${AI_SEARCH_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Search Index Data Contributor"

# Search Service Contributor
assign_role "Search Service Contributor" "${AI_SEARCH_RESOURCE_ID}" "${PROJECT_PRINCIPAL_ID}" "Search Service Contributor"

# Key Vault Secrets Officer
assign_role "Key Vault Secrets Officer" "${KEY_VAULT_ID}" "${PROJECT_PRINCIPAL_ID}" "Key Vault Secrets Officer"

# Check for failures
if [ $ROLE_ASSIGNMENT_FAILURES -gt 0 ]; then
  echo "  ⚠️  ${ROLE_ASSIGNMENT_FAILURES} role assignment(s) failed"
  echo "  Review the errors above and ensure:"
  echo "    1. The principal ID ${PROJECT_PRINCIPAL_ID} is valid"
  echo "    2. You have sufficient permissions (Owner or User Access Administrator)"
  echo "    3. The target resources exist and are accessible"
  exit 1
fi

echo "  ✓ All RBAC roles assigned successfully"

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
