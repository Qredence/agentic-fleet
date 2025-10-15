"""Event callbacks for Magentic workflow observability."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agenticfleet.core.logging import get_logger

if TYPE_CHECKING:
    from agent_framework import ChatMessage

logger = get_logger(__name__)


async def streaming_agent_response_callback(message: Any) -> None:
    """
    Stream agent responses to logs for observability.

    Args:
        message: MagenticResponseMessage from a participant agent.
    """
    agent_name = getattr(message, "agent_name", "unknown")
    content = getattr(message, "content", str(message))

    logger.info(f"[Fleet] Agent '{agent_name}' response: {content[:200]}...")


async def plan_creation_callback(ledger: Any) -> None:
    """
    Log plan creation and facts gathered by the manager.

    Args:
        ledger: MagenticTaskLedger with plan and facts.
    """
    plan = getattr(ledger, "plan", "No plan")
    facts = getattr(ledger, "facts", "No facts")

    logger.info("[Fleet] Plan created:")
    logger.info(f"  Facts: {facts}")
    logger.info(f"  Plan: {plan}")


async def progress_ledger_callback(ledger: Any) -> None:
    """
    Track progress evaluation and next actions.

    Args:
        ledger: MagenticProgressLedger with status and next speaker.
    """
    is_satisfied = getattr(ledger, "is_request_satisfied", {})
    is_loop = getattr(ledger, "is_in_loop", {})
    next_speaker = getattr(ledger, "next_speaker", "unknown")
    instruction = getattr(ledger, "instruction", "")

    logger.info("[Fleet] Progress evaluation:")
    logger.info(f"  Request satisfied: {is_satisfied}")
    logger.info(f"  In loop: {is_loop}")
    logger.info(f"  Next speaker: {next_speaker}")
    logger.info(f"  Instruction: {instruction[:100]}...")


async def notice_callback(message: str) -> None:
    """
    Log notice messages from the orchestrator.

    Args:
        message: Notice message string.
    """
    logger.info(f"[Fleet] Notice: {message}")


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
