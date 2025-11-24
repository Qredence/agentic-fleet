# Azure Cosmos DB NoSQL Data Model

## Design Philosophy & Approach

The design focuses on a **single-user / developer-centric** deployment of AgenticFleet, prioritizing **simplicity** and **observability** (tracing).
We use **Multi-Document Containers** to group related entities (Conversations + Messages, Workflows + Events) within the same logical partition. This allows for efficient single-partition queries to retrieve full context (e.g., "Get conversation with all messages" or "Get workflow run with all trace events") while avoiding the 2MB document size limit for long-running sessions.

## Aggregate Design Decisions

- **Conversation Aggregate**: Grouped by `conversationId`. A conversation is the natural unit of interaction. Messages are appended to this aggregate.
- **Workflow Aggregate**: Grouped by `workflowId`. A workflow run is a distinct execution unit. Events (traces) are appended to this aggregate.

## Container Designs

### `Conversations` Container

```json
[
  {
    "id": "conv_123",
    "partitionKey": "conv_123",
    "type": "conversation",
    "title": "Research AI Trends",
    "created_at": 1715432000,
    "updated_at": 1715432500,
    "userId": "user_1"
  },
  {
    "id": "msg_456",
    "partitionKey": "conv_123",
    "type": "message",
    "conversation_id": "conv_123",
    "role": "user",
    "content": "What are the trends?",
    "created_at": 1715432100
  },
  {
    "id": "msg_457",
    "partitionKey": "conv_123",
    "type": "message",
    "conversation_id": "conv_123",
    "role": "assistant",
    "content": "Here are the trends...",
    "created_at": 1715432200
  }
]
```

- **Purpose**: Stores chat history and metadata.
- **Aggregate Boundary**: All messages for a single conversation.
- **Partition Key**: `/conversationId` (mapped to `partitionKey` property in docs).
  - **Justification**: Queries are almost always scoped to a conversation. High cardinality (one partition per conversation).
- **Document Types**:
  - `conversation`: Metadata (title, timestamps).
  - `message`: Individual chat messages.
- **Attributes**:
  - `id`: Unique ID (UUID).
  - `partitionKey`: Same as `conversationId`.
  - `type`: Discriminator (`conversation` | `message`).
  - `content`, `role`: Message details.
- **Access Patterns Served**: #1, #3, #4.
- **Throughput Planning**: Low (400 RU/s manual or Autoscale).
- **Consistency Level**: Session.

### `Workflows` Container

```json
[
  {
    "id": "run_789",
    "partitionKey": "run_789",
    "type": "run",
    "status": "completed",
    "task": "Research AI Trends",
    "created_at": 1715432200,
    "conversation_id": "conv_123",
    "message_id": "msg_456"
  },
  {
    "id": "evt_001",
    "partitionKey": "run_789",
    "type": "event",
    "event_type": "tool_call",
    "agent": "researcher",
    "content": "Searching web...",
    "timestamp": 1715432205
  }
]
```

- **Purpose**: Stores execution traces and workflow status.
- **Aggregate Boundary**: All events for a single workflow run.
- **Partition Key**: `/workflowId` (mapped to `partitionKey` property).
  - **Justification**: Tracing queries focus on a specific run.
- **Document Types**:
  - `run`: Workflow metadata.
  - `event`: Granular execution steps.
- **Attributes**:
  - `id`: Unique ID.
  - `partitionKey`: Same as `workflowId`.
  - `type`: Discriminator (`run` | `event`).
  - `event_type`, `agent`, `content`: Trace details.
- **Access Patterns Served**: #5, #6, #7.
- **Throughput Planning**: Low/Medium (Autoscale if tracing is verbose).

### Indexing Strategy

- **Indexing Policy**: Automatic for most fields.
- **Excluded Paths**:
  - `/content/*` (Large text bodies in messages/events might not need full indexing if we only search by metadata/time).
- **Composite Indexes**:
  - `partitionKey` ASC, `created_at` DESC (For ordering messages/events).

## Access Pattern Mapping

| Pattern | Description         | Containers/Indexes | Cosmos DB Operations                                                           | Implementation Notes                                          |
| ------- | ------------------- | ------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| 1       | Create conversation | Conversations      | CreateItem (type=conversation)                                                 |                                                               |
| 2       | List conversations  | Conversations      | Query `SELECT * FROM c WHERE c.type='conversation' ORDER BY c.created_at DESC` | Cross-partition query (acceptable for single user low volume) |
| 3       | Get conversation    | Conversations      | Query `SELECT * FROM c WHERE c.partitionKey=@id`                               | Single partition, retrieves metadata + messages               |
| 4       | Add message         | Conversations      | CreateItem (type=message)                                                      |                                                               |
| 5       | Create workflow     | Workflows          | CreateItem (type=run)                                                          |                                                               |
| 6       | Log event           | Workflows          | CreateItem (type=event)                                                        | High frequency writes                                         |
| 7       | Get workflow trace  | Workflows          | Query `SELECT * FROM c WHERE c.partitionKey=@id`                               | Single partition                                              |

## Hot Partition Analysis

- **Conversations**: Evenly distributed by `conversationId`. No hot partition risk for single user.
- **Workflows**: Evenly distributed by `workflowId`.

## Trade-offs and Optimizations

- **Multi-Document vs Single Document**: Chosen **Multi-Document** for both containers to avoid 2MB limit. Traces and Chat logs can be verbose.
- **Cross-Partition Queries**: Listing all conversations (Pattern #2) is cross-partition. For a single user with <1000 conversations, this is negligible cost/latency.
- **Tracing Fidelity**: Storing every event as a document allows granular querying and analysis without loading the full run blob.

## Global Distribution Strategy

- **Single Region**: Sufficient for local developer usage.
- **Consistency**: Session consistency ensures "read your own writes" (e.g., post message, see it immediately).

## Validation Results

- [x] Reasoned step-by-step through design decisions ✅
- [x] Aggregate boundaries clearly defined ✅
- [x] Every access pattern solved ✅
- [x] Unnecessary cross-partition queries eliminated (except list) ✅
- [x] All containers and indexes documented ✅
- [x] Hot partition analysis completed ✅
- [x] Trade-offs explicitly documented ✅

## Provisioning

A Python script is provided to provision the database and containers automatically.

### Prerequisites

- Python 3.12+
- `azure-cosmos` and `azure-identity` packages (installed via `uv sync` or `pip install azure-cosmos azure-identity`)
- Azure Cosmos DB account created in Azure Portal

### Environment Variables

Set the following environment variables in your `.env` file or shell:

```bash
export AZURE_COSMOS_ENDPOINT="https://<your-account>.documents.azure.com:443/"
export AZURE_COSMOS_KEY="<your-primary-key>" # Optional if using Managed Identity
export AZURE_COSMOS_DATABASE="agentic-fleet" # Defaults to agentic-fleet
```

### Running the Script

```bash
python scripts/provision_cosmos.py
```

This will create:

1. Database `agentic-fleet`
2. Container `Conversations` (PK: `/conversationId`)
3. Container `Workflows` (PK: `/workflowId`)
