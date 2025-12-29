# Langfuse Sessions Setup

This guide explains how Langfuse sessions are configured in AgenticFleet to group related traces by conversation.

## Overview

Langfuse sessions allow you to group multiple traces (workflow executions) that belong to the same conversation. This is essential for:

- **Multi-turn conversations**: All traces in a conversation are grouped together
- **Session analytics**: Analyze user sessions and conversation flows
- **Cost tracking**: Track costs per conversation session
- **User journey**: Understand how users interact across multiple turns

## How It Works

### Session ID Mapping

AgenticFleet maps `conversation_id` to Langfuse `session_id`:

1. **Conversation ID**: The unique identifier for a user conversation (created by `ConversationManager`)
2. **Session ID**: The Langfuse session identifier (set via `propagate_attributes`)
3. **Mapping**: `conversation_id` → `session_id` (1:1 mapping)

### Automatic Session Tracking

Sessions are automatically tracked when:

1. **New Conversation**: When a user starts a new conversation, a `conversation_id` is created
2. **Workflow Execution**: Each workflow execution receives the `conversation_id`
3. **Langfuse Integration**: The `conversation_id` is passed as `session_id` to Langfuse
4. **Trace Grouping**: All traces in the same conversation are grouped under the same session

### Implementation Details

#### Workflow Supervisor

The `SupervisorWorkflow.run_stream()` method accepts `conversation_id` and uses it as the Langfuse session ID:

```python
async def run_stream(
    self,
    task: str | None,
    *,
    conversation_id: str | None = None,
    # ... other parameters
) -> AsyncIterator[Any]:
    # ...
    # Determine session_id: prefer conversation_id
    session_id = conversation_id

    # Set Langfuse context with session_id
    propagate_attributes(
        trace_id=trace_id,
        session_id=session_id,  # Maps conversation_id to Langfuse session
        # ...
    )
```

#### Chat Services

Both SSE and WebSocket services pass `conversation_id` to the workflow:

```python
# In chat_sse.py and chat_websocket.py
stream_kwargs["conversation_id"] = conversation_id
async for event in self.workflow.run_stream(message, **stream_kwargs):
```

## Usage

### Viewing Sessions in Langfuse

1. **Go to Langfuse Cloud** → Traces
2. **Filter by Session**: Use the session filter to see all traces in a conversation
3. **Session View**: Click on a session to see all related traces

### Session Metadata

Each trace includes session metadata:

```json
{
  "session_id": "conversation-uuid",
  "conversation_id": "conversation-uuid",
  "workflow_id": "workflow-uuid",
  "framework": "AgenticFleet"
}
```

### Session Analytics

In Langfuse, you can:

1. **View Session Timeline**: See all traces in chronological order
2. **Session Costs**: Track total costs per conversation session
3. **Session Duration**: See how long conversations last
4. **Trace Count**: See how many workflow executions per session

## Configuration

### Environment Variables

No additional configuration needed! Sessions work automatically when:

- `LANGFUSE_PUBLIC_KEY` is set
- `LANGFUSE_SECRET_KEY` is set
- `LANGFUSE_BASE_URL` is set

### Manual Session Management

If you need to manually set session IDs:

```python
from agentic_fleet.utils.infra.langfuse import set_langfuse_context

# Set session context
set_langfuse_context(
    session_id="custom-session-id",
    user_id="user-123",
    metadata={"custom": "data"},
)
```

## Troubleshooting

### Sessions Not Grouping

**Problem**: Traces appear but aren't grouped by session.

**Solutions**:

1. Verify `conversation_id` is being passed to `run_stream()`
2. Check Langfuse logs for session_id assignment
3. Verify `propagate_attributes()` is called with `session_id`

### Missing Session IDs

**Problem**: Traces don't have session_id set.

**Solutions**:

1. Ensure conversations are created before workflow execution
2. Check that `conversation_id` is not `None`
3. Verify chat services pass `conversation_id` to workflow

### Session Not Appearing in Langfuse

**Problem**: Session exists but doesn't show in Langfuse UI.

**Solutions**:

1. Wait a few seconds for traces to sync
2. Refresh the Langfuse UI
3. Check Langfuse API status
4. Verify credentials are correct

## Best Practices

1. **Always Use Conversations**: Create conversations for multi-turn interactions
2. **Consistent IDs**: Use the same `conversation_id` for all turns in a conversation
3. **Session Metadata**: Add relevant metadata to sessions for better filtering
4. **Session Cleanup**: Sessions persist in Langfuse; no manual cleanup needed

## Examples

### Example 1: Multi-Turn Conversation

```python
# Turn 1: User asks a question
conversation_id = "conv-123"
workflow.run_stream("What is Python?", conversation_id=conversation_id)
# Creates trace with session_id="conv-123"

# Turn 2: User asks follow-up
workflow.run_stream("Tell me more", conversation_id=conversation_id)
# Creates trace with session_id="conv-123" (same session!)

# Both traces are grouped under session "conv-123" in Langfuse
```

### Example 2: New Conversation

```python
# New conversation
conversation_id = conversation_manager.create_conversation().id
workflow.run_stream("Hello", conversation_id=conversation_id)
# Creates new session in Langfuse
```

## API Reference

### SupervisorWorkflow.run_stream()

```python
async def run_stream(
    self,
    task: str | None,
    *,
    conversation_id: str | None = None,  # Maps to Langfuse session_id
    workflow_id: str | None = None,
    reasoning_effort: str | None = None,
    thread: AgentThread | None = None,
    conversation_history: list[Any] | None = None,
    checkpoint_id: str | None = None,
    checkpoint_storage: Any | None = None,
    schedule_quality_eval: bool = True,
) -> AsyncIterator[Any]:
```

### set_langfuse_context()

```python
from agentic_fleet.utils.infra.langfuse import set_langfuse_context

set_langfuse_context(
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> None
```

## Next Steps

1. **Test Sessions**: Run a multi-turn conversation and verify traces are grouped
2. **View in Langfuse**: Check Langfuse UI to see session grouping
3. **Analytics**: Use session analytics to understand user behavior
4. **Cost Tracking**: Track costs per conversation session
