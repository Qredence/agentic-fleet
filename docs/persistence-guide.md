# SQLite Conversation Persistence

## Overview

The persistence layer provides SQLite-backed storage for conversations, messages, events, ledger snapshots, and reasoning traces. It implements per-conversation event sequencing, automatic summarization, structured reasoning storage, and **conversation memory** for context retention across messages.

## Key Features

- **Conversation Memory**: Automatic history injection into workflows for context-aware responses
- **Per-Conversation Sequencing**: Monotonic counters ensure total event ordering
- **Automatic Summarization**: LLM-based history compression when threshold reached
- **Structured Reasoning**: Separate storage for reasoning traces with metadata
- **Ledger Snapshots**: Task progress tracking across workflow phases
- **Event Replay**: Resume workflows from any sequence point

## Architecture

### Components

- **Schema (`schema.py`)**: SQL table definitions with foreign key constraints
- **Database (`database.py`)**: Connection manager with initialization
- **Repositories**: Data access layer for each entity type
- **Service (`service.py`)**: High-level API integrating all repositories
- **Summarization (`summarization.py`)**: Automatic conversation history compression
- **Settings (`settings.py`)**: Configuration from environment variables

### Database Schema

```
conversations
├── id (PK)
├── workflow_id
├── next_sequence (atomic counter)
├── created_at
├── updated_at
└── metadata_json

messages
├── id (PK)
├── conversation_id (FK)
├── sequence (ordered)
├── role
├── content
├── reasoning
├── agent_id
└── created_at

events
├── id (PK)
├── conversation_id (FK)
├── sequence (ordered)
├── event_type
├── event_data_json
└── created_at

ledger_snapshots
├── id (PK)
├── conversation_id (FK)
├── sequence (ordered)
├── task_id
├── goal
├── status
├── agent_id
├── snapshot_json
└── created_at

reasoning_traces
├── id (PK)
├── conversation_id (FK)
├── message_id (FK)
├── reasoning_text
├── effort
├── verbosity
├── model
├── metadata_json
└── created_at
```

## Features

### 1. Per-Conversation Event Sequencing

Every conversation maintains a monotonic sequence counter stored in the `next_sequence` field. All messages and events receive sequence numbers via atomic `UPDATE...RETURNING` operations:

```python
async def get_next_sequence(self, conversation_id: str) -> int:
    """Atomically allocate next sequence number."""
    async with self.db.execute(
        """
        UPDATE conversations
        SET next_sequence = next_sequence + 1, updated_at = ?
        WHERE id = ?
        RETURNING next_sequence
        """,
        (time.time(), conversation_id),
    ) as cursor:
        row = await cursor.fetchone()
        await self.db.commit()
        return row[0] - 1  # Return pre-increment value
```

**Benefits:**

- Total ordering of all conversation activities
- Safe concurrent access from multiple processes
- Enable event replay and resume-from-sequence
- Audit trail with guaranteed ordering

### 2. Ledger Injection

Task ledger snapshots are stored with sequence numbers, allowing reconstruction of workflow state at any point:

```python
await service.add_ledger_snapshot(
    conversation_id=conv_id,
    task_id="task-1",
    goal="Complete implementation",
    status="in_progress",
    snapshot_data={
        "progress": 75,
        "subtasks": [...],
    },
)
```

The `get_ledger_state()` method returns the latest snapshot for each task_id, providing current workflow state without replaying all events.

### 3. Reasoning Trace Storage

Reasoning traces are stored separately from messages with structured metadata:

```python
await reasoning_repo.add(
    conversation_id=conv_id,
    message_id=msg_id,
    reasoning_text="Detailed reasoning trace...",
    effort="high",
    verbosity="verbose",
    model="gpt-5-mini",
    metadata={"tokens": 1000, "duration_ms": 2500},
)
```

**Features:**

- Preserved across summarization (messages may be deleted, reasoning remains)
- Queryable by conversation or message
- Metadata for analysis (effort level, token counts, timing)
- Supports audit and debugging

### 4. Automatic Summarization

When message count exceeds threshold, oldest messages are automatically summarized:

```python
# Configure threshold
settings = PersistenceSettings()
settings.summary_threshold = 20  # Trigger at 20 messages
settings.summary_keep_recent = 6  # Preserve last 6 messages

# Summarization runs automatically on assistant messages
await service.add_message(
    conversation_id=conv_id,
    role="assistant",
    content="Response...",
)
# If threshold exceeded, summarization triggers
```

