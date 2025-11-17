from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from ...utils.models import ExecutionMode, RoutingDecision
from ..execution import (
    execute_delegated,
    execute_parallel,
    execute_sequential,
    execute_sequential_with_handoffs,
)
from ..handoff_manager import HandoffManager
from ..orchestration import SupervisorContext
from .models import ExecutionOutcome

logger = logging.getLogger(__name__)


class ExecutionPhaseError(RuntimeError):
    """Raised when execution phase prerequisites are not satisfied."""


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

    if routing.mode is ExecutionMode.PARALLEL:
        result = await execute_parallel(agents_map, assigned_agents, subtasks)
    elif routing.mode is ExecutionMode.SEQUENTIAL:
        result = await _execute_sequential(
            agents_map=agents_map,
            agents=assigned_agents,
            task=task,
            enable_handoffs=context.enable_handoffs,
            handoff_manager=context.handoff_manager,
        )
    else:
        delegate = assigned_agents[0] if assigned_agents else None
        if delegate is None:
            raise ExecutionPhaseError("Delegated execution requires at least one assigned agent.")
        result = await execute_delegated(agents_map, delegate, task)

    return ExecutionOutcome(
        result=str(result),
        mode=routing.mode,
        assigned_agents=assigned_agents,
        subtasks=subtasks,
        status="success",
        artifacts={},
    )


async def _execute_sequential(
    *,
    agents_map: dict[str, Any],
    agents: Sequence[str],
    task: str,
    enable_handoffs: bool,
    handoff_manager: HandoffManager | None,
) -> str:
    if not agents:
        raise ExecutionPhaseError("Sequential execution requires at least one agent.")

    if enable_handoffs and handoff_manager:
        return await execute_sequential_with_handoffs(
            agents_map,
            list(agents),
            task,
            handoff_manager,
        )

    # Pass simple_mode through to suppress heavy tool usage on trivial tasks
    simple_mode = False
    try:
        # `task` here is the text; we cannot directly access metadata. Default false.
        # Simple-mode is primarily signaled via executor metadata; this is a best-effort guard.
        simple_mode = False
    except Exception:
        simple_mode = False
    return await execute_sequential(
        agents_map,
        list(agents),
        task,
        enable_handoffs=False,
        handoff_manager=None,
        simple_mode=simple_mode,
    )
