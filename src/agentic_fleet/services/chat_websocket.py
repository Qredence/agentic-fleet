"""WebSocket chat streaming service.

This module holds the implementation behind the `/api/ws/chat` WebSocket endpoint.
Routes should stay thin and delegate to this service for:
- Origin validation
- Session lifecycle management
- Multi-turn AgentThread caching
- Workflow event streaming → StreamEvent mapping
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from agent_framework._threads import AgentThread
else:
    try:
        from agent_framework._threads import AgentThread
    except Exception:  # pragma: no cover - optional dependency / stubbed environments

        class AgentThread:  # type: ignore[no-redef]
            """Fallback AgentThread stub used when agent-framework is unavailable."""

            pass


from fastapi import HTTPException, WebSocket, WebSocketDisconnect, status

from agentic_fleet.api.events.mapping import classify_event, map_workflow_event
from agentic_fleet.core.settings import get_settings
from agentic_fleet.models import (
    ChatRequest,
    MessageRole,
    StreamEvent,
    StreamEventType,
    WorkflowResumeRequest,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.services.background_evaluation import schedule_quality_evaluation
from agentic_fleet.utils.cfg import load_config
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.workflows.config import build_workflow_config_from_yaml
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

logger = setup_logger(__name__)

# In-memory storage for conversation threads (per conversation_id).
# Uses a bounded, TTL-aware cache to prevent memory leaks.
_MAX_THREADS = 100  # Maximum number of conversation threads to keep.
_TTL_SECONDS = 3600  # Time-to-live: expire threads after 1 hour of inactivity.

# Maps conversation_id -> (AgentThread, last_access_timestamp)
_conversation_threads: OrderedDict[str, tuple[AgentThread, float]] = OrderedDict()
_threads_lock: asyncio.Lock = asyncio.Lock()


_UNSET_TASK: object = object()


def _prefer_service_thread_mode(thread: Any | None) -> None:
    """Best-effort: prefer service-managed thread storage over local message stores.

    Certain agent-framework backends (notably Responses API implementations) may
    set a service-managed thread id on an AgentThread. If a local message_store is
    already attached, agent-framework raises:
    "Only the service_thread_id or message_store may be set...".

    To avoid that mode switch, we proactively clear any local message_store on
    cached threads and mark the thread so hydration is skipped.
    """

    if thread is None:
        return

    with contextlib.suppress(Exception):
        thread._agentic_fleet_prefer_service_thread = True

    with contextlib.suppress(Exception):
        if getattr(thread, "message_store", None) is not None:
            thread.message_store = None

    with contextlib.suppress(Exception):
        if getattr(thread, "_message_store", None) is not None:
            thread._message_store = None


def _sanitize_log_input(value: str) -> str:
    # Only allow alphanumeric, dash, underscore, and dot for maximal log safety.
    # Remove all other characters, including control codes and non-ASCII.
    # Truncate excessively long input for logging.
    import re

    if not isinstance(value, str):
        value = str(value)
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", value)
    if not sanitized:
        sanitized = "UNKNOWN"
    return sanitized[:256]


async def _get_or_create_thread(conversation_id: str | None) -> AgentThread | None:
    """Get or create an AgentThread for a conversation."""
    if not conversation_id:
        return None

    # NOTE: We intentionally cache threads by conversation_id so that each
    # user-visible conversation maintains context across WebSocket connections.

    async with _threads_lock:
        now = time.monotonic()

        # Evict expired entries first (lazy cleanup on access).
        expired_ids = [
            cid
            for cid, (_, last_access) in _conversation_threads.items()
            if now - last_access > _TTL_SECONDS
        ]
        for cid in expired_ids:
            del _conversation_threads[cid]
            logger.debug("Evicted expired conversation thread: conversation_id=%s", cid)

        if expired_ids:
            logger.info(
                "Evicted %d expired conversation thread(s) due to TTL (%ds)",
                len(expired_ids),
                _TTL_SECONDS,
            )

        # Check if thread exists and update access time.
        if conversation_id in _conversation_threads:
            thread, _ = _conversation_threads[conversation_id]
            _conversation_threads[conversation_id] = (thread, now)
            _conversation_threads.move_to_end(conversation_id)
            return thread

        # Create new thread.
        new_thread = AgentThread()
        _conversation_threads[conversation_id] = (new_thread, now)
        _conversation_threads.move_to_end(conversation_id)
        logger.debug(
            "Created new conversation thread for: %s", _sanitize_log_input(conversation_id)
        )

        # Evict oldest entries if capacity exceeded.
        while len(_conversation_threads) > _MAX_THREADS:
            evicted_id, (_, evicted_ts) = _conversation_threads.popitem(last=False)
            age_seconds = int(now - evicted_ts)
            logger.info(
                "Evicted oldest conversation thread to cap memory: conversation_id=%s, age=%ds",
                evicted_id,
                age_seconds,
            )

        return new_thread


def _message_role_value(role: Any) -> str:
    value = getattr(role, "value", role)
    return str(value)


def _thread_has_any_messages(thread: Any | None) -> bool:
    if thread is None:
        return False

    service_thread_id = getattr(thread, "service_thread_id", None) or getattr(
        thread, "_service_thread_id", None
    )
    if service_thread_id:
        return True

    if bool(getattr(thread, "is_initialized", False)):
        # Conservatively treat initialized threads as potentially holding context.
        return True

    try:
        return len(thread) > 0  # type: ignore[arg-type]
    except Exception:
        pass

    store = getattr(thread, "message_store", None) or getattr(thread, "_message_store", None)
    if store is not None:
        for attr in ("messages", "_messages", "history"):
            msgs = getattr(store, attr, None)
            if msgs is None:
                continue
            try:
                return len(msgs) > 0  # type: ignore[arg-type]
            except Exception:
                continue
        try:
            return len(store) > 0  # type: ignore[arg-type]
        except Exception:
            pass

    for attr in ("messages", "history", "_messages"):
        msgs = getattr(thread, attr, None)
        if msgs is None:
            continue
        try:
            return len(msgs) > 0  # type: ignore[arg-type]
        except Exception:
            continue

    return False


async def _hydrate_thread_from_conversation(
    thread: AgentThread | None,
    conversation_messages: list[Any],
) -> None:
    """Best-effort: populate an AgentThread with persisted conversation history.

    This is used to preserve context when the frontend opens a new WebSocket
    connection per turn. We avoid hard dependencies on agent-framework types by
    importing ChatMessage lazily.
    """

    if thread is None:
        return

    # If we prefer service-managed threads, do not hydrate local message stores.
    # This avoids invalid mode switching (message_store <-> service_thread_id).
    if bool(getattr(thread, "_agentic_fleet_prefer_service_thread", False)):
        return

    service_thread_id = getattr(thread, "service_thread_id", None) or getattr(
        thread, "_service_thread_id", None
    )
    if service_thread_id:
        return

    on_new_messages = getattr(thread, "on_new_messages", None)
    if not callable(on_new_messages):
        return

    try:
        from agent_framework._types import ChatMessage
    except Exception:
        # If agent-framework isn't available, there is no thread state to hydrate.
        return

    af_messages: list[Any] = []
    for msg in conversation_messages:
        try:
            role_str = _message_role_value(getattr(msg, "role", "user"))
            content = str(getattr(msg, "content", ""))
            if not content:
                continue
            author_name = getattr(msg, "author", None)
            af_messages.append(
                ChatMessage(
                    role=cast(Any, role_str),
                    text=content,
                    author_name=author_name,
                )
            )
        except Exception:
            continue

    if not af_messages:
        return

    try:
        await cast(Any, on_new_messages)(af_messages)
    except Exception:
        # Defensive: do not fail the chat endpoint if hydration fails.
        return


def _log_stream_event(event: StreamEvent, workflow_id: str) -> str | None:
    """Log a stream event to the console in real-time and return the log line."""
    event_type = event.type.value
    short_id = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

    log_line: str | None = None

    if event.type == StreamEventType.ORCHESTRATOR_MESSAGE:
        log_line = f"[{short_id}] 📢 {event.message}"
        logger.info(log_line)
    elif event.type == StreamEventType.ORCHESTRATOR_THOUGHT:
        log_line = f"[{short_id}] 💭 {event.kind}: {event.message}"
        logger.info(log_line)
    elif event.type == StreamEventType.RESPONSE_DELTA:
        # Only log first 80 chars of deltas to avoid flooding.
        delta_preview = (event.delta or "")[:80]
        if delta_preview:
            log_line = f"[{short_id}] ✏️  delta: {delta_preview}..."
            logger.debug(log_line)
    elif event.type == StreamEventType.RESPONSE_COMPLETED:
        result_preview = (event.message or "")[:100]
        log_line = f"[{short_id}] ✅ Response: {result_preview}..."
        logger.info(log_line)
    elif event.type == StreamEventType.REASONING_DELTA:
        log_line = f"[{short_id}] 🧠 reasoning delta"
        logger.debug(log_line)
    elif event.type == StreamEventType.REASONING_COMPLETED:
        log_line = f"[{short_id}] 🧠 Reasoning complete"
        logger.info(log_line)
    elif event.type == StreamEventType.ERROR:
        log_line = f"[{short_id}] ❌ Error: {event.error}"
        logger.error(log_line)
    elif event.type == StreamEventType.AGENT_START:
        log_line = f"[{short_id}] 🤖 Agent started: {event.agent_id}"
        logger.info(log_line)
    elif event.type == StreamEventType.AGENT_COMPLETE:
        log_line = f"[{short_id}] 🤖 Agent complete: {event.agent_id}"
        logger.info(log_line)
    elif event.type == StreamEventType.CANCELLED:
        log_line = f"[{short_id}] ⏹️ Cancelled by client"
        logger.info(log_line)
    elif event.type == StreamEventType.DONE:
        log_line = f"[{short_id}] 🏁 Stream completed"
        logger.info(log_line)
    elif event.type == StreamEventType.CONNECTED:
        log_line = f"[{short_id}] 🔌 WebSocket connected"
        logger.debug(log_line)
    elif event.type == StreamEventType.HEARTBEAT:
        log_line = f"[{short_id}] ♥ heartbeat"
        logger.debug(log_line)
    else:
        log_line = f"[{short_id}] {event_type}"
        logger.debug(log_line)

    return log_line


async def _event_generator(
    workflow: Any,
    session: WorkflowSession,
    session_manager: Any,
    *,
    task: str | object | None = _UNSET_TASK,
    log_reasoning: bool = False,
    reasoning_effort: str | None = None,
    cancel_event: asyncio.Event | None = None,
    thread: AgentThread | None = None,
    conversation_history: list[Any] | None = None,
    checkpoint_id: str | None = None,
    checkpoint_storage: Any | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Generate streaming events from workflow execution."""
    accumulated_reasoning = ""
    has_error = False
    error_message = ""

    try:
        await session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        logger.info(
            "Starting workflow stream: workflow_id=%s, task_preview=%s",
            session.workflow_id,
            session.task[:50],
        )

        init_event_type = StreamEventType.ORCHESTRATOR_MESSAGE
        init_category, init_ui_hint = classify_event(init_event_type)
        init_event = StreamEvent(
            type=init_event_type,
            message="Starting workflow execution...",
            category=init_category,
            ui_hint=init_ui_hint,
            workflow_id=session.workflow_id,
        )
        init_event.log_line = _log_stream_event(init_event, session.workflow_id)
        yield init_event.to_sse_dict()

        stream_kwargs: dict[str, Any] = {
            "reasoning_effort": reasoning_effort,
            "thread": thread,
            "conversation_history": conversation_history,
            # Align workflow history ids with the session id used by the websocket surface.
            "workflow_id": session.workflow_id,
            # We'll evaluate quality after sending the final answer so users don't wait.
            "schedule_quality_eval": False,
        }

        run_task: str | None
        if task is _UNSET_TASK:
            run_task = session.task
            is_resume = False
        elif task is None:
            run_task = None
            is_resume = True
        else:
            if not isinstance(task, str):
                raise TypeError("task override must be str | None")
            run_task = task
            is_resume = False

        # IMPORTANT: agent-framework requires message XOR checkpoint_id.
        # - new run: task/message provided => omit checkpoint_id
        # - resume: task/message omitted (None) => include checkpoint_id
        if checkpoint_id is not None and is_resume:
            stream_kwargs["checkpoint_id"] = checkpoint_id
        elif checkpoint_id is not None and not is_resume:
            logger.debug(
                "Ignoring checkpoint_id for new run in websocket streaming generator (checkpoint_id=%s)",
                checkpoint_id,
            )

        if checkpoint_storage is not None:
            stream_kwargs["checkpoint_storage"] = checkpoint_storage

        async for event in workflow.run_stream(run_task, **stream_kwargs):
            if cancel_event is not None and cancel_event.is_set():
                logger.info("Workflow cancelled: workflow_id=%s", session.workflow_id)
                break

            stream_event, accumulated_reasoning = map_workflow_event(event, accumulated_reasoning)
            if stream_event is None:
                continue

            events_to_emit = stream_event if isinstance(stream_event, list) else [stream_event]
            for se in events_to_emit:
                se.workflow_id = session.workflow_id
                log_line = _log_stream_event(se, session.workflow_id)
                if log_line:
                    se.log_line = log_line
                yield se.to_sse_dict()

    except Exception as exc:
        has_error = True
        error_message = str(exc)
        logger.error(
            "Workflow stream error: workflow_id=%s, error=%s",
            session.workflow_id,
            error_message,
            exc_info=True,
        )

        error_event_type = StreamEventType.ERROR
        error_category, error_ui_hint = classify_event(error_event_type)
        error_event = StreamEvent(
            type=error_event_type,
            error=error_message,
            reasoning_partial=bool(accumulated_reasoning) if accumulated_reasoning else None,
            category=error_category,
            ui_hint=error_ui_hint,
            workflow_id=session.workflow_id,
        )
        error_event.log_line = _log_stream_event(error_event, session.workflow_id)
        yield error_event.to_sse_dict()

    finally:
        final_status = WorkflowStatus.FAILED if has_error else WorkflowStatus.COMPLETED
        await session_manager.update_status(
            session.workflow_id,
            final_status,
            completed_at=datetime.now(),
        )

        if log_reasoning and accumulated_reasoning:
            logger.info(
                "Workflow reasoning captured: workflow_id=%s, reasoning_length=%d",
                session.workflow_id,
                len(accumulated_reasoning),
            )

        done_event_type = StreamEventType.DONE
        done_category, done_ui_hint = classify_event(done_event_type)
        done_event = StreamEvent(
            type=done_event_type,
            category=done_category,
            ui_hint=done_ui_hint,
            workflow_id=session.workflow_id,
        )
        done_event.log_line = _log_stream_event(done_event, session.workflow_id)
        yield done_event.to_sse_dict()

        logger.info(
            "Workflow stream completed: workflow_id=%s, status=%s, had_error=%s",
            session.workflow_id,
            final_status.value,
            has_error,
        )


