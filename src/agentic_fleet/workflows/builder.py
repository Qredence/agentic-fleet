"""Workflow builder for AgenticFleet.

Consolidated from fleet/builder.py and fleet/flexible_builder.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

try:
    from agent_framework._workflows import (
        GroupChatBuilder as _GroupChatBuilder,
    )
    from agent_framework._workflows import (
        HandoffBuilder as _HandoffBuilder,
    )
    from agent_framework._workflows import (
        WorkflowBuilder,
    )

    GroupChatBuilder: type[Any] = _GroupChatBuilder
    HandoffBuilder: type[Any] = _HandoffBuilder
except ImportError:
    # Fallback for environments where these are missing (e.g. older agent_framework)
    from agent_framework._workflows import WorkflowBuilder

    # Create minimal stub implementations that raise clear errors if used
    class _GroupChatBuilderStub:
        """Stub for GroupChatBuilder when agent_framework is missing."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """
            Constructor stub that always raises a RuntimeError indicating the GroupChatBuilder feature is unavailable.

            This initializer does not construct an instance; it exists as a fallback when the required
            agent-framework implementation is not present.

            Raises:
                RuntimeError: Indicates GroupChatBuilder is not available in the current agent-framework
                version and suggests upgrading or using the 'standard' workflow mode.
            """
            _ = args
            _ = kwargs
            raise RuntimeError(
                "GroupChatBuilder is not available in this agent-framework version. "
                "Please upgrade agent-framework or use 'standard' workflow mode."
            )

    class _HandoffBuilderStub:
        """Stub for HandoffBuilder when agent_framework is missing."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """
            Initializer for the stubbed HandoffBuilder that always raises when instantiated.

            This constructor accepts any positional and keyword arguments for signature compatibility but does not use them and will raise a RuntimeError indicating the real HandoffBuilder is unavailable in the installed agent-framework.

            Parameters:
                *args: Ignored positional arguments for compatibility.
                **kwargs: Ignored keyword arguments for compatibility.

            Raises:
                RuntimeError: Indicates HandoffBuilder is not available in this agent-framework version and suggests upgrading or using the 'standard' workflow mode.
            """
            _ = args
            _ = kwargs
            raise RuntimeError(
                "HandoffBuilder is not available in this agent-framework version. "
                "Please upgrade agent-framework or use 'standard' workflow mode."
            )

    GroupChatBuilder: type[Any] = _GroupChatBuilderStub  # type: ignore[no-redef]
    HandoffBuilder: type[Any] = _HandoffBuilderStub  # type: ignore[no-redef]


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
) -> WorkflowBuilder | Any:
    """
    Constructs and returns a workflow builder configured for the fleet according to the selected mode.

    Parameters:
        supervisor (DSPyReasoner): The reasoner/coordinator used to create executors and agents.
        context (SupervisorContext): Runtime context providing agents, configuration, and optional clients.
        mode (WorkflowMode): Workflow mode to build; one of "standard", "group_chat", "concurrent", or "handoff".

    Returns:
        WorkflowBuilder or Any: A WorkflowBuilder (or a mode-specific builder/stub) configured for the chosen mode. The concrete return may be a stub type when required agent-framework features are unavailable.
    """
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
) -> Any:
    """
    Construct and configure a Group Chat workflow builder using the supervisor context.

    Parameters:
        context (SupervisorContext): Supervisor context whose `agents`, `openai_client`, and `config`
            are used to set participants, create a chat client, and configure the prompt-based manager.
            - If `agents` is present, they will be added as participants when the builder supports it.
            - If `openai_client` and model configuration are present in `config` (or `config.dspy.model`),
              an OpenAIResponsesClient will be created and passed to the builder's prompt-based manager
              when supported.

    Returns:
        Any: A configured GroupChatBuilder (or a compatible stub) ready for use.

    Raises:
        ValueError: If `context.config` is missing when an OpenAI client is expected and a model cannot be resolved.
    """
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
            from agent_framework._agents import ChatAgent
            from agent_framework._workflows import ManagerSelectionResponse
            from agent_framework.openai import OpenAIResponsesClient

            model_id = "gpt-4.1-mini"
            if context.config:
                cfg_model = getattr(context.config, "model", None)
                if cfg_model:
                    model_id = str(cfg_model)
                else:
                    dspy_cfg = getattr(context.config, "dspy", None)
                    if dspy_cfg:
                        dspy_model = getattr(dspy_cfg, "model", None)
                        if dspy_model:
                            model_id = str(dspy_model)
            else:
                raise ValueError("Model configuration not found in context.")

            # Use OpenAIResponsesClient for consistency with agent-framework best practices.
            chat_client = OpenAIResponsesClient(
                async_client=context.openai_client,
                model_id=model_id,
            )

            # agent-framework 1.0.0b251211 uses an explicit manager agent.
            # The manager must return ManagerSelectionResponse for structured speaker selection.
            manager = ChatAgent(
                chat_client=chat_client,
                name="Coordinator",
                description="Coordinates multi-agent collaboration and selects the next speaker.",
                instructions=(
                    "You are the group chat coordinator. Review the conversation history and select the next "
                    "participant to speak. When ready to finish, set finish=True and provide the final answer "
                    "in final_message."
                ),
                response_format=ManagerSelectionResponse,
            )

            manager_fn = getattr(builder, "set_manager", None)
            if callable(manager_fn):
                manager_fn(manager, display_name="Orchestrator")
            else:
                logger.warning("GroupChatBuilder missing set_manager(); skipping")
        else:
            logger.warning(
                "No OpenAI client available. Group Chat manager might not function correctly."
            )

        return builder


def _build_handoff_workflow(
    supervisor: DSPyReasoner,
    context: SupervisorContext,
) -> Any:
    """
    Constructs and returns a Handoff workflow builder configured with a triage coordinator and full-mesh handoffs.

    The builder will include a created "Triage" coordinator agent (using the OpenAI client and model selected from context.config.model when available), all agents from context as participants, full-mesh handoff edges between specialists and the triage agent, and a termination condition that ends the conversation when the Triage agent posts a message containing "FINAL RESULT:".

    Parameters:
        supervisor (DSPyReasoner): Reasoner/service used by executors (passed through to executors; not inspected here).
        context (SupervisorContext): Supervisor context that must provide `agents` (mapping of agent name to agent descriptor) and an `openai_client` used to create the Triage agent. `context.config.model` is used to override the default model if present.

    Returns:
        HandoffBuilder | Any: A configured HandoffBuilder (or compatible builder object) ready to be used to run the handoff workflow.

    Raises:
        RuntimeError: If no agents are available on the context.
        RuntimeError: If an OpenAI client is required but not present on the context.
    """
    with optional_span("build_handoff_workflow"):
        logger.info("Constructing Handoff Fleet workflow...")

        if not context.agents:
            raise RuntimeError("No agents available for Handoff workflow.")

        # Create a Triage/Coordinator agent
        from agent_framework.openai import OpenAIResponsesClient

        model_id = "gpt-4.1-mini"
        if context.config:
            cfg_model = getattr(context.config, "model", None)
            if cfg_model:
                model_id = str(cfg_model)

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
