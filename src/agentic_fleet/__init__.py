"""AgenticFleet: DSPy-Enhanced Multi-Agent Orchestration.

AgenticFleet is a hybrid DSPy + Microsoft agent-framework runtime that delivers
a self-optimizing fleet of specialized AI agents. DSPy handles task analysis,
routing, progress & quality assessment; agent-framework provides robust
orchestration primitives, event streaming, and tool execution.

**Clean Public API (v0.7+):**

    Core infrastructure:
        - ``get_settings``, ``AppSettings`` - Configuration management
        - ``setup_logger``, ``initialize_tracing`` - Structured logging & tracing
        - ``ConversationStore``, ``HistoryManager`` - Storage backends

    Services:
        - ``AgentFactory``, ``DSPyEnhancedAgent`` - Agent creation
        - ``DSPyReasoner``, ``TaskAnalysis`` - DSPy reasoning
        - ``SupervisorWorkflow``, ``create_supervisor_workflow`` - Orchestration
        - ``ConversationManager`` - Conversation persistence

    API routers (for app composition):
        - ``api.health``, ``api.chat``, ``api.nlu``, ``api.streaming``
        - ``api.sessions``, ``api.conversations``, ``api.models``

    Legacy API (preserved for backward compatibility):
        - ``ToolRegistry``, ``ExecutionMode``, ``RoutingDecision``
        - ``Evaluator``, ``compute_metrics``
        - Tool classes: ``BrowserTool``, ``TavilyMCPTool``, ``TavilySearchTool``

Example:
    ```python
    from agentic_fleet import create_supervisor_workflow

    workflow = await create_supervisor_workflow()
    result = await workflow.run("Your task here")
    ```

    Or using the new clean imports:

    ```python
    from agentic_fleet.core import get_settings, setup_logger
    from agentic_fleet.services import AgentFactory, DSPyReasoner
    ```
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version
from typing import TYPE_CHECKING

from agentic_fleet.utils.agent_framework_shims import (
    ensure_agent_framework_shims as _ensure_agent_framework_shims,
)

_ensure_agent_framework_shims()

if TYPE_CHECKING:
    # Core infrastructure
    from agentic_fleet.core import (
        AppSettings,
        ConversationStore,
        HistoryManager,
        TTLCache,
        get_settings,
        initialize_tracing,
        setup_logger,
    )

    # Legacy imports (preserved for backward compat)
    from agentic_fleet.evaluation import Evaluator, compute_metrics

    # Services
    from agentic_fleet.services import (
        AgentFactory,
        ConversationManager,
        DSPyReasoner,
        SupervisorWorkflow,
        create_supervisor_workflow,
    )
    from agentic_fleet.tools import BrowserTool, TavilyMCPTool, TavilySearchTool
    from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
    from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry
    from agentic_fleet.workflows import WorkflowConfig

try:
    __version__ = _get_version("agentic-fleet")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"  # Fallback for editable installs without metadata

__all__ = [
    # Services (new clean API)
    "AgentFactory",
    # Core infrastructure (new clean API)
    "AppSettings",
    # Legacy exports (backward compat)
    "BrowserTool",
    "ConversationManager",
    "ConversationStore",
    "DSPyReasoner",
    "Evaluator",
    "ExecutionMode",
    "HistoryManager",
    "RoutingDecision",
    "SupervisorWorkflow",
    "TTLCache",
    "TavilyMCPTool",
    "TavilySearchTool",
    "ToolMetadata",
    "ToolRegistry",
    "WorkflowConfig",
    "compute_metrics",
    "create_supervisor_workflow",
    "get_settings",
    "initialize_tracing",
    "setup_logger",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API to avoid circular imports."""
    # Core infrastructure (new clean API)
    if name in ("AppSettings", "get_settings"):
        from agentic_fleet.core import AppSettings, get_settings

        return AppSettings if name == "AppSettings" else get_settings

    if name in ("setup_logger", "initialize_tracing"):
        from agentic_fleet.core import initialize_tracing, setup_logger

        return setup_logger if name == "setup_logger" else initialize_tracing

    if name in ("ConversationStore", "HistoryManager", "TTLCache"):
        from agentic_fleet.core import ConversationStore, HistoryManager, TTLCache

        return {
            "ConversationStore": ConversationStore,
            "HistoryManager": HistoryManager,
            "TTLCache": TTLCache,
        }[name]

    # Services (new clean API)
    if name == "DSPyReasoner":
        from agentic_fleet.services import DSPyReasoner

        return DSPyReasoner

    if name == "ConversationManager":
        from agentic_fleet.services import ConversationManager

        return ConversationManager

    # Workflows (both old and new paths)
    if name in ("SupervisorWorkflow", "WorkflowConfig", "create_supervisor_workflow"):
        from agentic_fleet.workflows import SupervisorWorkflow, create_supervisor_workflow
        from agentic_fleet.workflows.config import WorkflowConfig

        if name == "SupervisorWorkflow":
            return SupervisorWorkflow
        if name == "WorkflowConfig":
            return WorkflowConfig
        return create_supervisor_workflow

    # Agents (both old and new paths)
    if name == "AgentFactory":
        from agentic_fleet.agents import AgentFactory

        return AgentFactory

    # Legacy: Tool registry
    if name in ("ToolRegistry", "ToolMetadata"):
        from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry

        if name == "ToolRegistry":
            return ToolRegistry
        return ToolMetadata

    # Legacy: Models
    if name in ("ExecutionMode", "RoutingDecision"):
        from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

        if name == "ExecutionMode":
            return ExecutionMode
        return RoutingDecision

    # Legacy: Tools
    if name in ("BrowserTool", "TavilyMCPTool", "TavilySearchTool"):
        from agentic_fleet.tools import BrowserTool, TavilyMCPTool, TavilySearchTool

        if name == "BrowserTool":
            return BrowserTool
        if name == "TavilyMCPTool":
            return TavilyMCPTool
        return TavilySearchTool

    # Legacy: Evaluation
    if name in ("Evaluator", "compute_metrics"):
        from agentic_fleet.evaluation import Evaluator, compute_metrics

        if name == "Evaluator":
            return Evaluator
        return compute_metrics

    # Legacy: CLI console
    if name == "console":
        # Expose the CLI console module as an attribute for
        # backward-compatible imports (tests and docs use
        # `from agentic_fleet import console`).
        import importlib

        return importlib.import_module("agentic_fleet.cli.console")

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
