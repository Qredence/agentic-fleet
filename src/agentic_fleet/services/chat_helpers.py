"""Shared helper functions for chat streaming services.

This module contains helper functions shared by both WebSocket and SSE chat streaming
implementations to avoid code duplication and maintain consistency.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
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


from agentic_fleet.api.events.mapping import classify_event
from agentic_fleet.models import StreamEvent, StreamEventType
from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)

# In-memory storage for conversation threads (per conversation_id).
# Uses a bounded, TTL-aware cache to prevent memory leaks.
_MAX_THREADS = 100  # Maximum number of conversation threads to keep.
_TTL_SECONDS = 3600  # Time-to-live: expire threads after 1 hour of inactivity.

# Maps conversation_id -> (AgentThread, last_access_timestamp)
_conversation_threads: OrderedDict[str, tuple[AgentThread, float]] = OrderedDict()
_threads_lock: asyncio.Lock = asyncio.Lock()


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


def _has_messages(container: Any, attrs: Iterable[str]) -> bool:
    if container is None:
        return False

    for attr in attrs:
        candidate = getattr(container, attr, None)
        if candidate is None:
            continue
        try:
            if len(candidate) > 0:  # type: ignore[arg-type]
                return True
        except TypeError:
            continue

    try:
        return len(container) > 0  # type: ignore[arg-type]
    except TypeError:
        return False


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

    store = getattr(thread, "message_store", None) or getattr(thread, "_message_store", None)
    if _has_messages(store, ("messages", "_messages", "history")):
        return True

    return _has_messages(thread, ("messages", "history", "_messages"))


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


def _format_response_delta(event: StreamEvent, short_id: str) -> str | None:
    # Only log first 80 chars of deltas to avoid flooding.
    delta = event.delta or ""
    delta_preview = delta[:80]
    if not delta_preview:
        return None
    # Only add ellipsis if truncation actually occurred
    suffix = "..." if len(delta) > 80 else ""
    return f"[{short_id}] ✏️  delta: {delta_preview}{suffix}"


def _format_response_completed(event: StreamEvent, short_id: str) -> str:
    message = event.message or ""
    result_preview = message[:100]
    # Only add ellipsis if truncation actually occurred
    suffix = "..." if len(message) > 100 else ""
    return f"[{short_id}] ✅ Response: {result_preview}{suffix}"


def _format_orchestrator_thought(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 💭 {event.kind}: {event.message}"


def _format_orchestrator_message(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 📢 {event.message}"


def _format_reasoning_delta(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🧠 reasoning delta"


def _format_reasoning_completed(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🧠 Reasoning complete"


def _format_error(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] ❌ Error: {event.error}"


def _format_agent_start(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🤖 Agent started: {event.agent_id}"


def _format_agent_complete(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🤖 Agent complete: {event.agent_id}"


def _format_cancelled(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] ⏹️ Cancelled by client"


def _format_done(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🏁 Stream completed"


def _format_connected(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] 🔌 WebSocket connected"


def _format_heartbeat(event: StreamEvent, short_id: str) -> str:
    return f"[{short_id}] ♥ heartbeat"


def _log_stream_event(event: StreamEvent, workflow_id: str) -> str | None:
    """Log a stream event to the console in real-time and return the log line."""
    event_type = event.type.value
    short_id = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

    log_specs: dict[
        StreamEventType,
        tuple[Callable[[StreamEvent, str], str | None], int],
    ] = {
        StreamEventType.ORCHESTRATOR_MESSAGE: (_format_orchestrator_message, logging.INFO),
        StreamEventType.ORCHESTRATOR_THOUGHT: (_format_orchestrator_thought, logging.INFO),
        StreamEventType.RESPONSE_DELTA: (_format_response_delta, logging.DEBUG),
        StreamEventType.RESPONSE_COMPLETED: (_format_response_completed, logging.INFO),
        StreamEventType.REASONING_DELTA: (_format_reasoning_delta, logging.DEBUG),
        StreamEventType.REASONING_COMPLETED: (_format_reasoning_completed, logging.INFO),
        StreamEventType.ERROR: (_format_error, logging.ERROR),
        StreamEventType.AGENT_START: (_format_agent_start, logging.INFO),
        StreamEventType.AGENT_COMPLETE: (_format_agent_complete, logging.INFO),
        StreamEventType.CANCELLED: (_format_cancelled, logging.INFO),
        StreamEventType.DONE: (_format_done, logging.INFO),
        StreamEventType.CONNECTED: (_format_connected, logging.DEBUG),
        StreamEventType.HEARTBEAT: (_format_heartbeat, logging.DEBUG),
    }

    log_line: str | None = None
    log_spec = log_specs.get(event.type)
    if log_spec is None:
        log_line = f"[{short_id}] {event_type}"
        logger.debug(log_line)
        return log_line

    formatter, level = log_spec
    log_line = formatter(event, short_id)
    if log_line:
        logger.log(level, log_line)
    return log_line


def create_stream_event(
    event_type: StreamEventType,
    workflow_id: str | None = None,
    *,
    kind: str | None = None,
    message: str | None = None,
    error: str | None = None,
    delta: str | None = None,
    reasoning: str | None = None,
    agent_id: str | None = None,
    author: str | None = None,
    role: str | None = None,
    data: dict[str, Any] | None = None,
    reasoning_partial: bool | None = None,
    quality_score: float | None = None,
    quality_flag: str | None = None,
) -> StreamEvent:
    """Create a StreamEvent with automatic classification and logging.

    Args:
        event_type: The type of stream event.
        workflow_id: Optional workflow identifier.
        kind: Optional event kind (analysis, routing, quality, etc.).
        message: Optional message content.
        error: Optional error message.
        delta: Optional incremental text.
        reasoning: Optional reasoning text.
        agent_id: Optional agent identifier.
        author: Optional author name.
        role: Optional role (user/assistant/system).
        data: Optional additional data dictionary.
        reasoning_partial: Optional flag for partial reasoning.
        quality_score: Optional quality score.
        quality_flag: Optional quality flag.

    Returns:
        StreamEvent instance with category, ui_hint, and log_line set.
    """
    category, ui_hint = classify_event(event_type, kind)
    event = StreamEvent(
        type=event_type,
        workflow_id=workflow_id,
        kind=kind,
        message=message,
        error=error,
        delta=delta,
        reasoning=reasoning,
        agent_id=agent_id,
        author=author,
        role=role,
        data=data,
        reasoning_partial=reasoning_partial,
        quality_score=quality_score,
        quality_flag=quality_flag,
        category=category,
        ui_hint=ui_hint,
    )
    if workflow_id:
        event.log_line = _log_stream_event(event, workflow_id)
    return event


@dataclass
class ResponseState:
    """State tracking for response accumulation during streaming."""

    response_text: str = ""
    response_delta_text: str = ""  # Used by websocket implementation
    last_agent_text: str = ""
    last_author: str | None = None
    last_agent_id: str | None = None
    response_completed_emitted: bool = False
    saw_done: bool = False

    def update_from_event(self, event_data: dict[str, Any]) -> None:
        """Update state from a stream event dictionary."""
        event_type = event_data.get("type")
        author = event_data.get("author") or event_data.get("agent_id")
        if author:
            self.last_author = event_data.get("author") or self.last_author or author
            self.last_agent_id = event_data.get("agent_id") or self.last_agent_id

        if event_type == StreamEventType.RESPONSE_DELTA.value:
            # Accumulate deltas in both fields for compatibility
            self.response_delta_text += event_data.get("delta", "")
            self.response_text = self.response_delta_text
        elif event_type == StreamEventType.RESPONSE_COMPLETED.value:
            completed_msg = event_data.get("message", "")
            if completed_msg:
                self.response_text = completed_msg
            self.last_author = event_data.get("author") or self.last_author
            self.response_completed_emitted = True
        elif event_type in (
            StreamEventType.AGENT_OUTPUT.value,
            StreamEventType.AGENT_MESSAGE.value,
        ):
            agent_msg = event_data.get("message", "")
            if agent_msg:
                self.last_agent_text = agent_msg

        if event_type == StreamEventType.DONE.value:
            self.saw_done = True

    def get_final_text(self) -> str:
        """Get final response text with fallback."""
        return (
            self.response_text.strip()
            or self.last_agent_text.strip()
            or "Sorry, I couldn't produce a final answer this time."
        )


def create_checkpoint_storage(
    enable_checkpointing: bool, is_resume: bool, checkpoint_dir: str | None = None
) -> Any | None:
    """Create checkpoint storage if needed.

    Args:
        enable_checkpointing: Whether checkpointing is enabled.
        is_resume: Whether this is a resume operation.
        checkpoint_dir: Optional checkpoint directory path. Defaults to ".var/checkpoints" if not provided.

    Returns:
        CheckpointStorage instance or None.
    """
    if not (enable_checkpointing or is_resume):
        return None

    try:
        from agent_framework._workflows import (
            FileCheckpointStorage,
            InMemoryCheckpointStorage,
        )

        # Use provided checkpoint_dir or default to ".var/checkpoints"
        storage_dir = checkpoint_dir or ".var/checkpoints"
        try:
            from pathlib import Path

            Path(storage_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            storage_dir = ""

        if storage_dir:
            return FileCheckpointStorage(storage_dir)
        else:
            return InMemoryCheckpointStorage()
    except Exception:
        return None


__all__ = [
    "ResponseState",
    "_get_or_create_thread",
    "_hydrate_thread_from_conversation",
    "_log_stream_event",
    "_message_role_value",
    "_prefer_service_thread_mode",
    "_sanitize_log_input",
    "_thread_has_any_messages",
    "create_checkpoint_storage",
    "create_stream_event",
]
