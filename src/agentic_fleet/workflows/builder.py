"""Workflow builder for AgenticFleet.

Consolidated from fleet/builder.py and fleet/flexible_builder.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

try:
    from agent_framework._workflows import GroupChatBuilder, HandoffBuilder, WorkflowBuilder
except ImportError:
    # Fallback for environments where these are missing (e.g. older agent_framework)
    from agent_framework._workflows import WorkflowBuilder

    # Create minimal stub implementations that raise clear errors if used
    class GroupChatBuilder:
        """Stub for GroupChatBuilder when agent_framework is missing."""

        def __init__(self, *args, **kwargs):
            _ = args
            _ = kwargs
            raise RuntimeError(
                "GroupChatBuilder is not available in this agent-framework version. "
                "Please upgrade agent-framework or use 'standard' workflow mode."
            )

    class HandoffBuilder:
        """Stub for HandoffBuilder when agent_framework is missing."""

        def __init__(self, *args, **kwargs):
            _ = args
            _ = kwargs
            raise RuntimeError(
                "HandoffBuilder is not available in this agent-framework version. "
                "Please upgrade agent-framework or use 'standard' workflow mode."
            )


from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span
from .executors import (
    AnalysisExecutor,
    ExecutionExecutor,
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
    with optional_span("build_fleet_workflow", attributes={"mode": mode}):
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
    with optional_span("build_standard_workflow"):
        logger.info("Constructing Standard Fleet workflow...")

        analysis_executor = AnalysisExecutor("analysis", supervisor, context)
        routing_executor = RoutingExecutor("routing", supervisor, context)
        execution_executor = ExecutionExecutor("execution", context)
        progress_executor = ProgressExecutor("progress", supervisor, context)
        quality_executor = QualityExecutor("quality", supervisor, context)
        # NOTE: JudgeRefineExecutor removed in Plan #4 optimization
        # Workflow now terminates at QualityExecutor for faster execution

        return (
            WorkflowBuilder()
            .set_start_executor(analysis_executor)
            .add_edge(analysis_executor, routing_executor)
            .add_edge(routing_executor, execution_executor)
            .add_edge(execution_executor, progress_executor)
            .add_edge(progress_executor, quality_executor)
        )


def _build_group_chat_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
) -> GroupChatBuilder:
    """Build a Group Chat workflow."""
    with optional_span("build_group_chat_workflow"):
        logger.info("Constructing Group Chat workflow...")

        builder = GroupChatBuilder()

        if context.agents:
            participants_fn = getattr(builder, "participants", None)
            if callable(participants_fn):
                participants_fn(list(context.agents.values()))
            else:
                logger.warning("GroupChatBuilder missing participants() method; skipping")

        if context.openai_client:
            from agent_framework.openai import OpenAIResponsesClient

            model_id = "gpt-4o"
            if context.config:
                if hasattr(context.config, "model"):
                    model_id = str(context.config.model)
                elif hasattr(context.config, "dspy") and hasattr(context.config.dspy, "model"):
                    model_id = str(context.config.dspy.model)
            else:
                raise ValueError("Model configuration not found in context.")

            # Use OpenAIResponsesClient for consistency with agent-framework best practices
            chat_client = OpenAIResponsesClient(
                async_client=context.openai_client,
                model_id=model_id,
            )

            manager_fn = getattr(builder, "set_prompt_based_manager", None)
            if callable(manager_fn):
                manager_fn(
                    chat_client=chat_client,
                    instructions="You are the manager of this group chat. Coordinate the agents to complete the task.",
                    display_name="Manager",
                )
            else:
                logger.warning("GroupChatBuilder missing set_prompt_based_manager(); skipping")
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
    with optional_span("build_handoff_workflow"):
        logger.info("Constructing Handoff Fleet workflow...")

        if not context.agents:
            raise RuntimeError("No agents available for Handoff workflow.")

        # Create a Triage/Coordinator agent
        from agent_framework.openai import OpenAIResponsesClient

        model_id = "gpt-4o"
        if context.config and hasattr(context.config, "model"):
            model_id = str(context.config.model)

        # Ensure we have a client - use OpenAIResponsesClient for consistency
        if context.openai_client:
            chat_client = OpenAIResponsesClient(
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
        set_coordinator = getattr(builder, "set_coordinator", None)
        if callable(set_coordinator):
            set_coordinator(triage_agent)
        else:
            logger.warning("HandoffBuilder missing set_coordinator(); coordinator not set")

        # Configure Full Mesh Handoffs (Everyone can handoff to Everyone)
        # Triage -> All Agents
        add_handoff = getattr(builder, "add_handoff", None)
        if callable(add_handoff):
            add_handoff(triage_agent, list(context.agents.values()))
        else:
            logger.warning("HandoffBuilder missing add_handoff(); skipping graph wiring")

        # All Agents -> All Agents + Triage
        if callable(add_handoff):
            for agent in context.agents.values():
                targets = [t for t in list(context.agents.values()) if t != agent] + [triage_agent]
                add_handoff(agent, targets)

        # Termination condition: Look for "FINAL RESULT:" in the message
        # or if the message comes from Triage and seems like a conclusion.
        def termination_condition(conversation):
            if not conversation:
                return False
            last_msg = conversation[-1]
            # Terminate if Triage agent says "FINAL RESULT:"
            return last_msg.author_name == "Triage" and "FINAL RESULT:" in last_msg.text

        with_termination_condition = getattr(builder, "with_termination_condition", None)
        if callable(with_termination_condition):
            with_termination_condition(termination_condition)
        else:
            logger.warning(
                "HandoffBuilder missing with_termination_condition(); termination guard disabled"
            )

        return builder
