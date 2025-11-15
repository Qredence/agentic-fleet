"""Delegated execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

from ...utils.logger import setup_logger
from ..exceptions import AgentExecutionError

if TYPE_CHECKING:
    from ...utils.progress import ProgressCallback

logger = setup_logger(__name__)


async def execute_delegated(
    agents: dict[str, Any],
    agent_name: str,
    task: str,
) -> str:
    """Delegate the task to a single agent without streaming."""
    agent = agents.get(agent_name)
    if not agent:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=RuntimeError(f"Agent '{agent_name}' not found"),
        )

    response = await agent.run(task)
    return str(response)


async def execute_delegated_streaming(
    agents: dict[str, Any],
    agent_name: str,
    task: str,
    progress_callback: ProgressCallback | None = None,
):
    """Delegate task to single agent with streaming."""
    if agent_name not in agents:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=RuntimeError(f"Agent '{agent_name}' not found"),
        )

    if progress_callback:
        progress_callback.on_progress(f"Executing {agent_name}...")
    yield MagenticAgentMessageEvent(
        agent_id=agent_name,
        message=ChatMessage(role=Role.ASSISTANT, text="Processing task..."),
    )

    response = await agents[agent_name].run(task)

    if progress_callback:
        progress_callback.on_progress(f"{agent_name} completed")
    yield MagenticAgentMessageEvent(
        agent_id=agent_name,
        message=ChatMessage(role=Role.ASSISTANT, text=f"Completed: {response!s}"),
    )

    # Yield final result
    yield WorkflowOutputEvent(
        data={"result": str(response)},
        source_executor_id="delegated_execution",
    )
