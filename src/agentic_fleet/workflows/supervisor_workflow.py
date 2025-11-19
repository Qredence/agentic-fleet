"""Fleet-native workflow entrypoints.

This module exposes the public ``SupervisorWorkflow`` class used by the CLI and
tests, while delegating the main implementation to the fleet adapter.
"""

from __future__ import annotations

from .config import WorkflowConfig
from .fleet.adapter import SupervisorWorkflow as _FleetSupervisorWorkflow
from .fleet.adapter import create_fleet_workflow
from .initialization import initialize_workflow_context

# Public entrypoint used throughout the codebase/tests
SupervisorWorkflow = _FleetSupervisorWorkflow


def _validate_task(task: str, max_length: int = 10_000) -> str:
    """Validate a user-provided task string.

    This function enforces basic guardrails used by the comprehensive workflow
    tests while remaining intentionally lightweight so validation never becomes
    the critical path for execution.

    Validation rules:
    * Task must not be empty or only whitespace
    * Task must not exceed ``max_length`` characters
    * Leading/trailing whitespace is stripped on success

    Args:
        task: Raw task string supplied by the caller.
        max_length: Maximum permitted length (defaults to 10k chars).

    Returns:
        The normalized (stripped) task string.

    Raises:
        ValueError: If the task is empty/whitespace or exceeds ``max_length``.
    """
    normalized = task.strip()
    if not normalized:
        raise ValueError("Task cannot be empty")
    if len(normalized) > max_length:
        raise ValueError(
            f"Task exceeds maximum length of {max_length} characters (received {len(normalized)})"
        )
    return normalized


async def create_supervisor_workflow(
    *,
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
) -> _FleetSupervisorWorkflow:
    """Create and initialize the fleet workflow.

    This is the preferred entrypoint for the application.  It wires the
    ``SupervisorContext`` via :func:`initialize_workflow_context` and then
    delegates to :func:`create_fleet_workflow` to build the
    agent-framework-based workflow.
    """

    context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)
    return await create_fleet_workflow(context=context, compile_dspy=compile_dspy)
