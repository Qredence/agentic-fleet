"""Workflow package containing supervisor workflow implementations.

This package provides the core workflow orchestration functionality using
agent-framework WorkflowBuilder for multi-agent task execution.

Public API:
    - SupervisorWorkflow: Main workflow orchestrator
    - WorkflowConfig: Configuration dataclass for workflow execution
    - create_supervisor_workflow: Factory function to create and initialize fleet workflow
    - HandoffManager: Manager for handoff-based workflows
    - Exceptions: AgentExecutionError, RoutingError, HistoryError
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.workflows.config import WorkflowConfig
    from agentic_fleet.workflows.context import SupervisorContext
    from agentic_fleet.workflows.exceptions import AgentExecutionError, HistoryError, RoutingError
    from agentic_fleet.workflows.handoff import HandoffContext, HandoffManager
    from agentic_fleet.workflows.models import (
        AnalysisResult,
        ExecutionOutcome,
        ProgressReport,
        QualityReport,
        RoutingPlan,
    )
    from agentic_fleet.workflows.supervisor import (
        SupervisorWorkflow,
        create_supervisor_workflow,
    )

__all__ = [
    "AgentExecutionError",
    "AnalysisResult",
    "ExecutionOutcome",
    "HandoffContext",
    "HandoffManager",
    "HistoryError",
    "ProgressReport",
    "QualityReport",
    "RoutingError",
    "RoutingPlan",
    "SupervisorContext",
    "SupervisorWorkflow",
    "WorkflowConfig",
    "create_supervisor_workflow",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if (
        name == "SupervisorWorkflow"
        or name == "WorkflowConfig"
        or name == "create_supervisor_workflow"
    ):
        from agentic_fleet.workflows.config import WorkflowConfig
        from agentic_fleet.workflows.supervisor import (
            SupervisorWorkflow,
            create_supervisor_workflow,
        )

        if name == "SupervisorWorkflow":
            return SupervisorWorkflow
        if name == "WorkflowConfig":
            return WorkflowConfig
        return create_supervisor_workflow

    if name == "SupervisorContext":
        from agentic_fleet.workflows.context import SupervisorContext

        return SupervisorContext

    if name in (
        "AnalysisResult",
        "RoutingPlan",
        "ExecutionOutcome",
        "ProgressReport",
        "QualityReport",
    ):
        from agentic_fleet.workflows.models import (
            AnalysisResult,
            ExecutionOutcome,
            ProgressReport,
            QualityReport,
            RoutingPlan,
        )

        mapping = {
            "AnalysisResult": AnalysisResult,
            "RoutingPlan": RoutingPlan,
            "ExecutionOutcome": ExecutionOutcome,
            "ProgressReport": ProgressReport,
            "QualityReport": QualityReport,
        }
        return mapping[name]

    if name in ("HandoffManager", "HandoffContext"):
        from agentic_fleet.workflows.handoff import HandoffContext, HandoffManager

        if name == "HandoffManager":
            return HandoffManager
        return HandoffContext

    if name in ("AgentExecutionError", "RoutingError", "HistoryError"):
        from agentic_fleet.workflows.exceptions import (
            AgentExecutionError,
            HistoryError,
            RoutingError,
        )

        if name == "AgentExecutionError":
            return AgentExecutionError
        if name == "RoutingError":
            return RoutingError
        return HistoryError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
