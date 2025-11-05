"""Core package public API and compatibility shims.

This module exposes a few convenience imports while avoiding eager imports
that can cause circular dependencies during package initialization.
"""

from __future__ import annotations

from typing import Any

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


def __getattr__(name: str) -> Any:  # pragma: no cover - import-time behavior
    if name == "AgentFactory":
        from agentic_fleet.agents.coordinator import AgentFactory as _AgentFactory

        return _AgentFactory
    if name == "WorkflowFactory":
        from agentic_fleet.api.workflow_factory import WorkflowFactory as _WorkflowFactory

        return _WorkflowFactory
    if name in {"RunsWorkflow", "WorkflowEvent"}:
        from agentic_fleet.models.events import RunsWorkflow as _RunsWorkflow
        from agentic_fleet.models.events import WorkflowEvent as _WorkflowEvent

        return {"RunsWorkflow": _RunsWorkflow, "WorkflowEvent": _WorkflowEvent}[name]
    if name == "WorkflowConfig":
        from agentic_fleet.models.workflow import WorkflowConfig as _WorkflowConfig

        return _WorkflowConfig
    if name == "ToolRegistry":
        from agentic_fleet.tools.registry import ToolRegistry as _ToolRegistry

        return _ToolRegistry
    if name == "WorkflowEventBridge":
        from agentic_fleet.workflow.events import WorkflowEventBridge as _Bridge

        return _Bridge
    if name in {"MagenticFleetWorkflow", "MagenticFleetWorkflowBuilder"}:
        from agentic_fleet.workflow import magentic_workflow as _magentic_workflow

        return {
            "MagenticFleetWorkflow": _magentic_workflow.MagenticFleetWorkflow,
            "MagenticFleetWorkflowBuilder": _magentic_workflow.MagenticFleetWorkflowBuilder,
        }[name]
    raise AttributeError(name)
