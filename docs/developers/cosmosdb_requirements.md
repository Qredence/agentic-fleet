# Azure Cosmos DB NoSQL Modeling Session

## Application Overview

- **Domain**: AgenticFleet (Single-User / Developer Edition)
- **Key Entities**:
  - **Conversation**: A chat session between the user and the agent fleet.
  - **Message**: Individual messages within a conversation (User, Assistant, System).
  - **WorkflowRun**: The execution of a complex task triggered by a message.
  - **Event**: Granular steps within a workflow (Agent actions, Tool calls, Reasoning steps).
- **Business Context**:
  - The user runs the AgenticFleet locally or in a personal cloud environment.
  - The system uses FastAPI to expose endpoints for chat and workflow management.
  - Tracing is enabled via AI Toolkit, but the user wants a Cosmos DB schema to persist the core data (conversations, messages, events) similar to the tracing structure but for application state.
  - **Constraint**: "One user with its own cosmos database" - implies we don't need complex multi-tenant partitioning (like `tenantId`), but `userId` might still be useful for future-proofing or simply omitted if strictly single-user. I will assume a `userId` is present but cardinality is 1 for this specific deployment, or we can partition by `conversationId` / `workflowId` for better distribution even for a single user.
- **Scale**:
  - **Concurrent Users**: 1 (The developer/user).
  - **Volume**: Low (Personal usage).
  - **Data Size**:
    - Conversations: ~10-50 per day.
    - Messages: ~10-100 per conversation.
    - Events: ~50-500 per workflow run.
- **Geographic Distribution**: Single Region.

## Access Patterns Analysis

| Pattern # | Description                                  | RPS (Peak/Avg) | Type  | Attributes Needed                   | Key Requirements                   | Design Considerations                        | Status |
| --------- | -------------------------------------------- | -------------- | ----- | ----------------------------------- | ---------------------------------- | -------------------------------------------- | ------ |
| 1         | Create a new conversation                    | <1             | Write | title, created_at                   | Low latency                        | Simple point write                           | ⏳     |
| 2         | List all conversations (history)             | <1             | Read  | id, title, created_at               | Sort by date desc                  | Query by type/user                           | ⏳     |
| 3         | Get conversation details (with messages)     | <1             | Read  | id, messages                        | Low latency                        | Single partition read preferred              | ⏳     |
| 4         | Add a message to a conversation              | <1             | Write | conversation_id, content, role      | Append-only                        | Update conversation document or add new doc? | ⏳     |
| 5         | Create a workflow run (triggered by message) | <1             | Write | conversation_id, message_id, status | Link to msg                        |                                              | ⏳     |
| 6         | Log an event (tracing/execution step)        | ~10-50         | Write | run_id, type, content, timestamp    | High write freq relative to others | Append to run or separate docs?              | ⏳     |
| 7         | Get workflow run details (with events)       | <1             | Read  | run_id, events                      |                                    |                                              | ⏳     |

## Entity Relationships Deep Dive

- **Conversation (1) -> Messages (M)**: A conversation contains multiple messages.
- **Message (1) -> WorkflowRun (0..1)**: A message might trigger a workflow run (e.g., "Research this").
- **WorkflowRun (1) -> Events (M)**: A run generates many events (reasoning, tool calls).

## Enhanced Aggregate Analysis

### Conversation + Messages

- **Access Correlation**: High. When opening a chat, we usually want the messages.
- **Size Constraints**: A conversation could grow long. 100 messages \* 1KB = 100KB. Well within 2MB limit.
- **Decision**: **Single Document Aggregate** (Conversation document contains list of Messages) OR **Multi-Document Container** (Conversation metadata doc + Message docs).
  - Given "tracing" mention, messages might be numerous.
  - However, for a "chat" app, usually we load the last N messages.
  - **Refinement**: If we use a single document, we hit 2MB limit eventually. If we use separate documents, we need a query.
  - **Decision**: Let's start with **Multi-Document Container** (Partition Key = `conversationId`).
    - `Conversation` doc (metadata).
    - `Message` docs (partitioned by `conversationId`).
    - This allows unbounded conversation length.

### WorkflowRun + Events

- **Access Correlation**: High. Debugging a run requires seeing events.
- **Size Constraints**: Events can be verbose (tool outputs). 500 events \* 2KB = 1MB. Close to limit.
- **Decision**: **Multi-Document Container** (Partition Key = `runId` or `workflowId`).
  - `WorkflowRun` doc (metadata, status).
  - `Event` docs (partitioned by `runId`).

## Container Consolidation Analysis

- Can we put Conversations and WorkflowRuns in the same container?
  - **Option A**: `Chat` container (Conversations + Messages). `Workflows` container (Runs + Events).
  - **Option B**: Single `Fleet` container.
    - PK strategy?
    - If PK=`conversationId` for chat, and PK=`runId` for workflows.
    - A workflow is linked to a conversation?
    - If we want to query "all workflows for a conversation", having them in the same partition (`conversationId`) would be nice.
    - But a workflow might be large.
  - **Decision**: Separate containers seems cleaner for "Events" vs "Chat".
    - `Conversations` container (PK: `conversationId`).
    - `Workflows` container (PK: `workflowId`).
    - **Link**: Message has `workflowId`. Workflow has `conversationId`.

## Design Considerations

- **Single User**: We don't need `userId` in the Partition Key for distribution, but might include it as a property.
- **Tracing**: The user mentioned "tracing with AI toolkit". This usually implies a structure of `Session -> Run -> Span/Event`.
  - `Session` ~= `Conversation`.
  - `Run` ~= `WorkflowRun`.
  - `Span` ~= `Event`.
- **FastAPI Models**: The `Conversation` model has `messages: list[Message]`. This implies the API expects nested structure. We can construct this from query results.

## Validation Checklist

- [ ] Application domain and scale documented ⏳
- [ ] All entities and relationships mapped ⏳
- [ ] Aggregate boundaries identified ⏳
- [ ] Consolidation analysis ⏳