def _validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket connection origin against allowed CORS origins."""
    settings = get_settings()
    origin = websocket.headers.get("origin", "")

    # Allow connections without origin header (same-origin, CLI tools, etc.)
    if not origin:
        return True

    if settings.ws_allow_localhost:
        localhost_patterns = (
            "http://localhost:",
            "http://127.0.0.1:",
            "https://localhost:",
            "https://127.0.0.1:",
        )
        if any(origin.startswith(p) for p in localhost_patterns):
            return True

    if "*" in settings.cors_allowed_origins:
        return True

    if origin in settings.cors_allowed_origins:
        return True

    logger.warning(
        "WebSocket connection rejected: invalid origin '%s'", _sanitize_log_input(origin)
    )
    return False


class ChatWebSocketService:
    """Service implementing the WebSocket chat protocol at `/api/ws/chat`."""

    async def handle(self, websocket: WebSocket) -> None:
        """Handle a WebSocket chat session end-to-end."""
        if not _validate_websocket_origin(websocket):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        app = websocket.app
        session_manager = (
            app.state.session_manager if hasattr(app.state, "session_manager") else None
        )
        conversation_manager = (
            app.state.conversation_manager if hasattr(app.state, "conversation_manager") else None
        )

        if session_manager is None or conversation_manager is None:
            logger.error("Required managers not available in app state")
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "Server not initialized",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close()
            return

        # Get or create a shared SupervisorWorkflow cached in app.state.
        #
        # The workflow is shared across all WebSocket sessions to avoid expensive
        # per-session initialization. This is safe because:
        # - reasoning_effort is stored in contextvars (thread-safe, request-scoped)
        # - conversation context is passed per-request
        # - agent chat_client state is no longer mutated (see _apply_reasoning_effort)
        #
        # We reuse preloaded compiled DSPy decision modules from app.state (Phase 2)
        # and disable runtime compilation for deterministic production behavior.
        # WorkflowConfig is built from YAML in app.state to ensure WebSocket sessions
        # use the same configuration as the server.
        try:
            workflow = getattr(app.state, "supervisor_workflow", None)
            if workflow is None:
                # Load YAML config from app.state (stored during lifespan) or fallback to loading it
                yaml_config = getattr(app.state, "yaml_config", None)
                if yaml_config is None:
                    logger.warning(
                        "YAML config not found in app.state, loading from file (should not happen in normal operation)"
                    )
                    yaml_config = load_config(validate=False)

                # Build WorkflowConfig from YAML to preserve all server settings
                workflow_config = build_workflow_config_from_yaml(
                    yaml_config,
                    compile_dspy=False,  # Disable runtime compilation for production
                )

                workflow = await create_supervisor_workflow(
                    compile_dspy=False,
                    config=workflow_config,
                    dspy_routing_module=getattr(app.state, "dspy_routing_module", None),
                    dspy_quality_module=getattr(app.state, "dspy_quality_module", None),
                    dspy_tool_planning_module=getattr(app.state, "dspy_tool_planning_module", None),
                )
                app.state.supervisor_workflow = workflow
        except Exception as exc:
            logger.error(
                "Failed to initialize workflow for WebSocket session: %s", exc, exc_info=True
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "Workflow initialization failed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close()
            return

        cancel_event = asyncio.Event()
        session: WorkflowSession | None = None
        heartbeat_task: asyncio.Task[None] | None = None
        last_event_ts = datetime.now()
        stream_start_ts = datetime.now()
        max_runtime_seconds = 300

        try:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=15)
            except TimeoutError:
                await websocket.send_json(
                    {
                        "type": StreamEventType.ERROR.value,
                        "error": "WebSocket handshake timed out",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return

            msg_type = data.get("type")
            is_resume = msg_type == "workflow.resume"

            conversation_id: str | None
            message: str | None
            reasoning_effort: str | None
            effective_checkpoint_id: str | None
            enable_checkpointing: bool

            if is_resume:
                resume_req = WorkflowResumeRequest(**data)
                conversation_id = resume_req.conversation_id
                message = None
                reasoning_effort = resume_req.reasoning_effort
                effective_checkpoint_id = resume_req.checkpoint_id
                enable_checkpointing = False
                logger.info(
                    "WebSocket resume request received: conversation_id=%s, checkpoint_id=%s",
                    conversation_id,
                    str(effective_checkpoint_id)[:64],
                )
            else:
                request = ChatRequest(**data)
                conversation_id = request.conversation_id
                message = request.message
                reasoning_effort = request.reasoning_effort
                enable_checkpointing = bool(request.enable_checkpointing)

                # Backward compatibility: treat checkpoint_id alongside message as a request to enable storage.
                raw_checkpoint_id = request.checkpoint_id
                if raw_checkpoint_id is not None:
                    enable_checkpointing = True
                    logger.warning(
                        "Received checkpoint_id along with a message; ignoring checkpoint_id for new run "
                        "(client_checkpoint_id=%s). Use enable_checkpointing for new runs or workflow.resume to resume.",
                        raw_checkpoint_id,
                    )

                effective_checkpoint_id = None

                msg_preview = message[:50] if len(message) > 50 else message
                sanitized_preview = re.sub(r"[\x00-\x1F\x7F\u2028\u2029]", "", msg_preview)
                logger.info(
                    "WebSocket chat request received: message_preview=%s, reasoning_effort=%s, conversation_id=%s, enable_checkpointing=%s",
                    sanitized_preview,
                    reasoning_effort,
                    conversation_id,
                    enable_checkpointing,
                )

            # Load persisted conversation (if any) to hydrate a fresh thread.
            # NOTE: We do this *before* persisting the current user message so that
            # the thread history doesn't accidentally include the new message twice.
            conversation_history: list[Any] = []
            if conversation_id:
                existing = conversation_manager.get_conversation(conversation_id)
                if existing is not None and getattr(existing, "messages", None):
                    conversation_history = list(existing.messages)

            # If the latest persisted message matches the incoming user message,
            # drop it (can happen on client retry/reconnect).
            if (
                message
                and conversation_history
                and _message_role_value(getattr(conversation_history[-1], "role", ""))
                == MessageRole.USER.value
                and str(getattr(conversation_history[-1], "content", "")).strip() == message.strip()
            ):
                conversation_history = conversation_history[:-1]

            checkpoint_storage: Any | None = None
            if enable_checkpointing or is_resume:
                try:
                    from agent_framework._workflows import (
                        FileCheckpointStorage,
                        InMemoryCheckpointStorage,
                    )

                    checkpoint_dir = ".var/checkpoints"
                    try:
                        from pathlib import Path

                        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
                    except Exception:
                        checkpoint_dir = ""

                    if checkpoint_dir:
                        checkpoint_storage = FileCheckpointStorage(checkpoint_dir)
                    else:
                        checkpoint_storage = InMemoryCheckpointStorage()
                except Exception:
                    checkpoint_storage = None

            conversation_thread = await _get_or_create_thread(conversation_id)

            # Normalize thread storage mode to avoid service_thread_id/message_store conflicts.
            _prefer_service_thread_mode(conversation_thread)

            # Best-effort hydration for new socket connections.
            if conversation_history and not _thread_has_any_messages(conversation_thread):
                await _hydrate_thread_from_conversation(conversation_thread, conversation_history)

            # Persist current user message after hydration.
            if not is_resume and conversation_id and message:
                conversation_manager.add_message(
                    conversation_id,
                    MessageRole.USER,
                    message,
                    author="User",
                )

            try:
                session = await session_manager.create_session(
                    task=message or f"[resume:{effective_checkpoint_id}]",
                    reasoning_effort=reasoning_effort,
                )
            except HTTPException as exc:
                error_type = StreamEventType.ERROR
                error_category, error_ui_hint = classify_event(error_type)
                error_event = StreamEvent(
                    type=error_type,
                    error=exc.detail,
                    category=error_category,
                    ui_hint=error_ui_hint,
                    workflow_id=None,
                )
                await websocket.send_json(error_event.to_sse_dict())
                await websocket.close()
                return

            assert session is not None, "Session should be created at this point"

            connected_type = StreamEventType.CONNECTED
            connected_category, connected_ui_hint = classify_event(connected_type)
            connected_event = StreamEvent(
                type=connected_type,
                message="Connected",
                data={
                    "conversation_id": conversation_id,
                    "checkpoint_id": effective_checkpoint_id,
                    "is_resume": is_resume,
                    "checkpointing_enabled": bool(checkpoint_storage is not None),
                },
                category=connected_category,
                ui_hint=connected_ui_hint,
                workflow_id=session.workflow_id,
            )
            connected_event.log_line = _log_stream_event(connected_event, session.workflow_id)
            await websocket.send_json(connected_event.to_sse_dict())
            last_event_ts = datetime.now()

            async def send_heartbeat() -> None:
                nonlocal last_event_ts
                try:
                    while True:
                        await asyncio.sleep(5)
                        heartbeat_event = StreamEvent(
                            type=StreamEventType.HEARTBEAT,
                            message="heartbeat",
                            workflow_id=session.workflow_id,
                            timestamp=datetime.now(),
                        )
                        await websocket.send_json(heartbeat_event.to_sse_dict())
                        last_event_ts = datetime.now()
                except Exception:
                    return

            heartbeat_task = asyncio.create_task(send_heartbeat())

            async def listen_for_cancel() -> None:
                try:
                    while not cancel_event.is_set():
                        try:
                            msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.25)
                            msg_type = msg.get("type")
                            if msg_type == "cancel":
                                logger.info(
                                    "Cancel requested for workflow: %s", session.workflow_id
                                )
                                cancel_event.set()
                                break
                            if msg_type in ("workflow.response", "workflow_response", "response"):
                                request_id = msg.get("request_id")
                                response_payload = msg.get("response")
                                if not request_id:
                                    logger.warning(
                                        "Received workflow response without request_id (workflow_id=%s)",
                                        session.workflow_id,
                                    )
                                    continue

                                try:
                                    # Forward to SupervisorWorkflow which will call the underlying
                                    # agent-framework workflow's send_responses_streaming/send_responses.
                                    await workflow.send_workflow_responses(
                                        {str(request_id): response_payload}
                                    )
                                    logger.info(
                                        "Forwarded workflow response (workflow_id=%s, request_id=%s)",
                                        session.workflow_id,
                                        request_id,
                                    )
                                except Exception as exc:
                                    logger.error(
                                        "Failed to forward workflow response (workflow_id=%s, request_id=%s): %s",
                                        session.workflow_id,
                                        request_id,
                                        exc,
                                        exc_info=True,
                                    )
                        except TimeoutError:
                            continue
                except WebSocketDisconnect:
                    cancel_event.set()
                except Exception:
                    cancel_event.set()

            cancel_task = asyncio.create_task(listen_for_cancel())

            log_reasoning = False
            if hasattr(workflow, "config") and workflow.config:
                config = workflow.config
                logging_config = getattr(config, "logging", None)
                if logging_config and hasattr(logging_config, "log_reasoning"):
                    log_reasoning = bool(logging_config.log_reasoning)

            response_text = ""
            response_delta_text = ""
            last_agent_text = ""
            last_author: str | None = None
            last_agent_id: str | None = None
            saw_done = False
            response_completed_emitted = False

            try:
                async for event_data in _event_generator(
                    workflow,
                    session,
                    session_manager,
                    task=message,
                    log_reasoning=log_reasoning,
                    reasoning_effort=reasoning_effort,
                    cancel_event=cancel_event,
                    thread=conversation_thread,
                    conversation_history=conversation_history,
                    checkpoint_id=effective_checkpoint_id,
                    checkpoint_storage=checkpoint_storage,
                ):
                    # Idle timeout safeguard.
                    if (datetime.now() - last_event_ts).total_seconds() > 120:
                        timeout_type = StreamEventType.ERROR
                        timeout_category, timeout_ui_hint = classify_event(timeout_type)
                        timeout_event = StreamEvent(
                            type=timeout_type,
                            error="Stream idle timeout",
                            category=timeout_category,
                            ui_hint=timeout_ui_hint,
                            workflow_id=session.workflow_id,
                        )
                        timeout_event.log_line = _log_stream_event(
                            timeout_event, session.workflow_id
                        )
                        await websocket.send_json(timeout_event.to_sse_dict())
                        cancel_event.set()
                        break

                    # Max runtime safeguard.
                    if (datetime.now() - stream_start_ts).total_seconds() > max_runtime_seconds:
                        timeout_type = StreamEventType.ERROR
                        timeout_category, timeout_ui_hint = classify_event(timeout_type)
                        timeout_event = StreamEvent(
                            type=timeout_type,
                            error="Stream max runtime exceeded",
                            category=timeout_category,
                            ui_hint=timeout_ui_hint,
                            workflow_id=session.workflow_id,
                        )
                        timeout_event.log_line = _log_stream_event(
                            timeout_event, session.workflow_id
                        )
                        await websocket.send_json(timeout_event.to_sse_dict())
                        cancel_event.set()
                        break

                    if cancel_event.is_set():
                        cancelled_type = StreamEventType.CANCELLED
                        cancelled_category, cancelled_ui_hint = classify_event(cancelled_type)
                        cancelled_event = StreamEvent(
                            type=cancelled_type,
                            message="Streaming cancelled by client",
                            category=cancelled_category,
                            ui_hint=cancelled_ui_hint,
                            workflow_id=session.workflow_id,
                        )
                        cancelled_event.log_line = _log_stream_event(
                            cancelled_event, session.workflow_id
                        )
                        await websocket.send_json(cancelled_event.to_sse_dict())
                        done_category, done_ui_hint = classify_event(StreamEventType.DONE)
                        done_event = StreamEvent(
                            type=StreamEventType.DONE,
                            category=done_category,
                            ui_hint=done_ui_hint,
                            workflow_id=session.workflow_id,
                        )
                        await websocket.send_json(done_event.to_sse_dict())
                        break

                    event_type = event_data.get("type")

                    author = event_data.get("author") or event_data.get("agent_id")
                    if author:
                        last_author = event_data.get("author") or last_author or author
                        last_agent_id = event_data.get("agent_id") or last_agent_id

                    if event_type == StreamEventType.RESPONSE_DELTA.value:
                        response_delta_text += event_data.get("delta", "")
                        # Prefer deltas until a completed event arrives.
                        response_text = response_delta_text
                    elif event_type == StreamEventType.RESPONSE_COMPLETED.value:
                        completed_msg = event_data.get("message", "")
                        if completed_msg:
                            response_text = completed_msg
                        last_author = event_data.get("author") or last_author
                        response_completed_emitted = True
                    elif event_type in (
                        StreamEventType.AGENT_OUTPUT.value,
                        StreamEventType.AGENT_MESSAGE.value,
                    ):
                        agent_msg = event_data.get("message", "")
                        if agent_msg:
                            last_agent_text = agent_msg

                    if event_type == StreamEventType.DONE.value:
                        saw_done = True

                    await websocket.send_json(event_data)
                    last_event_ts = datetime.now()

                    if event_type == StreamEventType.DONE.value:
                        break
            finally:
                cancel_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await cancel_task

            final_text = (
                response_text.strip()
                or last_agent_text.strip()
                or "Sorry, I couldn't produce a final answer this time."
            )

            # Emit a final RESPONSE_COMPLETED only if the workflow did not already emit one.
            # This ensures the UI has a single authoritative "final answer" payload.
            if not response_completed_emitted:
                completed_type = StreamEventType.RESPONSE_COMPLETED
                comp_category, comp_ui = classify_event(completed_type)
                completed_event = StreamEvent(
                    type=completed_type,
                    message=final_text,
                    author=last_author,
                    agent_id=last_agent_id,
                    data={"quality_pending": True},
                    category=comp_category,
                    ui_hint=comp_ui,
                    workflow_id=session.workflow_id,
                )
                completed_event.log_line = _log_stream_event(completed_event, session.workflow_id)
                await websocket.send_json(completed_event.to_sse_dict())

            if not saw_done:
                done_category, done_ui_hint = classify_event(StreamEventType.DONE)
                done_event = StreamEvent(
                    type=StreamEventType.DONE,
                    category=done_category,
                    ui_hint=done_ui_hint,
                    workflow_id=session.workflow_id,
                )
                await websocket.send_json(done_event.to_sse_dict())

            assistant_message = None
            if conversation_id and final_text:
                assistant_message = conversation_manager.add_message(
                    conversation_id,
                    MessageRole.ASSISTANT,
                    final_text,
                    author=last_author,
                    agent_id=last_agent_id,
                    workflow_id=session.workflow_id,
                    quality_pending=True,
                )

            # Background quality evaluation (do not block the user).
            if (
                message
                and final_text
                and hasattr(workflow, "history_manager")
                and workflow.history_manager is not None
            ):
                schedule_quality_evaluation(
                    workflow_id=session.workflow_id,
                    task=message,
                    answer=final_text,
                    history_manager=workflow.history_manager,
                    conversation_manager=conversation_manager,
                    conversation_id=conversation_id,
                    message_id=getattr(assistant_message, "id", None),
                )

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as exc:
            logger.error("WebSocket error: %s", exc, exc_info=True)
            with contextlib.suppress(Exception):
                error_type = StreamEventType.ERROR
                error_category, error_ui_hint = classify_event(error_type)
                error_event = StreamEvent(
                    type=error_type,
                    error=str(exc),
                    category=error_category,
                    ui_hint=error_ui_hint,
                    workflow_id=session.workflow_id if session else None,
                )
                if session:
                    error_event.log_line = _log_stream_event(error_event, session.workflow_id)
                await websocket.send_json(error_event.to_sse_dict())
        finally:
            if session and cancel_event.is_set():
                await session_manager.update_status(
                    session.workflow_id,
                    WorkflowStatus.CANCELLED,
                    completed_at=datetime.now(),
                )
            with contextlib.suppress(Exception):
                await websocket.close()
            if heartbeat_task:
                heartbeat_task.cancel()


__all__ = ["ChatWebSocketService"]
