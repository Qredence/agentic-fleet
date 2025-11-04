"""Backward compatibility alias - use workflow.magentic_workflow instead."""

from __future__ import annotations

from agentic_fleet.workflow.magentic_workflow import (
    MagenticFleetWorkflow,
    MagenticFleetWorkflowBuilder,
)

__all__ = [
    "MagenticFleetWorkflow",
    "MagenticFleetWorkflowBuilder",
]
