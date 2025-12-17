# Standard Agent Setup for Azure AI Foundry

This directory contains infrastructure scripts and templates for configuring enterprise-ready standard agent setup with Bring Your Own (BYO) resources.

## Overview

Standard Agent Setup provides enterprise-grade data isolation by using your own Azure resources:

- **Azure Cosmos DB** for thread/conversation storage
- **Azure Storage** for file attachments
- **Azure AI Search** for vector stores
- **Azure Key Vault** for secrets management

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Azure AI Foundry Account                         │
│                    (fleet-agent-resource)                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Project (fleet-agent)                        │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │            Capability Host (Agents)                   │   │   │
│  │  │                                                       │   │   │
│  │  │  • Storage Connection → w7otstorage                   │   │   │
│  │  │  • Vector Store → w7otsearch                          │   │   │
│  │  │  • Thread Storage → cosmos-fleet                      │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Azure Storage  │  │  Azure AI Search │  │  Azure Cosmos DB │
│  (w7otstorage)  │  │  (w7otsearch)    │  │  (cosmos-fleet)  │
│                 │  │                  │  │                   │
│  • File storage │  │  • Vector stores │  │  • Thread storage │
│  • Attachments  │  │  • Embeddings    │  │  • Conversations  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Deployed Resources

### Existing BYO Resources

| Resource          | Type                   | Purpose                     |
| ----------------- | ---------------------- | --------------------------- |
| `cosmos-fleet`    | Cosmos DB (Serverless) | Thread/conversation storage |
| `w7otstorage`     | Storage Account        | File attachments            |
| `w7otsearch`      | AI Search (Standard)   | Vector stores               |
| `kv-fleet-agents` | Key Vault              | Secrets management          |

### Cosmos DB Containers

| Container                     | Partition Key | Purpose                |
| ----------------------------- | ------------- | ---------------------- |
| `thread-message-store`        | `/threadId`   | User thread messages   |
| `system-thread-message-store` | `/threadId`   | System thread messages |
| `agent-entity-store`          | `/agentId`    | Agent definitions      |

### Storage Containers

| Container           | Purpose                 |
| ------------------- | ----------------------- |
| `azureml-blobstore` | General ML blob storage |
| `agents-blobstore`  | Agent file attachments  |

### Connections

| Connection Name           | Category         | Target       |
| ------------------------- | ---------------- | ------------ |
| `w7otstorage6fafq2`       | Azure Storage    | w7otstorage  |
| `w7otsearch6fafq2`        | Cognitive Search | w7otsearch   |
| `cosmos-fleet-connection` | Cosmos DB        | cosmos-fleet |

## RBAC Role Assignments

The following roles are assigned to the project managed identity (`61aad581-af75-4fd1-834a-a1008676d402`):

### Cosmos DB

- `Cosmos DB Operator` - Resource management
- `Cosmos DB Built-in Data Contributor` - Read/write data

### Storage Account

- `Storage Account Contributor` - Resource management
- `Storage Blob Data Contributor` - Read/write blobs
- `Storage Blob Data Owner` - Full blob access

### AI Search

- `Search Index Data Contributor` - Index data operations
- `Search Service Contributor` - Service management

### Key Vault

- `Key Vault Secrets Officer` - Manage secrets

## Scripts

### deploy.sh

Initial deployment script that:

1. Verifies existing BYO resources
2. Creates Key Vault
3. Assigns RBAC roles
4. Creates Cosmos DB containers
5. Creates storage containers

```bash
./deploy.sh
```

### create-capability-host.sh

Creates the capability host with BYO connections:

1. Checks for existing capability hosts
2. Creates account-level capability host
3. Creates project-level capability host (if supported)

```bash
# Run after deploy.sh and after any previous capability host is fully deleted
./create-capability-host.sh
```

## Manual Steps (Azure Portal)

Some configurations may need to be done via Azure Portal:

1. **Project Capability Host**: If REST API doesn't support project-level capability hosts, configure in:
   - Navigate to: https://ai.azure.com/resource/projects/fleet-agent
   - Go to Settings → Agent → Configure Capability Host

2. **Developer Access**: Assign `Azure AI User` role to developers who need agent access

## Verification

Check capability host status:

```bash
az rest --method GET \
  --url "https://management.azure.com/subscriptions/10f3a1a0-7334-4df9-878b-ca03178af6f3/resourceGroups/rg-production/providers/Microsoft.CognitiveServices/accounts/fleet-agent-resource/capabilityHosts?api-version=2025-06-01"
```

Check connections:

```bash
az cognitiveservices account connection list \
  --name fleet-agent-resource \
  --resource-group rg-production
```

## Enterprise Features

✅ **Data Isolation**: All agent data stored in your BYO resources
✅ **RBAC Security**: Fine-grained access control via Azure AD
✅ **Soft Delete**: Key Vault configured with 90-day retention
✅ **Audit Logging**: Cosmos DB and Storage audit logs available
✅ **Regional Compliance**: All resources in Sweden Central
✅ **Serverless Cosmos**: Cost-efficient pay-per-use model

## Troubleshooting

### Capability Host in "Deleting" State

The capability host deletion includes deprovisioning Azure Container Apps Managed Environment, which can take 5-10 minutes. Wait for deletion to complete before creating a new one.

### Connection Errors

Ensure the managed identity has proper RBAC roles. Re-run `deploy.sh` to reassign roles.

### Cosmos DB 429 Errors

The serverless Cosmos DB auto-scales, but if you see rate limiting:

1. Check for hot partitions
2. Implement retry with exponential backoff in your application
3. Consider provisioned throughput for consistent high load

## Related Documentation

- [Standard Agent Setup](https://learn.microsoft.com/azure/ai-services/agents/how-to/standard-agent-setup)
- [Azure AI Foundry Projects](https://learn.microsoft.com/azure/ai-services/ai-studio/how-to/create-projects)
- [Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/sql/best-practice-dotnet)
