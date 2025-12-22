"""Shared helper functions for chat streaming services.

This module contains helper functions shared by both WebSocket and SSE chat streaming
implementations to avoid code duplication and maintain consistency.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import time
from collections import OrderedDict
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


__all__ = [
    "_get_or_create_thread",
    "_hydrate_thread_from_conversation",
    "_log_stream_event",
    "_message_role_value",
    "_prefer_service_thread_mode",
    "_sanitize_log_input",
    "_thread_has_any_messages",
]
