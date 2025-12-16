"""Delegated execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework._agents import ChatAgent
from agent_framework._threads import AgentThread
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..exceptions import AgentExecutionError
from ..models import MagenticAgentMessageEvent
from .base import (
    _extract_tool_usage,
    _get_agent,
    create_agent_event,
    create_system_event,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ...utils.progress import ProgressCallback
    from ..context import SupervisorContext

logger = setup_logger(__name__)


class DelegatedExecutionStrategy:
    """Execute a task via a single delegated agent."""

    mode = ExecutionMode.DELEGATED

    async def execute(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Execute the routing decision without streaming."""
        agents_map = context.agents or {}
        agent_name = routing.assigned_to[0] if routing.assigned_to else ""
        return await execute_delegated(
            agents_map,
            agent_name,
            task,
            thread=context.conversation_thread,
        )

    async def stream(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
        """Stream execution events for the routing decision."""
        agents_map = context.agents or {}
        agent_name = routing.assigned_to[0] if routing.assigned_to else ""
        async for event in execute_delegated_streaming(
            agents_map,
            agent_name,
            task,
            progress_callback=context.progress_callback,
            thread=context.conversation_thread,
        ):
            yield event


async def execute_delegated(
    agents: dict[str, ChatAgent],
    agent_name: str,
    task: str,
    *,
    thread: AgentThread | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Delegate the task to a single agent without streaming."""
    agent = _get_agent(agents, agent_name)
    if not agent:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=RuntimeError(f"Agent '{agent_name}' not found"),
        )

    try:
        if thread is None:
            response = await agent.run(task)
        else:
            response = await agent.run(task, thread=thread)
    except Exception as exc:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=exc,
        ) from exc
    usage = _extract_tool_usage(response)
    return str(response), usage


async def execute_delegated_streaming(
    agents: dict[str, ChatAgent],
    agent_name: str,
    task: str,
    progress_callback: ProgressCallback | None = None,
    thread: AgentThread | None = None,
) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
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

    try:
        if thread is None:
            response = await agents[agent_name].run(task)
        else:
            response = await agents[agent_name].run(task, thread=thread)
    except Exception as exc:
        if progress_callback:
            progress_callback.on_error(f"{agent_name} failed", exc)
        error_text = f"[{agent_name} failed: {exc!s}]"
        yield create_agent_event(
            stage="execution",
            event="agent.error",
            agent=agent_name,
            text=f"{agent_name} failed delegated execution",
            payload={"error": str(exc)},
        )
        msg = ChatMessage(
            role=Role.ASSISTANT,
            text=error_text,
            additional_properties={"agent": agent_name, "error": str(exc)},
        )
        yield WorkflowOutputEvent(
            data=[msg],
            source_executor_id="delegated_execution",
        )
        return

    if progress_callback:
        progress_callback.on_progress(f"{agent_name} completed")
    result_text = str(response)
    # Yield the actual agent output with full content
    yield create_agent_event(
        stage="execution",
        event="agent.output",
        agent=agent_name,
        text=result_text,
        payload={
            "output": result_text,
            "agent": agent_name,
        },
    )
    yield create_agent_event(
        stage="execution",
        event="agent.completed",
        agent=agent_name,
        text=f"{agent_name} completed delegated execution",
        payload={"result_preview": result_text[:200]},
    )

    # Yield final result
    metadata = {"agent": agent_name}
    msg = ChatMessage(role=Role.ASSISTANT, text=result_text, additional_properties=metadata)
    summary_event = WorkflowOutputEvent(
        data=[msg],
        source_executor_id="delegated_execution",
    )
    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text=f"{agent_name} result ready",
        payload={"agent": agent_name},
    )
    yield summary_event
