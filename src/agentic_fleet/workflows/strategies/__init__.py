"""Execution strategies for the workflow.

This package provides execution strategies for different agent coordination patterns:
- DelegatedExecutionStrategy: Single agent handles the task
- SequentialExecutionStrategy: Agents work one after another with handoffs
- ParallelExecutionStrategy: Multiple agents work simultaneously
- DiscussionExecutionStrategy: Agents collaborate through discussion

Public API also includes run_execution_phase functions for the workflow pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework._workflows import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..models import ExecutionOutcome, MagenticAgentMessageEvent
from .base import ExecutionPhaseError, _extract_tool_usage
from .delegated import (
    DelegatedExecutionStrategy,
    execute_delegated,
    execute_delegated_streaming,
)
from .discussion import DiscussionExecutionStrategy, execute_discussion_streaming
from .parallel import (
    ParallelExecutionStrategy,
    execute_parallel,
    execute_parallel_streaming,
)
from .sequential import (
    SequentialExecutionStrategy,
    execute_sequential,
    execute_sequential_streaming,
    execute_sequential_with_handoffs,
    format_handoff_input,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ..context import SupervisorContext

logger = setup_logger(__name__)

_DELEGATED_STRATEGY = DelegatedExecutionStrategy()
_PARALLEL_STRATEGY = ParallelExecutionStrategy()
_SEQUENTIAL_STRATEGY = SequentialExecutionStrategy()
_DISCUSSION_STRATEGY = DiscussionExecutionStrategy()


async def run_execution_phase(
    *,
    routing: RoutingDecision,
    task: str,
    context: SupervisorContext,
) -> ExecutionOutcome:
    """Execute task according to the routing decision and return structured outcome."""
    agents_map = context.agents
    if not agents_map:
        raise ExecutionPhaseError("Agents must be initialized before execution phase runs.")

    assigned_agents: list[str] = list(routing.assigned_to)
    subtasks: list[str] = list(routing.subtasks)
    tool_usage: list[dict[str, Any]] = []

    if routing.mode is ExecutionMode.PARALLEL:
        result, usage = await _PARALLEL_STRATEGY.execute(
            routing=routing, task=task, context=context
        )
        tool_usage.extend(usage)
    elif routing.mode is ExecutionMode.SEQUENTIAL:
        result, usage = await _SEQUENTIAL_STRATEGY.execute(
            routing=routing, task=task, context=context
        )
        tool_usage.extend(usage)
    else:
        # DISCUSSION does not currently have a non-streaming executor; fall back to delegated.
        delegate = assigned_agents[0] if assigned_agents else None
        if delegate is None:
            raise ExecutionPhaseError("Delegated execution requires at least one assigned agent.")
        result, usage = await execute_delegated(
            agents_map,
            delegate,
            task,
            thread=context.conversation_thread,
        )
        tool_usage.extend(usage)

    logger.info("Execution result: %s...", str(result)[:200])
    logger.info("Execution tool usage: %d items", len(tool_usage))

    return ExecutionOutcome(
        result=str(result),
        mode=routing.mode,
        assigned_agents=assigned_agents,
        subtasks=subtasks,
        status="success",
        artifacts={},
        tool_usage=tool_usage,
    )


async def run_execution_phase_streaming(
    *,
    routing: RoutingDecision,
    task: str,
    context: SupervisorContext,
) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
    """Execute task with streaming events."""
    agents_map = context.agents
    if not agents_map:
        raise ExecutionPhaseError("Agents must be initialized before execution phase runs.")

    # Get conversation thread from context for multi-turn support
    thread = context.conversation_thread

    if routing.mode is ExecutionMode.PARALLEL:
        async for event in execute_parallel_streaming(
            agents_map,
            list(routing.assigned_to),
            list(routing.subtasks),
            thread=thread,
        ):
            yield event
        return

    if routing.mode is ExecutionMode.SEQUENTIAL:
        async for event in execute_sequential_streaming(
            agents_map,
            list(routing.assigned_to),
            task,
            enable_handoffs=context.enable_handoffs,
            handoff=context.handoff,
            thread=thread,
        ):
            yield event
        return

    if routing.mode is ExecutionMode.DISCUSSION:
        async for event in execute_discussion_streaming(
            agents_map,
            list(routing.assigned_to),
            task,
            reasoner=context.dspy_supervisor,
            progress_callback=context.progress_callback,
            thread=thread,
        ):
            yield event
        return

    delegate = routing.assigned_to[0] if routing.assigned_to else None
    if delegate is None:
        raise ExecutionPhaseError("Delegated execution requires at least one assigned agent.")
    async for event in execute_delegated_streaming(agents_map, delegate, task, thread=thread):
        yield event


__all__ = [
    "DelegatedExecutionStrategy",
    "DiscussionExecutionStrategy",
    "ExecutionPhaseError",
    "ParallelExecutionStrategy",
    "SequentialExecutionStrategy",
    "_extract_tool_usage",
    "execute_delegated",
    "execute_delegated_streaming",
    "execute_discussion_streaming",
    "execute_parallel",
    "execute_parallel_streaming",
    "execute_sequential",
    "execute_sequential_streaming",
    "execute_sequential_with_handoffs",
    "format_handoff_input",
    "run_execution_phase",
    "run_execution_phase_streaming",
]
