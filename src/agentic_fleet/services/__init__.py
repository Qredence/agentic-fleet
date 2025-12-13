"""AgenticFleet Services package.

This package provides the business logic layer with four facade modules:

- dspy_programs: DSPy signatures, modules, reasoner, and assertions
- agents: Agent definitions, factory, and prompt helpers
- workflows: Workflow orchestration, executors, and strategies
- conversation: Conversation and session management

Usage:
    from agentic_fleet.services.dspy_programs import DSPyReasoner, TaskAnalysis
    from agentic_fleet.services.agents import AgentFactory, get_planner_instructions
    from agentic_fleet.services.workflows import SupervisorWorkflow, create_supervisor_workflow
    from agentic_fleet.services.conversation import ConversationManager
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.services.agents import AgentFactory, DSPyEnhancedAgent
    from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
    from agentic_fleet.services.dspy_programs import DSPyReasoner, TaskAnalysis
    from agentic_fleet.services.workflows import SupervisorWorkflow, WorkflowConfig

__all__ = [
    "AgentFactory",
    "ConversationManager",
    "DSPyEnhancedAgent",
    "DSPyReasoner",
    "SupervisorWorkflow",
    "TaskAnalysis",
    "WorkflowConfig",
    "WorkflowSessionManager",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if name in ("AgentFactory", "DSPyEnhancedAgent"):
        from agentic_fleet.services import agents

        return getattr(agents, name)

    if name in ("DSPyReasoner", "TaskAnalysis"):
        from agentic_fleet.services import dspy_programs

        return getattr(dspy_programs, name)

    if name in ("SupervisorWorkflow", "WorkflowConfig"):
        from agentic_fleet.services import workflows

        return getattr(workflows, name)

    if name in ("ConversationManager", "WorkflowSessionManager"):
        from agentic_fleet.services import conversation

        return getattr(conversation, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
