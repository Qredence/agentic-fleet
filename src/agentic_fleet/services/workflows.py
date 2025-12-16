"""Workflow services facade.

Re-exports workflow orchestration, executors, strategies, and models.
This provides a single import point for workflow-related functionality.

Usage:
    from agentic_fleet.services.workflows import SupervisorWorkflow, create_supervisor_workflow
    from agentic_fleet.services.workflows import WorkflowConfig, AnalysisResult, RoutingPlan
    from agentic_fleet.services.workflows import HandoffManager
"""

from __future__ import annotations

# =============================================================================
# Helpers
# =============================================================================
from agentic_fleet.dspy_modules.reasoner_utils import is_time_sensitive_task

# =============================================================================
# Builder
# =============================================================================
from agentic_fleet.workflows.builder import WorkflowBuilder

# =============================================================================
# Configuration
# =============================================================================
from agentic_fleet.workflows.config import WorkflowConfig

# =============================================================================
# Context
# =============================================================================
from agentic_fleet.workflows.context import SupervisorContext

# =============================================================================
# Exceptions
# =============================================================================
from agentic_fleet.workflows.exceptions import AgentExecutionError, HistoryError, RoutingError

# =============================================================================
# Executors
# =============================================================================
from agentic_fleet.workflows.executors import (
    AnalysisExecutor,
    DSPyExecutor,
    ExecutionExecutor,
    ProgressExecutor,
    QualityExecutor,
    RoutingExecutor,
)

# =============================================================================
# Handoff
# =============================================================================
from agentic_fleet.workflows.handoff import HandoffContext, HandoffManager
from agentic_fleet.workflows.helpers import (
    FastPathDetector,
    is_simple_task,
    normalize_routing_decision,
    synthesize_results,
)

# =============================================================================
# Models
# =============================================================================
from agentic_fleet.workflows.models import (
    AnalysisResult,
    ExecutionOutcome,
    ProgressReport,
    QualityReport,
    RoutingPlan,
)

# =============================================================================
# Strategies (execution functions)
# =============================================================================
from agentic_fleet.workflows.strategies import (
    ExecutionPhaseError,
    execute_delegated,
    execute_delegated_streaming,
    execute_parallel,
    execute_parallel_streaming,
    execute_sequential,
    execute_sequential_streaming,
    execute_sequential_with_handoffs,
    run_execution_phase,
    run_execution_phase_streaming,
)

# =============================================================================
# Group Chat
# =============================================================================
from agentic_fleet.workflows.strategies.group_chat_adapter import (
    DSPyGroupChatManager,
    GroupChatBuilder,
)

# =============================================================================
# Supervisor Workflow
# =============================================================================
from agentic_fleet.workflows.supervisor import (
    SupervisorWorkflow,
    create_supervisor_workflow,
)

__all__ = [
    "AgentExecutionError",
    "AnalysisExecutor",
    "AnalysisResult",
    "DSPyExecutor",
    "DSPyGroupChatManager",
    "ExecutionExecutor",
    "ExecutionOutcome",
    "ExecutionPhaseError",
    "FastPathDetector",
    "GroupChatBuilder",
    "HandoffContext",
    "HandoffManager",
    "HistoryError",
    "ProgressExecutor",
    "ProgressReport",
    "QualityExecutor",
    "QualityReport",
    "RoutingError",
    "RoutingExecutor",
    "RoutingPlan",
    "SupervisorContext",
    "SupervisorWorkflow",
    "WorkflowBuilder",
    "WorkflowConfig",
    "create_supervisor_workflow",
    "execute_delegated",
    "execute_delegated_streaming",
    "execute_parallel",
    "execute_parallel_streaming",
    "execute_sequential",
    "execute_sequential_streaming",
    "execute_sequential_with_handoffs",
    "is_simple_task",
    "is_time_sensitive_task",
    "normalize_routing_decision",
    "run_execution_phase",
    "run_execution_phase_streaming",
    "synthesize_results",
]
