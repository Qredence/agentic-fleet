"""Delegated execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ..exceptions import AgentExecutionError
from .streaming_events import create_agent_event, create_system_event

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
    yield create_agent_event(
        stage="execution",
        event="agent.start",
        agent=agent_name,
        text=f"{agent_name} started delegated execution",
        payload={"task_preview": task[:120]},
    )

    response = await agents[agent_name].run(task)

    if progress_callback:
        progress_callback.on_progress(f"{agent_name} completed")
    result_text = str(response)
    yield create_agent_event(
        stage="execution",
        event="agent.completed",
        agent=agent_name,
        text=f"{agent_name} completed delegated execution",
        payload={"result_preview": result_text[:200]},
    )

    # Yield final result
    summary_event = WorkflowOutputEvent(
        data={
            "result": result_text,
            "agent": agent_name,
        },
        source_executor_id="delegated_execution",
    )
    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text=f"{agent_name} result ready",
        payload={"agent": agent_name},
    )
    yield summary_event