**Process:**

1. Check message count after each assistant response
2. If over threshold, select oldest messages (excluding recent N)
3. Generate LLM summary (or fallback summary if no client)
4. Create system message with summary
5. Delete summarized messages
6. Reasoning traces and ledger snapshots are preserved

**Summary Message Format:**

```markdown
**Conversation Summary**

[LLM-generated summary of key facts, decisions, and action items]

_Summarized 14 messages._
```

## Usage

### Basic Setup

```python
from agentic_fleet.persistence import (
    ConversationPersistenceService,
    DatabaseManager,
    PersistenceSettings,
    get_database_manager,
)
from openai import AsyncOpenAI

# Initialize database
db_manager = get_database_manager("var/agenticfleet/conversations.db")

# Configure settings
settings = PersistenceSettings()
settings.summary_threshold = 20

# Create service with optional OpenAI client for summarization
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
service = ConversationPersistenceService(db_manager, settings, openai_client)
```

### Creating Conversations

```python
conv_id = await service.create_conversation(
    workflow_id="magentic-fleet",
    metadata={"user_id": "user123", "session": "xyz"},
)
```

### Adding Messages

```python
# User message
await service.add_message(
    conversation_id=conv_id,
    role="user",
    content="What is the weather today?",
)

# Assistant response with reasoning
await service.add_message(
    conversation_id=conv_id,
    role="assistant",
    content="The weather is sunny with temperatures around 75°F.",
    reasoning="Retrieved from weather API for user location",
    agent_id="weather-agent",
)
```

### Recording Events

```python
# Workflow events
await service.add_event(
    conversation_id=conv_id,
    event_type="workflow.start",
    event_data={"workflow_id": "magentic-fleet"},
)

await service.add_event(
    conversation_id=conv_id,
    event_type="agent.message.complete",
    event_data={"agent_id": "planner", "status": "completed"},
)
```

### Ledger Snapshots

```python
# Record task progress
await service.add_ledger_snapshot(
    conversation_id=conv_id,
    task_id="data-analysis",
    goal="Analyze user data",
    status="in_progress",
    snapshot_data={
        "progress": 60,
        "subtasks_complete": 3,
        "subtasks_total": 5,
    },
    agent_id="executor",
)
```

### Retrieving History

```python
# Get message history
messages = await service.get_conversation_history(conv_id)

# Include reasoning traces
messages_with_reasoning = await service.get_conversation_history(
    conv_id, include_reasoning=True
)

# Get current ledger state
ledger = await service.get_ledger_state(conv_id)

# Get event history for replay
events = await service.get_event_history(conv_id)

# Resume from sequence
events_from_seq_10 = await service.get_event_history(conv_id, from_sequence=10)
```

### Conversation Memory (Context Retention)

The persistence layer automatically provides conversation memory by injecting message history into workflow execution. This enables agents to maintain context across multiple turns in a conversation.

**How It Works:**

1. When a new message arrives, the system loads recent conversation history
2. History is formatted as "ROLE: content" pairs
3. History is prepended to the user's message before workflow execution
4. Agents receive both previous context and the new message

**Example Without Memory:**

```
User: "What's the capital of France?"
Agent: "Paris."

[New message - agent has NO context]
User: "What's its population?"
Agent: "I don't know what you're referring to."  ❌
```

**Example With Memory:**

```
User: "What's the capital of France?"
Agent: "Paris."

[New message - agent RECEIVES history]
Agent sees:
  Previous conversation:
  USER: What's the capital of France?
  ASSISTANT: Paris.

  User's current message: What's its population?

Agent: "Paris has approximately 2.1 million people in the city proper."  ✅
```

**Using the Persistence Adapter:**

```python
from agentic_fleet.api.conversations.persistence_adapter import (
    get_persistence_adapter,
)

adapter = get_persistence_adapter()

# Get formatted history for agent context
history = await adapter.get_formatted_history(
    conversation_id=conv_id,
    max_messages=10,  # Last 10 messages
)

# history is formatted as:
# "USER: message1\n\nASSISTANT: response1\n\nUSER: message2..."

# Inject into workflow
message_with_context = f"""
Previous conversation:
{history}

User's current message: {user_message}
"""

workflow_result = await workflow.run(message_with_context)
```

**History Window Configuration:**

The `max_messages` parameter controls how much history to include:

