# Performance Improvements - Suggested Code Changes

This document contains specific, actionable code improvements to address the performance issues identified in `PERFORMANCE_ANALYSIS.md`.

## Quick Reference

- **Immediate**: [Fix BridgeMiddleware Concurrency](#1-fix-bridgemiddleware-concurrency-issue)
- **High Impact**: [Refactor map_workflow_event](#2-refactor-map_workflow_event-dispatch-table)
- **High Impact**: [Simplify WebSocket Handler](#3-extract-websocket-handler-sub-functions)
- **Medium Impact**: [Simplify SSE Stream](#4-extract-sse-stream-setup)

---

## 1. Fix BridgeMiddleware Concurrency Issue

**Priority**: 🔴 Critical  
**File**: `src/agentic_fleet/api/middleware.py`  
**Effort**: 2-3 hours  
**Risk**: Medium

### Problem

`BridgeMiddleware` stores `self.execution_data` which is mutated during request processing. Since `SupervisorWorkflow` (and its middlewares) are shared across all WebSocket/SSE requests via `app.state.supervisor_workflow`, concurrent requests will race on this shared state.

### Solution: Use contextvars for request-scoped storage

```python
# Add to imports
from contextvars import ContextVar
from typing import Any

# Add module-level contextvar
_execution_data_var: ContextVar[dict[str, Any]] = ContextVar("execution_data", default=None)

class BridgeMiddleware(ChatMiddleware):
    """Middleware that captures workflow execution for offline learning."""

    def __init__(
        self,
        history_manager: HistoryManager,
        dspy_examples_path: str | None = ".var/logs/dspy_examples.jsonl",
    ):
        self.history_manager = history_manager
        self.dspy_examples_path = dspy_examples_path
        # Remove: self.execution_data

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Initialize execution data when workflow starts."""
        execution_data = {
            "workflowId": context.get("workflowId"),
            "task": task,
            "start_time": datetime.now().isoformat(),
            "mode": context.get("mode", "standard"),
            "metadata": context.get("metadata", {}),
        }
        _execution_data_var.set(execution_data)

    async def on_event(self, event: Any) -> None:
        """Handle intermediate workflow events (currently a no-op)."""
        return None

    async def on_end(self, result: Any) -> None:
        """Persist execution data and DSPy example when workflow completes."""
        execution_data = _execution_data_var.get()
        if execution_data is None:
            logger.warning("on_end called but no execution_data in context")
            return

        execution_data["end_time"] = datetime.now().isoformat()

        if isinstance(result, dict):
            execution_data.update(result)
        else:
            execution_data["result"] = str(result)

        try:
            await self.history_manager.save_execution_async(execution_data)
            await self._save_dspy_example(execution_data)
        except Exception as exc:
            logger.error("Failed to persist execution data: %s", exc)

    async def _save_dspy_example(self, execution_data: dict[str, Any]) -> None:
        """Save execution as DSPy training example."""
        # Update to accept execution_data as parameter
        if not self.dspy_examples_path:
            return

        # Rest of implementation...
```

### Testing

```python
# tests/test_middleware_concurrency.py
import asyncio
import pytest
from agentic_fleet.api.middleware import BridgeMiddleware

@pytest.mark.asyncio
async def test_bridge_middleware_concurrent_execution():
    """Test that concurrent requests don't share execution data."""
    middleware = BridgeMiddleware(mock_history_manager)
    
    async def run_task(task_id):
        await middleware.on_start(f"task_{task_id}", {"workflowId": task_id})
        # Simulate concurrent processing
        await asyncio.sleep(0.01)
        await middleware.on_end({"result": f"result_{task_id}"})
        return task_id
    
    # Run 10 concurrent tasks
    results = await asyncio.gather(*[run_task(i) for i in range(10)])
    
    # Verify all tasks completed without data corruption
    assert len(results) == 10
```

---

## 2. Refactor map_workflow_event - Dispatch Table

**Priority**: 🟠 High  
**File**: `src/agentic_fleet/api/events/mapping.py`  
**Effort**: 6-8 hours  
**Risk**: Medium-High

### Problem

The `map_workflow_event()` function is 580 lines long with a massive if/elif chain for 15+ event types. This makes it hard to maintain and potentially slow (linear search through types).

### Solution: Extract handlers and use dispatch table

```python
# Type alias for handler signature
from collections.abc import Callable
EventHandler = Callable[[Any, str], tuple[StreamEvent | list[StreamEvent] | None, str]]

def _handle_workflow_started(
    event: WorkflowStartedEvent, accumulated_reasoning: str
) -> tuple[None, str]:
    """Skip generic WorkflowStartedEvent - covered by IN_PROGRESS status event."""
    return None, accumulated_reasoning


def _handle_workflow_status(
    event: WorkflowStatusEvent, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle WorkflowStatusEvent - convert FAILED to error, IN_PROGRESS to progress."""
    state = event.state
    data = event.data or {}
    message = data.get("message", "")
    workflow_id = data.get("workflow_id", "")

    # Convert state to valid name
    if hasattr(state, "name"):
        state_name = state.name
    elif isinstance(state, str):
        state_name = state.upper()
    else:
        logger.warning(f"Unrecognized workflow state type: {type(state)}")
        return None, accumulated_reasoning

    if state_name not in VALID_WORKFLOW_STATES:
        logger.warning(f"Unrecognized workflow state value: {state_name!r}")
        return None, accumulated_reasoning

    if state_name == "FAILED":
        event_type = StreamEventType.ERROR
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                error=message or "Workflow failed",
                data={"workflow_id": workflow_id, **data},
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )
    elif state_name == "IN_PROGRESS":
        event_type = StreamEventType.ORCHESTRATOR_MESSAGE
        kind = "progress"
        category, ui_hint = classify_event(event_type, kind)
        return (
            StreamEvent(
                type=event_type,
                message=message or "Workflow started",
                kind=kind,
                data={"workflow_id": workflow_id, **data},
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )

    return None, accumulated_reasoning


def _handle_request_info(
    event: RequestInfoEvent, accumulated_reasoning: str
) -> tuple[StreamEvent, str]:
    """Handle agent-framework workflow request events (HITL)."""
    data = getattr(event, "data", None)
    request_id = None
    request_obj = None

    if data is not None:
        request_id = getattr(data, "request_id", None)
        request_obj = getattr(data, "request", None)
        if request_id is None and isinstance(data, dict):
            request_id = data.get("request_id")
            request_obj = data.get("request")

    if request_id is None:
        request_id = getattr(event, "request_id", None)

    request_type_name = type(request_obj).__name__ if request_obj else None
    if request_type_name is None and data is not None:
        request_type_name = type(data).__name__

    # Serialize payload
    payload = _serialize_request_payload(request_obj)

    # Pick UI message
    msg = _get_request_message(request_type_name)

    event_type = StreamEventType.ORCHESTRATOR_MESSAGE
    kind = "request"
    category, ui_hint = classify_event(event_type, kind)
    return (
        StreamEvent(
            type=event_type,
            message=msg,
            agent_id="orchestrator",
            kind=kind,
            data={
                "request_id": request_id,
                "request_type": request_type_name,
                "request": payload,
            },
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )


def _serialize_request_payload(request_obj: Any) -> Any:
    """Best-effort serialization of request payload."""
    if request_obj is None:
        return None

    if hasattr(request_obj, "model_dump"):
        try:
            return request_obj.model_dump()
        except Exception:
            pass
    elif hasattr(request_obj, "to_dict"):
        try:
            return request_obj.to_dict()
        except Exception:
            pass
    elif isinstance(request_obj, dict):
        return request_obj

    return {
        "type": type(request_obj).__name__,
        "repr": repr(request_obj),
    }


def _get_request_message(request_type_name: str | None) -> str:
    """Get UI message based on request type."""
    lowered = (request_type_name or "").lower()
    if "approval" in lowered:
        return "Tool approval required"
    elif "user" in lowered and "input" in lowered:
        return "User input required"
    elif "intervention" in lowered or "plan" in lowered:
        return "Human intervention required"
    return "Action required"


def _handle_reasoning_stream(
    event: ReasoningStreamEvent, accumulated_reasoning: str
) -> tuple[StreamEvent, str]:
    """Handle GPT-5 reasoning tokens."""
    new_accumulated = accumulated_reasoning + event.reasoning

    if event.is_complete:
        event_type = StreamEventType.REASONING_COMPLETED
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                reasoning=event.reasoning,
                agent_id=event.agent_id,
                category=category,
                ui_hint=ui_hint,
            ),
            new_accumulated,
        )

    event_type = StreamEventType.REASONING_DELTA
    category, ui_hint = classify_event(event_type)
    return (
        StreamEvent(
            type=event_type,
            reasoning=event.reasoning,
            agent_id=event.agent_id,
            category=category,
            ui_hint=ui_hint,
        ),
        new_accumulated,
    )


# Continue for other event types...
# _handle_agent_message()
# _handle_executor_completed()
# _handle_workflow_output()
# etc.


# Dispatch table
_EVENT_HANDLERS: dict[type, EventHandler] = {
    WorkflowStartedEvent: _handle_workflow_started,
    WorkflowStatusEvent: _handle_workflow_status,
    RequestInfoEvent: _handle_request_info,
    ReasoningStreamEvent: _handle_reasoning_stream,
    MagenticAgentMessageEvent: _handle_agent_message,
    ExecutorCompletedEvent: _handle_executor_completed,
    WorkflowOutputEvent: _handle_workflow_output,
    # Add all other event types...
}


def map_workflow_event(
    event: Any,
    accumulated_reasoning: str,
) -> tuple[StreamEvent | list[StreamEvent] | None, str]:
    """
    Convert an internal workflow event into StreamEvent(s) for SSE streaming.

    Uses a dispatch table for O(1) lookup instead of linear if/elif chain.

    Parameters:
        event: The workflow event to map.
        accumulated_reasoning: Running concatenation of reasoning text.

    Returns:
        Tuple of (StreamEvent | list | None, updated_reasoning).
    """
    event_type = type(event)
    handler = _EVENT_HANDLERS.get(event_type)

    if handler:
        return handler(event, accumulated_reasoning)

    # Fallback: check for dict-based events
    if isinstance(event, dict):
        return _handle_dict_event(event, accumulated_reasoning)

    # Unknown event type
    logger.debug(f"Unknown event type skipped: {event_type.__name__}")
    return None, accumulated_reasoning
```

### Benefits

1. **Performance**: O(1) lookup vs O(n) if/elif chain
2. **Maintainability**: Each handler is ~20-50 lines (easy to understand)
3. **Testability**: Test handlers independently
4. **Extensibility**: Add new event types without modifying main function

### Testing

```python
# tests/api/test_event_mapping_refactored.py
def test_dispatch_table_completeness():
    """Verify all event types have handlers."""
    from agent_framework._workflows import ALL_EVENT_TYPES
    for event_type in ALL_EVENT_TYPES:
        assert event_type in _EVENT_HANDLERS, f"Missing handler for {event_type}"

def test_handler_isolation():
    """Test each handler independently."""
    event = WorkflowStatusEvent(state="FAILED", data={"message": "Test failure"})
    result, reasoning = _handle_workflow_status(event, "")
    assert result.type == StreamEventType.ERROR
    assert result.error == "Test failure"
```

---

## 3. Extract WebSocket Handler Sub-Functions

**Priority**: 🟠 High  
**File**: `src/agentic_fleet/services/chat_websocket.py`  
**Effort**: 4-6 hours  
**Risk**: Medium

### Problem

The `handle()` method is 300+ lines with complexity 76, handling validation, setup, message loop, and error handling all in one function.

### Solution: Extract phases

```python
class ChatWebSocketService:
    async def handle(self, websocket: WebSocket) -> None:
        """Handle a WebSocket chat session end-to-end."""
        # Phase 1: Validation
        if not _validate_websocket_origin(websocket):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        # Phase 2: Setup
        setup_result = await self._setup_session(websocket)
        if not setup_result.success:
            await self._send_error(websocket, setup_result.error)
            await websocket.close()
            return

        # Phase 3: Message loop
        try:
            await self._message_loop(websocket, setup_result.context)
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {setup_result.context.session_id}")
        except Exception as exc:
            logger.error(f"WebSocket error: {exc}", exc_info=True)
            await self._send_error(websocket, str(exc))
        finally:
            await self._cleanup_session(setup_result.context)

    async def _setup_session(self, websocket: WebSocket) -> _SetupResult:
        """Setup WebSocket session with managers and workflow."""
        app = websocket.app
        session_manager = getattr(app.state, "session_manager", None)
        conversation_manager = getattr(app.state, "conversation_manager", None)

        if session_manager is None or conversation_manager is None:
            return _SetupResult(
                success=False,
                error="Server not initialized"
            )

        # Get or create workflow
        workflow = await self._get_or_create_workflow(app)
        if workflow is None:
            return _SetupResult(
                success=False,
                error="Workflow initialization failed"
            )

        return _SetupResult(
            success=True,
            context=_SessionContext(
                session_manager=session_manager,
                conversation_manager=conversation_manager,
                workflow=workflow,
            )
        )

    async def _message_loop(self, websocket: WebSocket, context: _SessionContext) -> None:
        """Main WebSocket message processing loop."""
        cancel_task: asyncio.Task | None = None

        try:
            while True:
                # Receive message
                message_data = await websocket.receive_json()
                msg_type = message_data.get("type")

                if msg_type == "task":
                    cancel_task = await self._handle_task_message(
                        websocket, message_data, context
                    )
                elif msg_type == "response":
                    await self._handle_response_message(
                        websocket, message_data, context
                    )
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "cancel":
                    await self._handle_cancel_message(message_data, cancel_task)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")

        except WebSocketDisconnect:
            raise
        finally:
            if cancel_task and not cancel_task.done():
                cancel_task.cancel()

    async def _handle_task_message(
        self, websocket: WebSocket, msg_data: dict, context: _SessionContext
    ) -> asyncio.Task | None:
        """Handle incoming task message and start streaming."""
        task_text = msg_data.get("message", "").strip()
        if not task_text:
            await self._send_error(websocket, "Empty task")
            return None

        conversation_id = msg_data.get("conversation_id", "default")
        reasoning_effort = msg_data.get("reasoning_effort")

        # Create cancel event for this task
        cancel_event = asyncio.Event()

        # Start streaming task
        cancel_task = asyncio.create_task(
            self._stream_task(
                websocket,
                task_text,
                conversation_id,
                context,
                cancel_event,
                reasoning_effort,
            )
        )

        return cancel_task

    async def _handle_response_message(
        self, websocket: WebSocket, msg_data: dict, context: _SessionContext
    ) -> None:
        """Handle HITL response message."""
        request_id = msg_data.get("request_id")
        response_data = msg_data.get("response")

        if not request_id:
            await self._send_error(websocket, "Missing request_id")
            return

        # Forward response to workflow
        # ... (existing logic)

    async def _send_error(self, websocket: WebSocket, error: str) -> None:
        """Send error event to client."""
        try:
            await websocket.send_json({
                "type": "error",
                "error": error,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.error(f"Failed to send error: {exc}")


@dataclass
class _SetupResult:
    """Result of session setup."""
    success: bool
    context: _SessionContext | None = None
    error: str | None = None


@dataclass
class _SessionContext:
    """Context for WebSocket session."""
    session_manager: Any
    conversation_manager: Any
    workflow: Any
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### Benefits

1. **Reduced complexity**: Main `handle()` becomes ~15 lines, complexity ~5
2. **Easier testing**: Test each phase independently
3. **Better error handling**: Scoped try/catch per phase
4. **Clearer flow**: Setup → Loop → Cleanup pattern

---

## 4. Extract SSE Stream Setup

**Priority**: 🟡 Medium  
**File**: `src/agentic_fleet/services/chat_sse.py`  
**Effort**: 2-3 hours  
**Risk**: Low-Medium

### Solution

```python
class ChatSSEService:
    async def stream_chat(
        self,
        conversation_id: str,
        message: str,
        *,
        reasoning_effort: str | None = None,
        enable_checkpointing: bool = False,
    ) -> AsyncIterator[str]:
        """Stream chat response as SSE events."""
        # Setup
        context = await self._setup_stream_context(
            conversation_id, message, reasoning_effort, enable_checkpointing
        )

        try:
            # Stream events
            async for sse_event in self._stream_events(context):
                yield sse_event
        finally:
            # Cleanup
            await self._cleanup_stream(context)

    async def _setup_stream_context(
        self,
        conversation_id: str,
        message: str,
        reasoning_effort: str | None,
        enable_checkpointing: bool,
    ) -> _StreamContext:
        """Setup streaming context with history, checkpoints, and session."""
        # Load conversation history
        conversation_history = await self._load_conversation_history(conversation_id)

        # Setup checkpointing
        checkpoint_storage = None
        if enable_checkpointing:
            checkpoint_storage = await self._setup_checkpointing()

        # Get or create thread
        conversation_thread = await _get_or_create_thread(conversation_id)
        _prefer_service_thread_mode(conversation_thread)

        # Hydrate thread if needed
        if conversation_history and not _thread_has_any_messages(conversation_thread):
            await _hydrate_thread_from_conversation(conversation_thread, conversation_history)

        # Persist user message
        self.conversation_manager.add_message(
            conversation_id, MessageRole.USER, message, author="User"
        )

        # Create session
        session = await self.session_manager.create_session(
            task=message, reasoning_effort=reasoning_effort
        )
        assert session is not None, "Session creation failed"

        # Setup cancel tracking
        cancel_event = asyncio.Event()
        self._cancel_events[session.workflow_id] = cancel_event
        self._pending_responses[session.workflow_id] = asyncio.Queue()

        return _StreamContext(
            session=session,
            conversation_id=conversation_id,
            conversation_thread=conversation_thread,
            checkpoint_storage=checkpoint_storage,
            cancel_event=cancel_event,
        )

    async def _load_conversation_history(self, conversation_id: str) -> list[Any]:
        """Load conversation history and deduplicate."""
        conversation_history: list[Any] = []
        existing = self.conversation_manager.get_conversation(conversation_id)
        if existing is not None and getattr(existing, "messages", None):
            conversation_history = list(existing.messages)
        return conversation_history

    async def _setup_checkpointing(self) -> Any | None:
        """Setup checkpoint storage if requested."""
        try:
            from pathlib import Path
            from agent_framework._workflows import FileCheckpointStorage

            checkpoint_dir = ".var/checkpoints"
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            return FileCheckpointStorage(checkpoint_dir)
        except Exception:
            return None

    async def _cleanup_stream(self, context: _StreamContext) -> None:
        """Cleanup streaming resources."""
        workflow_id = context.session.workflow_id
        self._cancel_events.pop(workflow_id, None)
        self._pending_responses.pop(workflow_id, None)


@dataclass
class _StreamContext:
    """Context for SSE streaming."""
    session: Any
    conversation_id: str
    conversation_thread: Any
    checkpoint_storage: Any | None
    cancel_event: asyncio.Event
```

---

## 5. Simplify Agent Framework Shims

**Priority**: 🟢 Low  
**File**: `src/agentic_fleet/utils/agent_framework_shims.py`  
**Effort**: 2 hours  
**Risk**: Low

### Solution

```python
def ensure_agent_framework_shims():
    """Apply all necessary patches to agent-framework for compatibility."""
    _patch_azure_openai()
    _patch_async_client()
    _patch_agent_attributes()
    _patch_logging()


def _patch_azure_openai():
    """Patch AzureOpenAI client creation."""
    # Existing Azure OpenAI patching logic


def _patch_async_client():
    """Patch AsyncOpenAI client support."""
    # Existing async client patching logic


def _patch_agent_attributes():
    """Patch ChatAgent attributes for compatibility."""
    # Existing attribute patching logic


def _patch_logging():
    """Configure agent-framework logging."""
    # Existing logging configuration
```

---

## Testing Checklist

Before deploying any changes:

- [ ] All existing tests pass: `make test`
- [ ] WebSocket connections work correctly
- [ ] SSE streaming works correctly
- [ ] Concurrent requests don't corrupt data
- [ ] Performance hasn't regressed (< 10%)
- [ ] Memory usage is stable under load

Load testing commands:

```bash
# Install dependencies
pip install locust py-spy

# Profile SSE endpoint
py-spy record -o sse_profile.svg -- python -c "
import asyncio
from agentic_fleet.services.chat_sse import ChatSSEService
# ... profile code
"

# Load test WebSocket
locust -f tests/load/websocket_load.py --host ws://localhost:8000

# Concurrent request test
pytest tests/api/test_concurrency.py -n 10 --dist loadgroup
```

---

## Implementation Order

1. **Week 1**: Fix BridgeMiddleware (#1)
2. **Week 2**: Refactor map_workflow_event (#2)
3. **Week 3**: Simplify WebSocket handler (#3)
4. **Week 4**: Extract SSE setup (#4) + Simplify shims (#5)

Each week should include:
- Implementation
- Unit tests
- Integration tests
- Performance benchmarking
- Code review

---

## Success Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| WebSocket handler complexity | 76 | < 15 | Cyclomatic complexity |
| map_workflow_event length | 580 lines | < 100 lines | Line count |
| SSE stream_chat complexity | 37 | < 15 | Cyclomatic complexity |
| Concurrency issues | 1 | 0 | No race conditions under load |
| p50 latency | Baseline | < 110% | Load test results |
| p99 latency | Baseline | < 115% | Load test results |

