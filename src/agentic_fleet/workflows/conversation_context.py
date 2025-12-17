"""Conversation-context helpers for multi-turn workflows.

The UI may send very short follow-up inputs (e.g., quick-replies like
"academic" or "popular, intermediate"). Those strings are often ambiguous
without the preceding assistant question.

This module provides a compact rendering of recent messages from an
agent-framework AgentThread so analysis/routing can interpret these follow-ups
in context.
"""

from __future__ import annotations

from typing import Any


def _is_unittest_mock(obj: Any) -> bool:
    """Return True for unittest.mock objects.

    We avoid introspecting mocks as if they were real AgentThread/message stores.
    """

    try:
        return obj is not None and obj.__class__.__module__.startswith("unittest.mock")
    except Exception:
        return False


def _get_message_store(thread: Any) -> Any | None:
    if thread is None:
        return None
    if _is_unittest_mock(thread):
        return None
    store = getattr(thread, "message_store", None)
    if store is not None:
        return None if _is_unittest_mock(store) else store
    return getattr(thread, "_message_store", None)


def _get_messages_list(thread: Any) -> list[Any]:
    """Best-effort extraction of message objects from an AgentThread."""

    store = _get_message_store(thread)
    if store is None:
        return []

    raw = getattr(store, "messages", None)
    if raw is None:
        return []

    if _is_unittest_mock(raw):
        return []

    # agent-framework usually stores a list-like `messages`.
    try:
        return list(raw)
    except TypeError:
        # Some message stores are not directly iterable.
        return []


def _coerce_role(msg: Any) -> str:
    role = getattr(msg, "role", None)
    if role is None and isinstance(msg, dict):
        role = msg.get("role")
    # Support enums (e.g., MessageRole.USER) by using `.value` when present.
    # If `.value` is not present, use the original `role` object as-is.
    role_value = getattr(role, "value", role)
    return str(role_value or "").strip().lower()


def _coerce_text(msg: Any) -> str:
    text = getattr(msg, "text", None)
    # Persisted conversation messages use `content` instead of `text`.
    if text is None:
        text = getattr(msg, "content", None)
    if text is None and isinstance(msg, dict):
        text = msg.get("text")
        if text is None:
            text = msg.get("content")
    return str(text or "").strip()


def render_conversation_context_from_messages(
    messages: list[Any],
    *,
    current_user_input: str | None,
    max_messages: int,
    max_chars: int,
) -> str:
    """Render a compact context string from a message list.

    This is useful when AgentThread-local history is unavailable (e.g. when
    using service-managed threads that do not expose a local message store).
    """

    if not messages or max_messages <= 0 or max_chars <= 0:
        return ""

    current_user_input_s = (current_user_input or "").strip()

    pairs: list[tuple[str, str]] = []
    for msg in messages:
        role = _coerce_role(msg)
        if role not in {"user", "assistant"}:
            continue
        text = _coerce_text(msg)
        if not text:
            continue
        pairs.append((role, text))

    if not pairs:
        return ""

    # Drop trailing current user input if already present.
    while pairs and pairs[-1][0] == "user":
        if not current_user_input_s:
            break
        last_user_text_stripped = pairs[-1][1].strip()
        if last_user_text_stripped == current_user_input_s:
            pairs.pop()
            continue
        break

    if not pairs:
        return ""

    pairs = pairs[-max_messages:]
    lines: list[str] = []
    for role, text in pairs:
        prefix = "User" if role == "user" else "Assistant"
        cleaned = " ".join(text.split())
        lines.append(f"{prefix}: {cleaned}")

    rendered = "\n".join(lines).strip()
    if not rendered:
        return ""

    if len(rendered) > max_chars:
        rendered = rendered[-max_chars:]
        rendered = "…" + rendered.lstrip()

    return rendered.strip()


def render_conversation_context(
    thread: Any,
    *,
    current_user_input: str | None,
    max_messages: int,
    max_chars: int,
) -> str:
    """Render a compact, recent conversation context string.

    Notes:
        - Includes only user/assistant messages.
        - Excludes the current user input if it's already present as the last user message.
        - Truncates to the last `max_chars` characters, biasing toward the most recent content.
    """

    if thread is None or max_messages <= 0 or max_chars <= 0:
        return ""

    current_user_input_s = (current_user_input or "").strip() or None

    return render_conversation_context_from_messages(
        _get_messages_list(thread),
        current_user_input=current_user_input_s,
        max_messages=max_messages,
        max_chars=max_chars,
    )
