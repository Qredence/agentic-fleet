"""WorkflowBuilder for fleet workflow.

Constructs the agent-framework workflow using WorkflowBuilder API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import WorkflowBuilder

from ...utils.logger import setup_logger
from .analysis_executor import AnalysisExecutor
from .execution_executor import ExecutionExecutor
from .judge_refine_executor import JudgeRefineExecutor
from .progress_executor import ProgressExecutor
from .quality_executor import QualityExecutor
from .routing_executor import RoutingExecutor

if TYPE_CHECKING:
    from ...dspy_modules.supervisor import DSPySupervisor
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


def build_fleet_workflow(
    supervisor: DSPySupervisor,
    context: SupervisorContext,
) -> WorkflowBuilder:
    """Build the fleet workflow using WorkflowBuilder.

    Args:
        supervisor: DSPy supervisor instance
        context: Supervisor context with configuration and state

    Returns:
        Configured WorkflowBuilder instance
    """
    logger.info("Building fleet workflow with agent-framework WorkflowBuilder...")

    # Create executors
    analysis_executor = AnalysisExecutor(
        executor_id="analysis",
        supervisor=supervisor,
        context=context,
    )

    routing_executor = RoutingExecutor(
        executor_id="routing",
        supervisor=supervisor,
        context=context,
    )

    execution_executor = ExecutionExecutor(
        executor_id="execution",
        context=context,
    )

    progress_executor = ProgressExecutor(
        executor_id="progress",
        supervisor=supervisor,
        context=context,
    )

    quality_executor = QualityExecutor(
        executor_id="quality",
        supervisor=supervisor,
        context=context,
    )

    judge_refine_executor = JudgeRefineExecutor(
        executor_id="judge_refine",
        context=context,
    )

    # Build workflow graph
    workflow_builder = (
        WorkflowBuilder()
        .set_start_executor(analysis_executor)
        .add_edge(analysis_executor, routing_executor)
        .add_edge(routing_executor, execution_executor)
        .add_edge(execution_executor, progress_executor)
        .add_edge(progress_executor, quality_executor)
        .add_edge(quality_executor, judge_refine_executor)
    )

    logger.info("Fleet workflow built successfully")
    return workflow_builder
