"""Workflow factory for creating supervisor workflows.

This module provides the create_supervisor_workflow factory function
that creates and initializes the agent-framework WorkflowBuilder-based fleet workflow.

Note: This file exists for historical import compatibility. The actual implementation
is in workflows/fleet/adapter.py (FleetWorkflowAdapter). This module simply re-exports
the fleet-based workflow as SupervisorWorkflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import WorkflowConfig
from .fleet.adapter import SupervisorWorkflow as FleetWorkflowAdapter
from .fleet.adapter import create_fleet_workflow
from .initialization import initialize_workflow_context

if TYPE_CHECKING:
    # Re-exported type alias for backward compatibility.
    from .fleet.adapter import SupervisorWorkflow as _SupervisorWorkflowType


def _validate_task(task: str, *, max_length: int = 10000) -> str:
    """Validate a task string.

    This helper exists for backward compatibility with earlier versions of
    AgenticFleet and is exercised directly in the test suite and docs.

    Args:
        task: Task description provided by the caller.
        max_length: Maximum allowed task length in characters.

    Returns:
        The trimmed task string.

    Raises:
        ValueError: If the task is empty/whitespace-only or exceeds max_length.
    """

    if not task or not task.strip():
        raise ValueError("Task cannot be empty")
    if len(task) > max_length:
        raise ValueError(f"Task exceeds maximum length of {max_length} characters")
    return task.strip()


async def create_supervisor_workflow(
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
) -> _SupervisorWorkflowType:
    """Factory function to create and initialize supervisor workflow.

    Uses the agent-framework WorkflowBuilder-based fleet workflow.

    Args:
        compile_dspy: Whether to compile DSPy supervisor
        config: Optional workflow configuration. When provided, this
            configuration is passed through to the workflow initializer.

    Returns:
        SupervisorWorkflow instance (FleetWorkflowAdapter)
    """

    # Initialize workflow context
    context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)

    # Create workflow entrypoint
    workflow = await create_fleet_workflow(context, compile_dspy=compile_dspy)
    return workflow


# Alias for backward compatibility in external imports
SupervisorWorkflow = FleetWorkflowAdapter
FleetWorkflowAdapter = FleetWorkflowAdapter