- **Too small (1-3)**: Agents may miss important context
- **Optimal (8-12)**: Balance between context and token usage
- **Too large (>20)**: May hit token limits, slower processing

**Summarization Integration:**

When conversations exceed the summarization threshold:

1. Oldest messages are compressed into a summary
2. Summary becomes part of the history
3. Recent messages preserved in full detail
4. Combined summary + recent messages stay within token limits

Example with summarization:

```
Messages 1-14: [Summarized]
→ "User asked about France, discussed Paris history and culture..."

Messages 15-20: Full content
→ USER: What about Lyon?
→ ASSISTANT: Lyon is France's third-largest city...

New message 21: "Tell me about its cuisine"
→ Receives summary + messages 15-20 as context
```

**API Integration:**

The chat routes automatically handle history injection:

```python
# In api/chat/routes.py
conversation = await persistence_adapter.get(conversation_id)

# Load history
conversation_history = await persistence_adapter.get_formatted_history(
    conversation_id, max_messages=10
)

# Inject into workflow (for non-fast-path)
if conversation_history and not use_fast_path:
    message_with_context = (
        f"Previous conversation:\n{conversation_history}\n\n"
        f"User's current message: {user_message}"
    )
```

**Benefits:**

- ✅ Agents understand follow-up questions and references
- ✅ Maintain conversational continuity across sessions
- ✅ Automatic summarization prevents token limit issues
- ✅ No manual context management required
- ✅ Works seamlessly with existing workflows

**Configuration:**

```bash
# Enable persistence for conversation memory
ENABLE_PERSISTENCE=true

# Control summarization to manage history size
CONVERSATION_SUMMARY_THRESHOLD=20  # Compress after 20 messages
CONVERSATION_SUMMARY_KEEP_RECENT=6  # Keep last 6 full messages
```

## Configuration

### Environment Variables

```bash
# Enable/disable persistence (default: true)
ENABLE_PERSISTENCE=true

# Database path (default: var/agenticfleet/conversations.db)
DB_PATH=/path/to/conversations.db

# Summarization threshold (default: 20 messages)
CONVERSATION_SUMMARY_THRESHOLD=20

# Recent messages to keep during summarization (default: 6)
CONVERSATION_SUMMARY_KEEP_RECENT=6

# Enable event sequencing (default: true)
ENABLE_EVENT_SEQUENCING=true

# Enable ledger tracking (default: true)
ENABLE_LEDGER_TRACKING=true

# Enable reasoning trace storage (default: true)
ENABLE_REASONING_TRACES=true
```

### Programmatic Configuration

```python
from agentic_fleet.persistence import PersistenceSettings

settings = PersistenceSettings()
settings.enabled = True
settings.db_path = Path("custom/path/conversations.db")
settings.summary_threshold = 30
settings.summary_keep_recent = 10
settings.enable_sequencing = True
settings.enable_ledger = True
settings.enable_reasoning_traces = True
```

## Integration with Existing Code

### Replacing In-Memory ConversationService

**Before (in-memory):**

```python
from agentic_fleet.api.conversations.service import ConversationService

service = ConversationService()
conversation = service.create_conversation(workflow_id)
service.add_message(conversation_id, role, content, ...)
history = service.get_conversation_history(conversation_id)
```

**After (SQLite-backed):**

```python
from agentic_fleet.persistence import ConversationPersistenceService, get_database_manager

db_manager = get_database_manager(settings.db_path)
service = ConversationPersistenceService(db_manager)

conversation_id = await service.create_conversation(workflow_id)
await service.add_message(conversation_id, role, content, ...)
history = await service.get_conversation_history(conversation_id)
```

**Key Differences:**

- All methods are async (`await`)
- Conversation ID returned instead of object
- Automatic sequencing and event emission
- Built-in summarization support

### Emitting Ledger Events in WorkflowEventBridge

```python
# In workflow/events.py
async def convert_event_with_persistence(
    event: dict,
    persistence_service: ConversationPersistenceService,
    conversation_id: str,
) -> dict:
    """Convert event and optionally persist ledger updates."""

    converted = convert_event(event)  # Existing conversion

    # Check for task ledger orchestrator messages
    if converted.get("type") == "orchestrator.message":
        kind = converted.get("data", {}).get("kind")

        if kind == "task_ledger":
            # Extract ledger data
            message = converted["data"]["message"]
            # Parse ledger information from message
            # ...

            # Store ledger snapshot
            await persistence_service.add_ledger_snapshot(
                conversation_id=conversation_id,
                task_id=task_id,
                goal=goal,
                status=status,
                snapshot_data=ledger_data,
            )

    return converted
```

