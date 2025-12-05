"""Streaming chat endpoint using WebSocket.

This module provides the streaming chat endpoint that converts
workflow events to JSON format for real-time frontend updates via WebSocket.
"""

from __future__ import annotations

import asyncio
import contextlib
import re  # For robust input sanitization
import string  # For printable ASCII filtering
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agent_framework._threads import AgentThread
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from agentic_fleet.app.dependencies import SessionManagerDep
from agentic_fleet.app.events.mapping import classify_event, map_workflow_event
from agentic_fleet.app.schemas import (
    ChatRequest,
    MessageRole,
    StreamEvent,
    StreamEventType,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.app.settings import get_settings
from agentic_fleet.dspy_modules.answer_quality import score_answer_with_dspy
from agentic_fleet.utils.logger import setup_logger

if TYPE_CHECKING:
    pass

logger = setup_logger(__name__)


def _sanitize_log_input(s: str) -> str:
    # Remove all control and non-printable characters (keep only printable ASCII)
    # Also, truncate excessively long input to reasonable length for logging.
    sanitized = "".join(ch for ch in s if ch in string.printable and ch not in "\r\n")
    return sanitized[:256]


router = APIRouter()

# In-memory storage for conversation threads (per conversation_id)
# Uses a bounded, TTL-aware cache to prevent memory leaks
_MAX_THREADS = 100  # Maximum number of conversation threads to keep
_TTL_SECONDS = 3600  # Time-to-live: expire threads after 1 hour of inactivity

# Maps conversation_id -> (AgentThread, last_access_timestamp)
_conversation_threads: OrderedDict[str, tuple[AgentThread, float]] = OrderedDict()
# Lock to synchronize access to _conversation_threads (prevents race conditions)
_threads_lock: asyncio.Lock = asyncio.Lock()


async def _get_or_create_thread(conversation_id: str | None) -> AgentThread | None:
    """Get or create an AgentThread for a conversation.

    Uses a bounded, TTL-aware cache that:
    - Evicts expired entries (older than _TTL_SECONDS)
    - Evicts oldest entries when capacity (_MAX_THREADS) is exceeded
    - Updates last-access timestamp on each access

    This function is thread-safe via asyncio.Lock.

    Args:
        conversation_id: The conversation ID, or None for no thread.

    Returns:
        The AgentThread for the conversation, or None if no conversation_id.
    """
    if not conversation_id:
        return None

    async with _threads_lock:
        now = time.monotonic()

        # Evict expired entries first (lazy cleanup on access)
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

        # Check if thread exists and update access time
        if conversation_id in _conversation_threads:
            thread, _ = _conversation_threads[conversation_id]
            _conversation_threads[conversation_id] = (thread, now)
            _conversation_threads.move_to_end(conversation_id)
            return thread

        # Create new thread
        new_thread = AgentThread()
        _conversation_threads[conversation_id] = (new_thread, now)
        _conversation_threads.move_to_end(conversation_id)
        logger.debug("Created new conversation thread for: %s", conversation_id)

        # Evict oldest entries if capacity exceeded
        while len(_conversation_threads) > _MAX_THREADS:
            evicted_id, (_, evicted_ts) = _conversation_threads.popitem(last=False)
            age_seconds = int(now - evicted_ts)
            logger.info(
                "Evicted oldest conversation thread to cap memory: conversation_id=%s, age=%ds",
                evicted_id,
                age_seconds,
            )

        return new_thread


# =============================================================================
# Real-time Logging Utilities
# =============================================================================


def _log_stream_event(event: StreamEvent, workflow_id: str) -> str | None:
    """Log a stream event to the console in real-time and return the log line.

    Args:
        event: The stream event to log.
        workflow_id: The workflow ID for context.

    Returns:
        The formatted log line that was emitted (or None if suppressed).
    """
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
        # Only log first 80 chars of deltas to avoid flooding
        delta_preview = (event.delta or "")[:80]
        if delta_preview:
            log_line = f"[{short_id}] ✏️  delta: {delta_preview}..."
            logger.debug(log_line)
    elif event.type == StreamEventType.RESPONSE_COMPLETED:
        result_preview = (event.message or "")[:100]
        log_line = f"[{short_id}] ✅ Response: {result_preview}..."
        logger.info(log_line)
    elif event.type == StreamEventType.REASONING_DELTA:
        # Log reasoning at debug level to avoid noise
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


def _evaluate_final_answer(final_text: str, task: str) -> dict[str, Any]:
    """Lightweight heuristic to flag obviously low-quality finals.

    Returns a dict with quality_score (0..1) and optional quality_flag.
    """
    text = final_text.strip()
    if not text:
        return {"quality_score": 0.0, "quality_flag": "empty"}

    lowered = text.lower()
    bad_phrases = ["i don't know", "cannot help", "sorry", "unable to", "as an ai"]
    penalty = any(p in lowered for p in bad_phrases)

    wc = len(text.split())
    base = min(wc / 50, 1.0)  # 50 words -> score ~1.0 cap

    # crude overlap with task keywords
    task_words = {w for w in re.findall(r"[a-zA-Z0-9]+", task.lower()) if len(w) > 3}
    text_words = {w for w in re.findall(r"[a-zA-Z0-9]+", lowered) if len(w) > 3}
    overlap = len(task_words & text_words) / max(len(task_words) or 1, 1)

    score = 0.5 * base + 0.5 * overlap
    if penalty:
        score *= 0.6

    flag = None
    if score < 0.35:
        flag = "low_confidence"
    return {"quality_score": round(score, 3), "quality_flag": flag}


async def _event_generator(
    workflow: Any,
    session: WorkflowSession,
    session_manager: Any,
    log_reasoning: bool = False,
    reasoning_effort: str | None = None,
    cancel_event: asyncio.Event | None = None,
    thread: AgentThread | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Generate streaming events from workflow execution.

    Args:
        workflow: The SupervisorWorkflow instance.
        session: The workflow session metadata.
        session_manager: The session manager for status updates.
        log_reasoning: Whether to accumulate reasoning for logging.
        reasoning_effort: Optional reasoning effort override for GPT-5 models.
        cancel_event: Optional asyncio.Event to signal cancellation.
        thread: Optional AgentThread for multi-turn conversation context.

    Yields:
        Dictionaries with event data suitable for JSON serialization.
    """
    accumulated_reasoning = ""
    has_error = False
    error_message = ""

    try:
        # Update session to running
        await session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        logger.info(
            f"Starting workflow stream: workflow_id={session.workflow_id}, "
            f"task_preview={session.task[:50]}"
        )

        # Yield initial orchestrator message
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

        # Stream workflow events with optional reasoning effort override and conversation thread
        async for event in workflow.run_stream(
            session.task, reasoning_effort=reasoning_effort, thread=thread
        ):
            # Check for cancellation
            if cancel_event is not None and cancel_event.is_set():
                logger.info(f"Workflow cancelled: workflow_id={session.workflow_id}")
                break

            stream_event, accumulated_reasoning = map_workflow_event(event, accumulated_reasoning)
            if stream_event is not None:
                events_to_emit = stream_event if isinstance(stream_event, list) else [stream_event]
                for se in events_to_emit:
                    se.workflow_id = session.workflow_id
                    log_line = _log_stream_event(se, session.workflow_id)
                    if log_line:
                        se.log_line = log_line
                    yield se.to_sse_dict()

    except Exception as e:
        has_error = True
        error_message = str(e)
        logger.error(
            f"Workflow stream error: workflow_id={session.workflow_id}, error={error_message}",
            exc_info=True,
        )

        # Yield error event with partial reasoning flag if applicable
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
        # Update session status
        final_status = WorkflowStatus.FAILED if has_error else WorkflowStatus.COMPLETED
        await session_manager.update_status(
            session.workflow_id,
            final_status,
            completed_at=datetime.now(),
        )

        # Log reasoning if configured and accumulated
        if log_reasoning and accumulated_reasoning:
            logger.info(
                f"Workflow reasoning captured: workflow_id={session.workflow_id}, "
                f"reasoning_length={len(accumulated_reasoning)}"
            )

        # Yield done event
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
            f"Workflow stream completed: workflow_id={session.workflow_id}, "
            f"status={final_status.value}, had_error={has_error}"
        )


# =============================================================================
# WebSocket Origin Validation
# =============================================================================


def _validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket connection origin against allowed CORS origins.

    Checks the Origin header against configured allowed origins.
    Localhost connections are permitted when WS_ALLOW_LOCALHOST=true (default).

    Args:
        websocket: The WebSocket connection.

    Returns:
        True if origin is allowed, False otherwise.
    """
    settings = get_settings()
    origin = websocket.headers.get("origin", "")

    # Allow connections without origin header (same-origin, CLI tools, etc.)
    if not origin:
        return True

    # Allow localhost in development mode
    if settings.ws_allow_localhost:
        localhost_patterns = (
            "http://localhost:",
            "http://127.0.0.1:",
            "https://localhost:",
            "https://127.0.0.1:",
        )
        if any(origin.startswith(p) for p in localhost_patterns):
            return True

    # Check against CORS allowed origins
    if "*" in settings.cors_allowed_origins:
        return True

    if origin in settings.cors_allowed_origins:
        return True

    logger.warning(f"WebSocket connection rejected: invalid origin '{_sanitize_log_input(origin)}'")
    return False


# =============================================================================
# Endpoints
# =============================================================================


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint for streaming chat responses.

    Protocol:
    1. Client connects to /ws/chat
    2. Client sends ChatRequest JSON as first message
    3. Server streams StreamEvent JSON messages
    4. Client can send {"type": "cancel"} to abort
    5. Server sends {"type": "done"} and closes connection

    Args:
        websocket: The WebSocket connection.
    """
    # Validate origin before accepting connection
    if not _validate_websocket_origin(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Get dependencies from app state
    app = websocket.app
    session_manager = app.state.session_manager if hasattr(app.state, "session_manager") else None
    conversation_manager = (
        app.state.conversation_manager if hasattr(app.state, "conversation_manager") else None
    )
    workflow = app.state.workflow if hasattr(app.state, "workflow") else None

    # Fallback to global instances if not in app state
    if session_manager is None:
        from agentic_fleet.app.dependencies import get_session_manager

        session_manager = get_session_manager()
    if conversation_manager is None:
        from agentic_fleet.app.dependencies import get_conversation_manager

        conversation_manager = get_conversation_manager()
    if workflow is None:
        logger.error("Workflow not available in app state")
        await websocket.send_json(
            {
                "type": "error",
                "error": "Workflow not initialized",
                "timestamp": datetime.now().isoformat(),
            }
        )
        await websocket.close()
        return

    cancel_event = asyncio.Event()
    session: WorkflowSession | None = None
    heartbeat_task: asyncio.Task | None = None
    last_event_ts = datetime.now()
    stream_start_ts = datetime.now()
    max_runtime_seconds = 180

    try:
        # Receive initial chat request with a timeout to avoid hanging sockets
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

        request = ChatRequest(**data)

        msg_preview = request.message[:50] if len(request.message) > 50 else request.message
        sanitized_preview = re.sub(r"[\x00-\x1F\x7F\u2028\u2029]", "", msg_preview)
        logger.info(
            f"WebSocket chat request received: message_preview={sanitized_preview}, "
            f"reasoning_effort={request.reasoning_effort}, "
            f"conversation_id={request.conversation_id}"
        )

        # Save user message if conversation_id is provided
        if request.conversation_id:
            conversation_manager.add_message(
                request.conversation_id,
                MessageRole.USER,
                request.message,
                author="User",
            )

        # Get or create conversation thread for multi-turn context
        conversation_thread = await _get_or_create_thread(request.conversation_id)

        # Create session (will raise 429 if limit exceeded)
        try:
            session = await session_manager.create_session(
                task=request.message,
                reasoning_effort=request.reasoning_effort,
            )
        except HTTPException as e:
            error_type = StreamEventType.ERROR
            error_category, error_ui_hint = classify_event(error_type)
            error_event = StreamEvent(
                type=error_type,
                error=e.detail,
                category=error_category,
                ui_hint=error_ui_hint,
                workflow_id=session.workflow_id if session else None,
            )
            if session:
                error_event.log_line = _log_stream_event(error_event, session.workflow_id)
            await websocket.send_json(error_event.to_sse_dict())
            await websocket.close()
            return

        # Send a connection acknowledgement immediately after session creation
        connected_type = StreamEventType.CONNECTED
        connected_category, connected_ui_hint = classify_event(connected_type)
        connected_event = StreamEvent(
            type=connected_type,
            message="Connected",
            data={"conversation_id": request.conversation_id},
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

        # Start background task to listen for cancel messages
        async def listen_for_cancel() -> None:
            try:
                while not cancel_event.is_set():
                    try:
                        msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.25)
                        if msg.get("type") == "cancel":
                            logger.info(f"Cancel requested for workflow: {session.workflow_id}")
                            cancel_event.set()
                            break
                    except TimeoutError:
                        continue
            except WebSocketDisconnect:
                cancel_event.set()
            except Exception:
                cancel_event.set()

        cancel_task = asyncio.create_task(listen_for_cancel())

        # Check if reasoning logging is enabled (from config)
        log_reasoning = False
        if hasattr(workflow, "config") and workflow.config:
            config = workflow.config
            if hasattr(config, "logging") and hasattr(config.logging, "log_reasoning"):
                log_reasoning = bool(config.logging.log_reasoning)

        # Stream events
        full_response = ""
        last_author: str | None = None
        last_agent_id: str | None = None
        saw_completed = False
        saw_done = False

        try:
            async for event_data in _event_generator(
                workflow,
                session,
                session_manager,
                log_reasoning,
                request.reasoning_effort,
                cancel_event,
                thread=conversation_thread,
            ):
                # Idle timeout safeguard
                if (datetime.now() - last_event_ts).total_seconds() > 60:
                    timeout_type = StreamEventType.ERROR
                    timeout_category, timeout_ui_hint = classify_event(timeout_type)
                    timeout_event = StreamEvent(
                        type=timeout_type,
                        error="Stream idle timeout",
                        category=timeout_category,
                        ui_hint=timeout_ui_hint,
                        workflow_id=session.workflow_id,
                    )
                    timeout_event.log_line = _log_stream_event(timeout_event, session.workflow_id)
                    await websocket.send_json(timeout_event.to_sse_dict())
                    cancel_event.set()
                    break

                # Max runtime safeguard
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
                    timeout_event.log_line = _log_stream_event(timeout_event, session.workflow_id)
                    await websocket.send_json(timeout_event.to_sse_dict())
                    cancel_event.set()
                    break

                if cancel_event.is_set():
                    # Send cancelled event before breaking
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
                    # Also emit DONE so clients stop cleanly
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

                # Track author/agent metadata for final conversation save
                author = event_data.get("author") or event_data.get("agent_id")
                if author:
                    last_author = event_data.get("author") or last_author or author
                    last_agent_id = event_data.get("agent_id") or last_agent_id

                # Capture response content for history from various event types
                if event_type == StreamEventType.RESPONSE_DELTA.value:
                    full_response += event_data.get("delta", "")
                elif event_type == StreamEventType.RESPONSE_COMPLETED.value:
                    completed_msg = event_data.get("message", "")
                    if completed_msg:
                        full_response = completed_msg
                    last_author = event_data.get("author") or last_author
                    saw_completed = True
                elif event_type in (
                    StreamEventType.AGENT_OUTPUT.value,
                    StreamEventType.AGENT_MESSAGE.value,
                ):
                    agent_msg = event_data.get("message", "")
                    if agent_msg:
                        full_response = agent_msg

                if event_type == StreamEventType.DONE.value:
                    saw_done = True

                await websocket.send_json(event_data)
                last_event_ts = datetime.now()

                # If the backend signals stream completion, stop reading further and close promptly
                if event_type == StreamEventType.DONE.value:
                    break
        finally:
            cancel_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_task

        # Ensure a final answer is always sent (markdown-friendly text) and scored
        if not saw_completed:
            final_text = (
                full_response.strip() or "Sorry, I couldn't produce a final answer this time."
            )
            quality = score_answer_with_dspy(request.message, final_text)
            completed_type = StreamEventType.RESPONSE_COMPLETED
            comp_category, comp_ui = classify_event(completed_type)
            completed_event = StreamEvent(
                type=completed_type,
                message=final_text,
                author=last_author,
                agent_id=last_agent_id,
                data=quality,
                quality_score=quality.get("quality_score"),
                quality_flag=quality.get("quality_flag"),
                category=comp_category,
                ui_hint=comp_ui,
                workflow_id=session.workflow_id,
            )
            completed_event.log_line = _log_stream_event(completed_event, session.workflow_id)
            await websocket.send_json(completed_event.to_sse_dict())
        else:
            # If we already sent response.completed but lacked quality, attach a scored echo
            # Note: We skip logging this event to avoid duplicate "Response:" log entries
            if full_response.strip():
                quality = score_answer_with_dspy(request.message, full_response)
                completed_type = StreamEventType.RESPONSE_COMPLETED
                comp_category, comp_ui = classify_event(completed_type)
                quality_event = StreamEvent(
                    type=completed_type,
                    message=full_response,
                    author=last_author,
                    agent_id=last_agent_id,
                    data=quality,
                    quality_score=quality.get("quality_score"),
                    quality_flag=quality.get("quality_flag"),
                    category=comp_category,
                    ui_hint=comp_ui,
                    workflow_id=session.workflow_id,
                )
                # Skip logging to avoid duplicate "Response:" entries - original was already logged
                await websocket.send_json(quality_event.to_sse_dict())

        if not saw_done:
            done_category, done_ui_hint = classify_event(StreamEventType.DONE)
            done_event = StreamEvent(
                type=StreamEventType.DONE,
                category=done_category,
                ui_hint=done_ui_hint,
                workflow_id=session.workflow_id,
            )
            await websocket.send_json(done_event.to_sse_dict())

        # Save assistant message on completion if conversation_id provided
        if request.conversation_id and full_response:
            conversation_manager.add_message(
                request.conversation_id,
                MessageRole.ASSISTANT,
                full_response,
                author=last_author,
                agent_id=last_agent_id,
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        with contextlib.suppress(Exception):
            error_type = StreamEventType.ERROR
            error_category, error_ui_hint = classify_event(error_type)
            error_event = StreamEvent(
                type=error_type,
                error=str(e),
                category=error_category,
                ui_hint=error_ui_hint,
                workflow_id=session.workflow_id if session else None,
            )
            if session:
                error_event.log_line = _log_stream_event(error_event, session.workflow_id)
            await websocket.send_json(error_event.to_sse_dict())
    finally:
        # Update session status if cancelled
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


@router.get(
    "/sessions",
    summary="List active workflow sessions",
    description="Returns a list of all workflow sessions (active and recent).",
)
async def list_sessions(
    session_manager: SessionManagerDep,
) -> list[WorkflowSession]:
    """List all workflow sessions.

    Args:
        session_manager: Injected session manager.

    Returns:
        List of workflow sessions.
    """
    return await session_manager.list_sessions()


@router.get(
    "/sessions/{workflow_id}",
    summary="Get workflow session details",
    description="Returns details for a specific workflow session.",
)
async def get_session(
    workflow_id: str,
    session_manager: SessionManagerDep,
) -> WorkflowSession:
    """Get a specific workflow session.

    Args:
        workflow_id: The workflow ID.
        session_manager: Injected session manager.

    Returns:
        The workflow session.

    Raises:
        HTTPException: If session not found.
    """
    session = await session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )
    return session


@router.delete(
    "/sessions/{workflow_id}",
    summary="Cancel a workflow session",
    description="Cancels a running workflow session. Has no effect on completed sessions.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_session(
    workflow_id: str,
    session_manager: SessionManagerDep,
) -> None:
    """Cancel a running workflow session.

    Args:
        workflow_id: The workflow ID to cancel.
        session_manager: Injected session manager.

    Raises:
        HTTPException: If session not found.
    """
    session = await session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )

    # Only cancel if running
    if session.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING):
        await session_manager.update_status(
            workflow_id,
            WorkflowStatus.CANCELLED,
            completed_at=datetime.now(),
        )
        sanitized_workflow_id = workflow_id.replace("\n", "").replace("\r", "")
        logger.info(f"Cancelled workflow session: workflow_id={sanitized_workflow_id}")
