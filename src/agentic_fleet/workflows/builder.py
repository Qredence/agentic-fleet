"""Workflow builder for AgenticFleet.

Consolidated from fleet/builder.py and fleet/flexible_builder.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from agent_framework import GroupChatBuilder, HandoffBuilder, WorkflowBuilder

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
        return _build_handoff_workflow(supervisor, context)
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
        else:
            raise ValueError("Model configuration not found in context.")

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


def _build_handoff_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
):
    """Build a Handoff-based workflow."""
    logger.info("Constructing Handoff Fleet workflow...")

    if not context.agents:
        raise RuntimeError("No agents available for Handoff workflow.")

    # Create a Triage/Coordinator agent
    from agent_framework.openai import OpenAIChatClient

    model_id = "gpt-4o"
    if context.config and hasattr(context.config, "model"):
        model_id = str(context.config.model)

    # Ensure we have a client
    if context.openai_client:
        chat_client = OpenAIChatClient(
            async_client=context.openai_client,
            model_id=model_id,
        )
    else:
        # Fallback (should not happen if initialized correctly)
        raise RuntimeError("OpenAI client required for Triage agent creation")

    # Create Triage Agent
    triage_agent = chat_client.create_agent(
        name="Triage",
        instructions=(
            "You are the Fleet Coordinator. Your goal is to route the user's task to the appropriate specialist(s) "
            "and ensure the task is completed satisfactorily. "
            "Available Specialists:\n"
            + "\n".join(
                [f"- {name}: {agent.description}" for name, agent in context.agents.items()]
            )
            + "\n\nRules:\n"
            "1. Analyze the user task.\n"
            "2. Hand off to the most relevant specialist (e.g., Researcher for questions, Writer for drafting).\n"
            "3. Specialists can hand off to each other. You can also hand off to them.\n"
            "4. When the task is complete and you have the final answer, reply to the user starting with 'FINAL RESULT:'."
        ),
    )

    # Build Handoff Workflow
    participants = [triage_agent, *list(context.agents.values())]

    builder = HandoffBuilder(name="fleet_handoff", participants=participants)
    builder.set_coordinator(triage_agent)

    # Configure Full Mesh Handoffs (Everyone can handoff to Everyone)
    # Triage -> All Agents
    builder.add_handoff(triage_agent, list(context.agents.values()))

    # All Agents -> All Agents + Triage
    for agent in context.agents.values():
        targets = [t for t in list(context.agents.values()) if t != agent] + [triage_agent]
        builder.add_handoff(agent, targets)

    # Termination condition: Look for "FINAL RESULT:" in the message
    # or if the message comes from Triage and seems like a conclusion.
    def termination_condition(conversation):
        if not conversation:
            return False
        last_msg = conversation[-1]
        # Terminate if Triage agent says "FINAL RESULT:"
        return last_msg.author_name == "Triage" and "FINAL RESULT:" in last_msg.text

    builder.with_termination_condition(termination_condition)

    return builder