## Testing

Run persistence tests:

```bash
# All persistence tests
uv run pytest tests/test_persistence.py -v

# Specific tests
uv run pytest tests/test_persistence.py::test_sequence_monotonic_increment -v
uv run pytest tests/test_persistence.py::test_concurrent_sequence_allocation -v
uv run pytest tests/test_persistence.py::test_summarization_threshold -v
```

Key test scenarios:

- Monotonic sequence increment
- Concurrent sequence allocation safety
- Message history ordering
- Ledger snapshot storage and retrieval
- Event replay from sequence
- Automatic summarization trigger
- Reasoning trace preservation

## Performance Considerations

### Indexing

All foreign keys have indexes. Additional indexes on frequently queried fields:

```sql
CREATE INDEX idx_messages_conversation_sequence ON messages(conversation_id, sequence);
CREATE INDEX idx_events_conversation_sequence ON events(conversation_id, sequence);
CREATE INDEX idx_ledger_conversation_sequence ON ledger_snapshots(conversation_id, sequence);
CREATE INDEX idx_reasoning_conversation ON reasoning_traces(conversation_id);
CREATE INDEX idx_reasoning_message ON reasoning_traces(message_id);
```

### Sequence Allocation

Sequence allocation uses atomic `UPDATE...RETURNING` to avoid race conditions. SQLite's built-in locking ensures safety for concurrent access.

### Summarization Impact

Summarization only runs:

- After assistant messages (not user messages)
- When threshold exceeded
- Asynchronously (doesn't block response)

Average overhead: ~100-500ms for LLM summary generation.

## Migration from In-Memory Storage

1. **Install dependency**: `aiosqlite>=0.20.0`
2. **Initialize database**: Run on startup or first request
3. **Update service instantiation**: Use `ConversationPersistenceService`
4. **Convert sync to async**: Add `await` to persistence calls
5. **Optional**: Migrate existing data from memory to SQLite

Example migration script:

```python
# Migrate from in-memory to SQLite
from agentic_fleet.api.conversations.service import ConversationService
from agentic_fleet.persistence import ConversationPersistenceService, get_database_manager

# Old service
old_service = ConversationService()

# New service
db_manager = get_database_manager("var/agenticfleet/conversations.db")
new_service = ConversationPersistenceService(db_manager)

# Migrate conversations
for conv_id, conv in old_service.conversations.items():
    await new_service.create_conversation(
        conversation_id=conv_id,
        workflow_id=conv.workflow_id,
        metadata={"migrated": True},
    )

    # Migrate messages
    for msg in conv.messages:
        await new_service.add_message(
            conversation_id=conv_id,
            role=msg.role,
            content=msg.content,
            reasoning=msg.reasoning,
            agent_id=msg.agent_id,
            message_id=msg.id,
            emit_event=False,  # Skip events for historical data
        )
```

## Troubleshooting

### Database Locked Error

**Symptom**: `sqlite3.OperationalError: database is locked`

**Solution**: Reduce concurrent write operations or increase timeout:

```python
async with aiosqlite.connect(db_path, timeout=10.0) as db:
    # operations
```

### High Summarization Frequency

**Symptom**: Summarization running too often

**Solution**: Increase threshold or `keep_recent` count:

```bash
CONVERSATION_SUMMARY_THRESHOLD=50
CONVERSATION_SUMMARY_KEEP_RECENT=10
```

### Missing Reasoning Traces

**Symptom**: Reasoning not appearing in history

**Solution**: Enable reasoning traces and use `include_reasoning=True`:

```bash
ENABLE_REASONING_TRACES=true
```

```python
history = await service.get_conversation_history(conv_id, include_reasoning=True)
```

### Sequence Gaps

**Symptom**: Non-consecutive sequence numbers

**Cause**: Normal - sequence counter increments for all activity (messages + events + ledger)

**Solution**: No action needed - gaps are expected and don't affect ordering

## Future Enhancements

- **Alembic migrations** for schema versioning
- **PostgreSQL support** via SQLAlchemy
- **Sharding** for multi-tenant deployments
- **Retention policies** (auto-delete old conversations)
- **Export/import** tools for backup
- **Query API** for analytics
