"""Parallel execution strategy."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from agent_framework import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ..exceptions import AgentExecutionError
from ..utils import synthesize_results
from .streaming_events import create_agent_event, create_system_event

if TYPE_CHECKING:
    from ...utils.progress import ProgressCallback

logger = setup_logger(__name__)


async def execute_parallel(
    agents: dict[str, Any],
    agent_names: list[str],
    subtasks: list[str],
) -> str:
    """Execute subtasks in parallel without streaming."""
    tasks = []
    valid_agent_names = []

    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        agent = agents.get(agent_name)
        if not agent:
            logger.warning("Skipping unknown agent '%s' during parallel execution", agent_name)
            continue
        tasks.append(agent.run(subtask))
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
    for agent_name, result in zip(valid_agent_names, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Agent '{agent_name}' failed: {result}")
            successful_results.append(f"[{agent_name} failed: {result!s}]")
        else:
            successful_results.append(str(result))

    return synthesize_results(successful_results)


async def execute_parallel_streaming(
    agents: dict[str, Any],
    agent_names: list[str],
    subtasks: list[str],
    progress_callback: ProgressCallback | None = None,
):
    """Execute subtasks in parallel with streaming."""
    tasks = []
    valid_agent_names = []
    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        if agent_name in agents:
            tasks.append(agents[agent_name].run(subtask))
            valid_agent_names.append(agent_name)

    if progress_callback:
        progress_callback.on_progress(
            f"Executing {len(valid_agent_names)} agents in parallel...",
            current=0,
            total=len(valid_agent_names),
        )

    # Yield start events for each agent
    for agent_name, subtask in zip(valid_agent_names, subtasks, strict=False):
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
    yield WorkflowOutputEvent(
        data={
            "result": final_result,
            "agents": valid_agent_names,
        },
        source_executor_id="parallel_execution",
    )
