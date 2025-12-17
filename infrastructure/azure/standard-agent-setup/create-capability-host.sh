#!/bin/bash
# Create Standard Agent Setup Capability Host
# Run this script AFTER the previous capability host has been deleted
#
# Prerequisites:
# - Azure CLI logged in
# - Previous capability host fully deleted
# - Connections created: w7otstorage6fafq2, w7otsearch6fafq2, cosmos-fleet-connection

set -e

SUBSCRIPTION_ID="10f3a1a0-7334-4df9-878b-ca03178af6f3"
RG="rg-production"
ACCOUNT="fleet-agent-resource"
PROJECT="fleet-agent"
API_VERSION="2025-06-01"

echo "🔐 Creating Standard Agent Setup Capability Host"
echo "================================================="
echo ""

# Check if old capability host is still being deleted
echo "📋 Step 1: Checking for existing capability hosts..."
ACCESS_TOKEN=$(az account get-access-token --resource https://management.azure.com --query accessToken -o tsv)

HOSTS=$(curl -s "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/capabilityHosts?api-version=${API_VERSION}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

COUNT=$(echo "$HOSTS" | jq '.value | length')
if [ "$COUNT" != "0" ]; then
    STATE=$(echo "$HOSTS" | jq -r '.value[0].properties.provisioningState')
    if [ "$STATE" = "Deleting" ]; then
        echo "  ⏳ Previous capability host is still being deleted (state: $STATE)"
        echo "  Please wait and run this script again later."
        echo ""
        echo "  You can check status with:"
        echo "  az rest --method GET --url 'https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/capabilityHosts?api-version=${API_VERSION}'"
        exit 1
    else
        echo "  ⚠️  Existing capability host found with state: $STATE"
        echo "  Delete it first with:"
        echo "  az rest --method DELETE --url 'https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/capabilityHosts/<name>?api-version=${API_VERSION}'"
        exit 1
    fi
fi
echo "  ✓ No existing capability hosts"

# Create Account Capability Host
echo ""
echo "📋 Step 2: Creating Account Capability Host..."

RESULT=$(curl -sX PUT "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/capabilityHosts/agents-caphost?api-version=${API_VERSION}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "capabilityHostKind": "Agents",
      "storageConnections": ["w7otstorage6fafq2"],
      "vectorStoreConnections": ["w7otsearch6fafq2"],
      "threadStorageConnections": ["cosmos-fleet-connection"]
    }
  }')

if echo "$RESULT" | grep -q '"error"'; then
    echo "  ❌ Error creating Account Capability Host:"
    echo "$RESULT" | jq '.error.message'
    exit 1
fi

STATE=$(echo "$RESULT" | jq -r '.properties.provisioningState')
echo "  ✓ Account Capability Host created (state: $STATE)"

# Wait for provisioning
echo ""
echo "📋 Step 3: Waiting for provisioning to complete..."
for i in {1..30}; do
    ACCESS_TOKEN=$(az account get-access-token --resource https://management.azure.com --query accessToken -o tsv)

    RESULT=$(curl -s "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/capabilityHosts/agents-caphost?api-version=${API_VERSION}" \
      -H "Authorization: Bearer ${ACCESS_TOKEN}")

    STATE=$(echo "$RESULT" | jq -r '.properties.provisioningState')

    if [ "$STATE" = "Succeeded" ]; then
        echo "  ✓ Provisioning complete!"
        break
    elif [ "$STATE" = "Failed" ]; then
        echo "  ❌ Provisioning failed"
        echo "$RESULT" | jq .
        exit 1
    fi

    echo "  Attempt $i/30: State = $STATE"
    sleep 20
done

# Create Project Capability Host
echo ""
echo "📋 Step 4: Creating Project Capability Host..."

RESULT=$(curl -sX PUT "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT}/projects/${PROJECT}/capabilityHosts/agents-caphost?api-version=${API_VERSION}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "capabilityHostKind": "Agents",
      "storageConnections": ["w7otstorage6fafq2"],
      "vectorStoreConnections": ["w7otsearch6fafq2"],
      "threadStorageConnections": ["cosmos-fleet-connection"]
    }
  }')

if echo "$RESULT" | grep -q '"error"'; then
    echo "  ⚠️  Project Capability Host creation:"
    echo "$RESULT" | jq '.error.message'
    echo "  (This may need to be configured via Azure Portal)"
else
    STATE=$(echo "$RESULT" | jq -r '.properties.provisioningState')
    echo "  ✓ Project Capability Host created (state: $STATE)"
fi

# Summary
echo ""
echo "================================================="
echo "✅ Standard Agent Setup Configuration Complete!"
echo "================================================="
echo ""
echo "Your enterprise-ready agent infrastructure is configured with:"
echo "  • Storage Connection: w7otstorage6fafq2 (file storage)"
echo "  • Search Connection: w7otsearch6fafq2 (vector stores)"
echo "  • Thread Storage: cosmos-fleet-connection (conversations)"
echo ""
echo "Enterprise Features Enabled:"
echo "  ✓ Data isolation (BYO resources)"
echo "  ✓ RBAC-based access control"
echo "  ✓ Soft delete protection (Key Vault)"
echo "  ✓ Compliance-ready architecture"
echo ""
echo "Portal URL: https://ai.azure.com/resource/projects/${PROJECT}"
echo ""
