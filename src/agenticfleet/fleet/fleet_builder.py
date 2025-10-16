"""Fleet builder using Microsoft Agent Framework's MagenticBuilder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.logging import get_logger
from agenticfleet.core.openai import get_responses_model_parameter
from agenticfleet.fleet.callbacks import ConsoleCallbacks

try:  # pragma: no cover - runtime import guard
    from agent_framework import MagenticBuilder as _RealMagenticBuilder
    from agent_framework.openai import OpenAIResponsesClient as _RealOpenAIResponsesClient
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments
    _RealMagenticBuilder = None  # type: ignore
    _RealOpenAIResponsesClient = None  # type: ignore


if TYPE_CHECKING:
    from agent_framework import AgentProtocol, CheckpointStorage, Workflow


class _FallbackOpenAIResponsesClient:
    """Minimal stand-in when Microsoft Agent Framework is not installed."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _FallbackWorkflow:
    """Workflow placeholder that raises if execution is attempted without dependency."""

    async def run(self, *_: Any, **__: Any) -> Any:
        raise AgentConfigurationError(
            "agent_framework is required to execute workflows. Install 'agent-framework' to "
            "enable Magentic orchestration."
        )


class _FallbackMagenticBuilder:
    """No-op MagenticBuilder replacement for test environments."""

    def __init__(self) -> None:
        self._workflow = _FallbackWorkflow()

    def participants(self, **kwargs: Any) -> _FallbackMagenticBuilder:
        self.participants_kwargs = kwargs
        return self

    def with_standard_manager(self, **kwargs: Any) -> _FallbackMagenticBuilder:
        self.manager_kwargs = kwargs
        return self

    def on_event(self, *_: Any, **__: Any) -> _FallbackMagenticBuilder:
        return self

    def with_checkpointing(self, *_: Any, **__: Any) -> _FallbackMagenticBuilder:
        return self

    def with_plan_review(self, *_: Any, **__: Any) -> _FallbackMagenticBuilder:
        return self

    def build(self) -> _FallbackWorkflow:
        return self._workflow


MagenticBuilder = _RealMagenticBuilder or _FallbackMagenticBuilder  # type: ignore[truthy-function,unreachable]
OpenAIResponsesClient = _RealOpenAIResponsesClient or _FallbackOpenAIResponsesClient  # type: ignore[truthy-function,unreachable]
_AGENT_FRAMEWORK_AVAILABLE = _RealMagenticBuilder is not None

logger = get_logger(__name__)


class FleetBuilder:
    """
    Constructs Magentic workflow with AgenticFleet conventions.

    Uses Microsoft Agent Framework's MagenticBuilder to create a workflow
    with StandardMagenticManager (planner) and MagenticAgentExecutor-wrapped
    specialist agents (participants).
    """

    def __init__(self, console_callbacks: ConsoleCallbacks | None = None) -> None:
        """Initialize the fleet builder with default configuration."""
        workflow_defaults = settings.workflow_config.get("workflow", {})
        fleet_config = settings.workflow_config.get("fleet", {})
        self.config = fleet_config
        self.console_callbacks = console_callbacks or ConsoleCallbacks()

        # Extract orchestrator settings
        orchestrator_config = fleet_config.get("orchestrator", {})
        self.max_round_count = orchestrator_config.get(
            "max_round_count", workflow_defaults.get("max_rounds", 15)
        )
        self.max_stall_count = orchestrator_config.get(
            "max_stall_count", workflow_defaults.get("max_stalls", 3)
        )
        self.max_reset_count = orchestrator_config.get(
            "max_reset_count", workflow_defaults.get("max_resets", 2)
        )

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

        self._using_fallback_builder = not _AGENT_FRAMEWORK_AVAILABLE
        if self._using_fallback_builder:
            logger.warning(
                "agent_framework package not available; using fallback MagenticBuilder stub. "
                "Install 'agent-framework' to enable full workflow execution."
            )

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
        api_key = settings.require_openai_api_key()

        client_kwargs: dict[str, Any] = {
            get_responses_model_parameter(OpenAIResponsesClient): manager_model,
            "api_key": api_key,
        }
        if self.manager_reasoning:
            client_kwargs["reasoning"] = self.manager_reasoning

        chat_client = OpenAIResponsesClient(**client_kwargs)

        # Configure the manager with custom settings
        # chat_client is OpenAIResponsesClient which implements ChatClientProtocol when
        # agent_framework is installed; fallback is only for import-time compatibility
        self.builder = self.builder.with_standard_manager(
            chat_client=cast(Any, chat_client),
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

        if not _AGENT_FRAMEWORK_AVAILABLE:
            logger.warning(
                "agent_framework not available; skipping observability callbacks. "
                "Install 'agent-framework' to enable streaming telemetry."
            )
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
                # Handle orchestrator messages (plan, instructions, etc.)
                if event.kind == "task_ledger" and self.log_progress:
                    await self.console_callbacks.plan_creation_callback(event.message)
                elif event.kind == "progress_ledger" and self.log_progress:
                    await self.console_callbacks.progress_ledger_callback(event.message)
                elif event.kind == "notice" and event.message:
                    await self.console_callbacks.notice_callback(str(event.message))
                # Could log other kinds: user_task, instruction, notice
            elif isinstance(event, MagenticAgentDeltaEvent):
                # Handle streaming agent deltas (buffered; no immediate console output)
                if self.streaming_enabled:
                    await self.console_callbacks.agent_delta_callback(event)
            elif isinstance(event, MagenticAgentMessageEvent):
                # Handle final agent messages
                if self.streaming_enabled and event.message:
                    await self.console_callbacks.agent_message_callback(event.message)
            elif isinstance(event, MagenticFinalResultEvent):
                # Handle final result
                if event.message and self.log_progress:
                    logger.info(f"[Fleet] Final result: {event.message.text[:200]}...")
                    await self.console_callbacks.final_answer_callback(event.message)

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
        if self._using_fallback_builder:
            logger.warning(
                "agent_framework is not installed; returning fallback workflow stub. "
                "Install 'agent-framework' to enable Magentic execution."
            )
        logger.info("Magentic workflow built successfully")
        return workflow  # type: ignore[return-value]
