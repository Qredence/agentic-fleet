"""Workflow factory for creating supervisor workflows.

This module provides the create_supervisor_workflow factory function
that creates and initializes the agent-framework WorkflowBuilder-based fleet workflow.

Note: This file exists for historical import compatibility. The actual implementation
is in workflows/fleet/adapter.py (FleetWorkflowAdapter). This module simply re-exports
the fleet-based workflow as SupervisorWorkflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fleet.adapter import SupervisorWorkflow as FleetWorkflowAdapter

# Type alias for public API compatibility
from .fleet.adapter import SupervisorWorkflow, create_fleet_workflow
from .initialization import initialize_workflow_context

# Alias for backward compatibility
FleetWorkflowAdapter = SupervisorWorkflow


async def create_supervisor_workflow(compile_dspy: bool = True) -> SupervisorWorkflow:
    """Factory function to create and initialize supervisor workflow.

    Uses the agent-framework WorkflowBuilder-based fleet workflow.

    Args:
        compile_dspy: Whether to compile DSPy supervisor

    Returns:
        SupervisorWorkflow instance (FleetWorkflowAdapter)
    """

    # Initialize workflow context
    context = await initialize_workflow_context(compile_dspy=compile_dspy)

    # Create workflow entrypoint
    workflow = await create_fleet_workflow(context, compile_dspy=compile_dspy)
    return workflow
