"""AgenticFleet: DSPy-Enhanced Multi-Agent Orchestration.

AgenticFleet is a hybrid DSPy + Microsoft agent-framework runtime that delivers
a self-optimizing fleet of specialized AI agents. DSPy handles task analysis,
routing, progress & quality assessment; agent-framework provides robust
orchestration primitives, event streaming, and tool execution.

Public API:
    - SupervisorWorkflow: Main workflow orchestrator
    - WorkflowConfig: Configuration for workflow execution
    - AgentFactory: Factory for creating ChatAgent instances
    - ToolRegistry: Central registry for managing tool metadata
    - ExecutionMode: Enumeration of supported execution modes
    - RoutingDecision: Typed representation of routing decisions
    - Evaluator: Batch evaluation engine
    - Tool classes: BrowserTool, TavilyMCPTool, TavilySearchTool

Example:
    ```python
    from agentic_fleet import create_supervisor_workflow

    workflow = await create_supervisor_workflow()
    result = await workflow.run("Your task here")
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.agents import AgentFactory
    from agentic_fleet.evaluation import Evaluator, compute_metrics
    from agentic_fleet.tools import BrowserTool, TavilyMCPTool, TavilySearchTool
    from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
    from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry
    from agentic_fleet.workflows import (
        SupervisorWorkflow,
        WorkflowConfig,
        create_supervisor_workflow,
    )

__version__ = "0.6.0"

__all__ = [
    "AgentFactory",
    "BrowserTool",
    "Evaluator",
    "ExecutionMode",
    "RoutingDecision",
    "SupervisorWorkflow",
    "TavilyMCPTool",
    "TavilySearchTool",
    "ToolMetadata",
    "ToolRegistry",
    "WorkflowConfig",
    "compute_metrics",
    "create_supervisor_workflow",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API to avoid circular imports."""
    if (
        name == "SupervisorWorkflow"
        or name == "WorkflowConfig"
        or name == "create_supervisor_workflow"
    ):
        from agentic_fleet.workflows import SupervisorWorkflow, create_supervisor_workflow
        from agentic_fleet.workflows.config import WorkflowConfig

        if name == "SupervisorWorkflow":
            return SupervisorWorkflow
        if name == "WorkflowConfig":
            return WorkflowConfig
        return create_supervisor_workflow

    if name == "AgentFactory":
        from agentic_fleet.agents import AgentFactory

        return AgentFactory

    if name in ("ToolRegistry", "ToolMetadata"):
        from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry

        if name == "ToolRegistry":
            return ToolRegistry
        return ToolMetadata

    if name in ("ExecutionMode", "RoutingDecision"):
        from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

        if name == "ExecutionMode":
            return ExecutionMode
        return RoutingDecision

    if name in ("BrowserTool", "TavilyMCPTool", "TavilySearchTool"):
        from agentic_fleet.tools import BrowserTool, TavilyMCPTool, TavilySearchTool

        if name == "BrowserTool":
            return BrowserTool
        if name == "TavilyMCPTool":
            return TavilyMCPTool
        return TavilySearchTool

    if name in ("Evaluator", "compute_metrics"):
        from agentic_fleet.evaluation import Evaluator, compute_metrics

        if name == "Evaluator":
            return Evaluator
        return compute_metrics

    if name == "console":
        # Expose the CLI console module as an attribute for
        # backward-compatible imports (tests and docs use
        # `from agentic_fleet import console`).
        import importlib

        return importlib.import_module("agentic_fleet.cli.console")

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
