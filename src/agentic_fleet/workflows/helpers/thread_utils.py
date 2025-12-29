"""Thread utility functions for workflow execution.

This module contains helper functions for working with agent-framework
AgentThread objects, extracted from supervisor.py to reduce complexity.
"""

from __future__ import annotations

from typing import Any

from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)


def thread_has_history(thread: Any | None) -> bool:
    """Best-effort check for whether an agent-framework AgentThread has prior messages.

    We intentionally avoid importing/depending on AgentThread internals here so this
    remains compatible across agent-framework versions.

    Args:
        thread: An agent-framework AgentThread instance, or None

    Returns:
        True if the thread appears to have message history, False otherwise
    """
    if thread is None:
        return False

    # Common case: AgentThread supports __len__.
    try:
        return len(thread) > 0  # type: ignore[arg-type]
    except Exception:
        pass

    # agent-framework AgentThread does not implement __len__ but may expose
    # messages via a ChatMessageStore on `message_store`.
    #
    # We keep this best-effort and defensive to remain compatible across
    # agent-framework versions and custom stores.
    store = getattr(thread, "message_store", None)
    if store is None:
        store = getattr(thread, "_message_store", None)
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

    # Service-managed threads: if a service thread id is set, treat this as
    # multi-turn context and avoid stateless fast-path.
    service_thread_id = getattr(thread, "service_thread_id", None) or getattr(
        thread, "_service_thread_id", None
    )
    if service_thread_id:
        return True

    # Last-resort: if the thread is initialized, conservatively assume it may
    # have context (better to skip fast-path than ignore history).
    if bool(getattr(thread, "is_initialized", False)):
        return True

    # Common attribute names across thread implementations.
    for attr in ("messages", "history", "_messages"):
        msgs = getattr(thread, attr, None)
        if msgs is None:
            continue
        try:
            return len(msgs) > 0  # type: ignore[arg-type]
        except Exception:
            continue

    # Fallback: try calling methods that might return an iterable of messages.
    for method_name in ("get_messages", "to_messages", "iter_messages"):
        method = getattr(thread, method_name, None)
        if not callable(method):
            continue
        try:
            maybe_msgs = method()
        except TypeError:
            # Method likely requires args we don't know.
            continue
        except Exception:
            continue
        try:
            it = iter(maybe_msgs)  # type: ignore[arg-type]
        except Exception:
            continue
        try:
            next(it)
            return True
        except StopIteration:
            return False
        except Exception:
            continue

    return False
