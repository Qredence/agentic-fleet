"""Agent-framework workflow implementation for AgenticFleet.

This module provides a WorkflowBuilder-based implementation using agent-framework's
native workflow capabilities with DSPy-enhanced executors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter import SupervisorWorkflow, create_fleet_workflow

__all__ = [
    "SupervisorWorkflow",
    "create_fleet_workflow",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if name == "create_fleet_workflow":
        from .adapter import create_fleet_workflow

        return create_fleet_workflow

    if name == "SupervisorWorkflow":
        from .adapter import SupervisorWorkflow

        return SupervisorWorkflow

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
