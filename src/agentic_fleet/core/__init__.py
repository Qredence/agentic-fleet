"""Backward compatibility aliases for old import paths.

These modules provide compatibility shims for code that imports
from the old locations. They will be removed in a future release.
"""

from __future__ import annotations

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.api.workflow_factory import WorkflowFactory
from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent
from agentic_fleet.models.workflow import WorkflowConfig
from agentic_fleet.tools.registry import ToolRegistry
from agentic_fleet.workflow.events import WorkflowEventBridge
from agentic_fleet.workflow.magentic_workflow import (
    MagenticFleetWorkflow,
    MagenticFleetWorkflowBuilder,
)

__all__ = [
    "AgentFactory",
    "MagenticFleetWorkflow",
    "MagenticFleetWorkflowBuilder",
    "RunsWorkflow",
    "ToolRegistry",
    "WorkflowConfig",
    "WorkflowEvent",
    "WorkflowEventBridge",
    "WorkflowFactory",
]
