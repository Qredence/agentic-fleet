"""Fleet builder using Microsoft Agent Framework's MagenticBuilder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import MagenticBuilder
from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.config import settings
from agenticfleet.core.logging import get_logger
from agenticfleet.fleet import callbacks

if TYPE_CHECKING:
    from agent_framework import AgentProtocol, CheckpointStorage, Workflow

logger = get_logger(__name__)


class FleetBuilder:
    """
    Constructs Magentic workflow with AgenticFleet conventions.

    Uses Microsoft Agent Framework's MagenticBuilder to create a workflow
    with StandardMagenticManager (planner) and MagenticAgentExecutor-wrapped
    specialist agents (participants).
    """

    def __init__(self) -> None:
        """Initialize the fleet builder with default configuration."""
        fleet_config = settings.workflow_config.get("fleet", {})
        self.config = fleet_config

        # Extract orchestrator settings
        orchestrator_config = fleet_config.get("orchestrator", {})
        self.max_round_count = orchestrator_config.get("max_round_count", 15)
        self.max_stall_count = orchestrator_config.get("max_stall_count", 3)
        self.max_reset_count = orchestrator_config.get("max_reset_count", 2)

        # Extract manager settings
        manager_config = fleet_config.get("manager", {})
        self.manager_model = manager_config.get("model", settings.openai_model)
        self.manager_instructions = manager_config.get(
            "instructions",
            self._default_manager_instructions(),
        )
        self.manager_reasoning = manager_config.get("reasoning")

        # Plan review settings
        plan_review_config = fleet_config.get("plan_review", {})
        self.plan_review_enabled = plan_review_config.get("enabled", False)

        # Callback settings
        callback_config = fleet_config.get("callbacks", {})
        self.streaming_enabled = callback_config.get("streaming_enabled", True)
        self.log_progress = callback_config.get("log_progress_ledger", True)

        self.builder = MagenticBuilder()

    def _default_manager_instructions(self) -> str:
        """Return default manager instructions for the planner."""
        return """You are coordinating a fleet of specialized AI agents to solve complex tasks.

Available agents:
- researcher: Performs web searches and gathers information from online sources
- coder: Executes Python code, analyzes code quality, and performs computations
- analyst: Analyzes data, creates visualizations, and provides insights

Your responsibilities:
1. Break down complex tasks into steps
2. Delegate to the appropriate agent based on their capabilities
3. Synthesize findings from all agents
4. Provide a comprehensive FINAL_ANSWER when the task is complete

Always explain your reasoning and include evidence from agent responses."""

    def with_agents(self, agents: dict[str, AgentProtocol]) -> FleetBuilder:
        """
        Register agent participants in the workflow.

        Args:
            agents: Dictionary mapping agent names to AgentProtocol instances.

        Returns:
            FleetBuilder instance for method chaining.
        """
        # MagenticBuilder.participants() expects **kwargs, so unpack the dictionary
        self.builder = self.builder.participants(**agents)
        return self

    def with_manager(
        self,
        instructions: str | None = None,
        model: str | None = None,
    ) -> FleetBuilder:
        """
        Configure StandardMagenticManager with custom prompts.

        Args:
            instructions: Custom manager instructions (uses default if None).
            model: Model to use for the manager (uses config if None).

        Returns:
            Self for method chaining.
        """
        manager_instructions = instructions or self.manager_instructions
        manager_model = model or self.manager_model

        logger.info(f"Configuring StandardMagenticManager with model: {manager_model}")

        # Create OpenAI client for the manager
        client_kwargs: dict[str, Any] = {
            "model": manager_model,
            "api_key": settings.openai_api_key,
        }
        if self.manager_reasoning:
            client_kwargs["reasoning"] = self.manager_reasoning

        chat_client = OpenAIResponsesClient(**client_kwargs)

        # Configure the manager with custom settings
        self.builder = self.builder.with_standard_manager(
            chat_client=chat_client,
            instructions=manager_instructions,
            max_round_count=self.max_round_count,
            max_stall_count=self.max_stall_count,
            max_reset_count=self.max_reset_count,
        )

        return self

    def with_observability(self) -> FleetBuilder:
        """
        Add streaming and progress callbacks for observability.

        Returns:
            Self for method chaining.
        """
        if not self.streaming_enabled and not self.log_progress:
            logger.debug("Observability callbacks disabled")
            return self

        logger.info("Enabling observability callbacks")

        # Import unified callback event types
        from agent_framework import (
            MagenticAgentDeltaEvent,
            MagenticAgentMessageEvent,
            MagenticCallbackEvent,
            MagenticCallbackMode,
            MagenticFinalResultEvent,
            MagenticOrchestratorMessageEvent,
        )

        # Create unified callback that routes to specific handlers
        async def unified_callback(event: MagenticCallbackEvent) -> None:
            """Route MagenticCallbackEvents to appropriate handlers."""
            if isinstance(event, MagenticOrchestratorMessageEvent):
                # Dispatch dictionary for orchestrator message kinds
                orchestrator_handlers = {
                    "task_ledger": lambda msg: self.log_progress and callbacks.plan_creation_callback(msg),
                    "progress_ledger": lambda msg: self.log_progress and callbacks.progress_ledger_callback(msg),
                    "notice": lambda msg: msg and callbacks.notice_callback(str(msg)),
                }
                handler = orchestrator_handlers.get(event.kind)
                if handler:
                    result = handler(event.message)
                    if result:
                        await result
                # Could log other kinds: user_task, instruction, notice
            elif isinstance(event, MagenticAgentDeltaEvent):
                # Handle streaming agent deltas (buffered; no immediate console output)
                if self.streaming_enabled:
                    await callbacks.agent_delta_callback(event)
            elif isinstance(event, MagenticAgentMessageEvent):
                # Handle final agent messages
                if self.streaming_enabled and event.message:
                    await callbacks.agent_message_callback(event.message)
            elif isinstance(event, MagenticFinalResultEvent):
                # Handle final result
                if event.message and self.log_progress:
                    logger.info(f"[Fleet] Final result: {event.message.text[:200]}...")

        # Register unified callback with appropriate mode
        mode = (
            MagenticCallbackMode.STREAMING
            if self.streaming_enabled
            else MagenticCallbackMode.NON_STREAMING
        )
        self.builder = self.builder.on_event(unified_callback, mode=mode)

        return self

    def with_checkpointing(
        self,
        storage: CheckpointStorage | None = None,
    ) -> FleetBuilder:
        """
        Enable checkpoint persistence for workflow state.

        Args:
            storage: CheckpointStorage instance (uses default if None).

        Returns:
            Self for method chaining.
        """
        if storage is None:
            logger.debug("No checkpoint storage provided, skipping")
            return self

        logger.info("Enabling checkpointing with provided storage")
        self.builder = self.builder.with_checkpointing(storage)

        return self

    def with_plan_review(
        self,
        enabled: bool | None = None,
    ) -> FleetBuilder:
        """
        Enable human-in-the-loop plan review.

        Args:
            enabled: Whether to enable plan review (uses config if None).

        Returns:
            Self for method chaining.
        """
        plan_review = enabled if enabled is not None else self.plan_review_enabled

        if plan_review:
            logger.info("Enabling plan review for HITL")
            self.builder = self.builder.with_plan_review(True)
        else:
            logger.debug("Plan review disabled")

        return self

    def build(self) -> Workflow:
        """
        Build and return the Magentic workflow.

        Returns:
            Configured Workflow instance ready for execution.
        """
        logger.info("Building Magentic workflow")
        workflow = self.builder.build()
        logger.info("Magentic workflow built successfully")
        return workflow  # type: ignore[return-value]
