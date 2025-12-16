"""Parallel execution strategy."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from agent_framework._agents import ChatAgent
from agent_framework._threads import AgentThread
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..exceptions import AgentExecutionError
from ..helpers import synthesize_results
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


class ParallelExecutionStrategy:
    """Execute subtasks concurrently across multiple agents."""

    mode = ExecutionMode.PARALLEL

    async def execute(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Execute the routing decision without streaming."""
        _ = task
        agents_map = context.agents or {}
        return await execute_parallel(
            agents_map,
            list(routing.assigned_to),
            list(routing.subtasks),
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
        _ = task
        agents_map = context.agents or {}
        async for event in execute_parallel_streaming(
            agents_map,
            list(routing.assigned_to),
            list(routing.subtasks),
            progress_callback=context.progress_callback,
            thread=context.conversation_thread,
        ):
            yield event


async def execute_parallel(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    subtasks: list[str],
    *,
    thread: AgentThread | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Execute subtasks in parallel without streaming."""
    tasks = []
    valid_agent_names = []

    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        agent = _get_agent(agents, agent_name)
        if not agent:
            logger.warning("Skipping unknown agent '%s' during parallel execution", agent_name)
            continue
        if thread is None:
            tasks.append(agent.run(subtask))
        else:
            tasks.append(agent.run(subtask, thread=thread))
        valid_agent_names.append(agent_name)

    if not tasks:
        raise AgentExecutionError(
            agent_name="unknown",
            task="parallel execution",
            original_error=RuntimeError("No valid agents available"),
        )

    # Execute with exception handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle exceptions
    successful_results = []
    aggregated_usage = []

    for agent_name, result in zip(valid_agent_names, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Agent '{agent_name}' failed: {result}")
            successful_results.append(f"[{agent_name} failed: {result!s}]")
        else:
            successful_results.append(str(result))
            aggregated_usage.extend(_extract_tool_usage(result))

    return synthesize_results(successful_results), aggregated_usage


async def execute_parallel_streaming(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    subtasks: list[str],
    progress_callback: ProgressCallback | None = None,
    thread: AgentThread | None = None,
) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
    """Execute subtasks in parallel with streaming."""
    tasks = []
    valid_agent_names = []
    valid_subtasks = []
    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        agent = _get_agent(agents, agent_name)
        if agent:
            if thread is None:
                tasks.append(agent.run(subtask))
            else:
                tasks.append(agent.run(subtask, thread=thread))
            valid_agent_names.append(agent_name)
            valid_subtasks.append(subtask)

    if progress_callback:
        progress_callback.on_progress(
            f"Executing {len(valid_agent_names)} agents in parallel...",
            current=0,
            total=len(valid_agent_names),
        )

    # Yield start events for each agent
    for agent_name, subtask in zip(valid_agent_names, valid_subtasks, strict=False):
        yield create_agent_event(
            stage="execution",
            event="agent.start",
            agent=agent_name,
            text=f"{agent_name} starting parallel subtask",
            payload={"subtask": subtask},
        )

    # Execute with exception handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Yield completion events and handle exceptions
    successful_results = []
    for idx, (agent_name, result) in enumerate(zip(valid_agent_names, results, strict=False), 1):
        if progress_callback:
            progress_callback.on_progress(
                f"Agent {agent_name} completed", current=idx, total=len(valid_agent_names)
            )
        if isinstance(result, Exception):
            logger.error(f"Agent '{agent_name}' failed: {result}")
            error_msg = f"[{agent_name} failed: {result!s}]"
            yield create_agent_event(
                stage="execution",
                event="agent.error",
                agent=agent_name,
                text=f"{agent_name} failed during parallel execution",
                payload={"error": str(result)},
            )
            successful_results.append(error_msg)
        else:
            result_text = str(result)
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
            # Also yield completion status
            yield create_agent_event(
                stage="execution",
                event="agent.completed",
                agent=agent_name,
                text=f"{agent_name} completed parallel subtask",
                payload={"result_preview": result_text[:200]},
            )
            successful_results.append(result_text)

    # Yield final synthesized result
    final_result = synthesize_results(successful_results)
    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text="Parallel execution complete",
        payload={"agents": valid_agent_names},
    )

    metadata = {"agents": valid_agent_names}
    msg = ChatMessage(role=Role.ASSISTANT, text=final_result, additional_properties=metadata)
    yield WorkflowOutputEvent(
        data=[msg],
        source_executor_id="parallel_execution",
    )
