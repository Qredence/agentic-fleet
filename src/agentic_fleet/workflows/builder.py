"""Workflow builder for AgenticFleet.

Consolidated from fleet/builder.py and fleet/flexible_builder.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from agent_framework import GroupChatBuilder, WorkflowBuilder

from ..utils.logger import setup_logger
from .executors import (
    AnalysisExecutor,
    ExecutionExecutor,
    JudgeRefineExecutor,
    ProgressExecutor,
    QualityExecutor,
    RoutingExecutor,
)

if TYPE_CHECKING:
    from ..dspy_modules.reasoner import DSPyReasoner
    from .context import SupervisorContext

logger = setup_logger(__name__)

WorkflowMode = Literal["group_chat", "concurrent", "handoff", "standard"]


def build_fleet_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
    mode: WorkflowMode = "standard",
) -> WorkflowBuilder | GroupChatBuilder:
    """Build the fleet workflow based on the specified mode."""
    logger.info(f"Building fleet workflow in '{mode}' mode...")

    if mode == "group_chat":
        return _build_group_chat_workflow(supervisor, context)
    elif mode == "concurrent":
        # Placeholder for future concurrent-specific wiring
        return _build_standard_workflow(supervisor, context)
    elif mode == "handoff":
        # Handoffs are integrated into standard/sequential execution strategies
        return _build_standard_workflow(supervisor, context)
    else:
        return _build_standard_workflow(supervisor, context)


def _build_standard_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
) -> WorkflowBuilder:
    """Build the standard fleet workflow graph."""
    logger.info("Constructing Standard Fleet workflow...")

    analysis_executor = AnalysisExecutor("analysis", supervisor, context)
    routing_executor = RoutingExecutor("routing", supervisor, context)
    execution_executor = ExecutionExecutor("execution", context)
    progress_executor = ProgressExecutor("progress", supervisor, context)
    quality_executor = QualityExecutor("quality", supervisor, context)
    judge_refine_executor = JudgeRefineExecutor("judge_refine", context)

    return (
        WorkflowBuilder()
        .set_start_executor(analysis_executor)
        .add_edge(analysis_executor, routing_executor)
        .add_edge(routing_executor, execution_executor)
        .add_edge(execution_executor, progress_executor)
        .add_edge(progress_executor, quality_executor)
        .add_edge(quality_executor, judge_refine_executor)
    )


def _build_group_chat_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
) -> GroupChatBuilder:
    """Build a Group Chat workflow."""
    logger.info("Constructing Group Chat workflow...")

    builder = GroupChatBuilder()

    if context.agents:
        builder.participants(list(context.agents.values()))

    if context.openai_client:
        from agent_framework.openai import OpenAIChatClient

        model_id = "gpt-4o"
        if context.config:
            if hasattr(context.config, "model"):
                model_id = str(context.config.model)
            elif hasattr(context.config, "dspy") and hasattr(context.config.dspy, "model"):
                model_id = str(context.config.dspy.model)

        chat_client = OpenAIChatClient(
            async_client=context.openai_client,
            model_id=model_id,
        )

        builder.set_prompt_based_manager(
            chat_client=chat_client,
            instructions="You are the manager of this group chat. Coordinate the agents to complete the task.",
            display_name="Manager",
        )
    else:
        logger.warning(
            "No OpenAI client available. Group Chat manager might not function correctly."
        )

    return builder
