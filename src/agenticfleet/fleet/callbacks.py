"""Event callbacks for Magentic workflow observability."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from agenticfleet.cli.ui import AgentMessage, get_console_ui
from agenticfleet.core.logging import get_logger


def _coerce_lines(value: Any) -> list[str]:
    """Convert various ledger data structures into readable bullet lines."""

    if value is None:
        return []

    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]

    if isinstance(value, dict):
        return [f"{key}: {val}" for key, val in value.items()]

    items = value if isinstance(value, list | tuple | set) else [value]
    lines: list[str] = []

    for item in items:
        if item is None:
            continue
        for attr in ("summary", "description", "text", "content", "instruction"):
            if hasattr(item, attr):
                text = getattr(item, attr)
                if isinstance(text, str) and text.strip():
                    lines.append(text.strip())
                    break
        else:
            text = str(item).strip()
            if text and not text.startswith("WorkflowStatusEvent"):
                lines.append(text)

    return lines


if TYPE_CHECKING:
    from agent_framework import ChatMessage

logger = get_logger(__name__)

_AGENT_STREAM_CACHE_LOCAL = threading.local()


def _extract_agent_name(message: Any) -> str:
    for attr in ("agent_name", "participant_id", "name", "role"):
        if hasattr(message, attr):
            value = getattr(message, attr)
            if value:
                return str(value)
    return "agent"


def _extract_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    for attr in ("delta", "text", "content", "message"):
        if hasattr(message, attr):
            value = getattr(message, attr)
            if isinstance(value, str):
                return value
            if isinstance(value, list | tuple):
                parts = [str(part) for part in value if str(part).strip()]
                if parts:
                    return "\n".join(parts)
    return str(message)


async def agent_delta_callback(event: Any) -> None:
    """Buffer streaming deltas without flooding the console."""

    agent_name = _extract_agent_name(event)
    text = _extract_text(event).strip()
    if not text:
        return
    if not hasattr(_AGENT_STREAM_CACHE_LOCAL, "cache"):
        _AGENT_STREAM_CACHE_LOCAL.cache = {}
    cache = _AGENT_STREAM_CACHE_LOCAL.cache
    cache.setdefault(agent_name, []).append(text)


async def agent_message_callback(message: Any) -> None:
    """Display the final aggregated agent response."""

    agent_name = _extract_agent_name(message)
    final_text = _extract_text(message).strip()
    cache = getattr(_AGENT_STREAM_CACHE_LOCAL, "cache", {})
    buffered = cache.pop(agent_name, []) if cache else []
    if buffered:
        buffered.append(final_text)
        combined = "\n".join(part for part in buffered if part)
    else:
        combined = final_text

    if not combined:
        return

    logger.info(f"[Fleet] Agent '{agent_name}' response: {combined[:200]}...")
    ui = get_console_ui()
    if ui:
        ui.log_agent_message(AgentMessage(agent_name=agent_name, content=combined, mode="response"))


async def plan_creation_callback(ledger: Any) -> None:
    """
    Log plan creation and facts gathered by the manager.

    Args:
        ledger: MagenticTaskLedger with plan and facts.
    """
    plan_lines = _coerce_lines(getattr(ledger, "plan", None))
    facts_lines = _coerce_lines(getattr(ledger, "facts", None))

    logger.info("[Fleet] Plan created:")
    for fact in facts_lines or ["(none)"]:
        logger.info(f"  Fact: {fact}")
    for step in plan_lines or ["(none)"]:
        logger.info(f"  Step: {step}")

    ui = get_console_ui()
    if ui:
        ui.log_plan(facts_lines or ["(none)"], plan_lines or ["(none)"])


async def progress_ledger_callback(ledger: Any) -> None:
    """
    Track progress evaluation and next actions.

    Args:
        ledger: MagenticProgressLedger with status and next speaker.
    """
    is_satisfied = getattr(ledger, "is_request_satisfied", False)
    is_loop = getattr(ledger, "is_in_loop", False)
    next_speaker = getattr(ledger, "next_speaker", "unknown")
    instruction_lines = _coerce_lines(getattr(ledger, "instruction", None))

    logger.info("[Fleet] Progress evaluation:")
    logger.info(f"  Request satisfied: {is_satisfied}")
    logger.info(f"  In loop: {is_loop}")
    logger.info(f"  Next speaker: {next_speaker}")
    if instruction_lines:
        for line in instruction_lines:
            logger.info(f"  Instruction: {line[:100]}")

    ui = get_console_ui()
    if ui:
        status = (
            "Satisfied" if bool(is_satisfied) else ("Looping" if bool(is_loop) else "In progress")
        )
        instruction_text = "\n".join(instruction_lines) if instruction_lines else None
        ui.log_progress(status=status, next_speaker=next_speaker, instruction=instruction_text)


async def notice_callback(message: str) -> None:
    """Display orchestration notices in the CLI."""

    ui = get_console_ui()
    if ui:
        ui.log_notice(message)


async def tool_call_callback(tool_name: str, tool_args: dict[str, Any], result: Any) -> None:
    """
    Log tool calls and results for debugging.

    Args:
        tool_name: Name of the tool being called.
        tool_args: Arguments passed to the tool.
        result: Result returned by the tool.
    """
    logger.debug(f"[Fleet] Tool call: {tool_name}")
    logger.debug(f"  Args: {tool_args}")
    logger.debug(f"  Result: {str(result)[:200]}...")


async def final_answer_callback(message: ChatMessage) -> None:
    """
    Log the final answer being returned to the user.

    Args:
        message: Final ChatMessage from the manager.
    """
    content = getattr(message, "content", str(message))
    logger.info(f"[Fleet] Final answer: {content[:300]}...")

    ui = get_console_ui()
    if ui:
        ui.log_final(str(content))
