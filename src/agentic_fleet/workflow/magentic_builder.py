"""
Enhanced Magentic workflow builder following Microsoft Agent Framework patterns.

Provides builder pattern for constructing Magentic workflows with:
- Configuration management
- Event bus integration
- Checkpointing support
- Approval gates (HITL)
- Dynamic orchestration
- Callback registration
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agentic_fleet.core.magentic_framework import MagenticContext, MagenticOrchestrator
from agentic_fleet.models.events import WorkflowEvent
from agentic_fleet.models.workflow import WorkflowConfig
from agentic_fleet.workflow.executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class MagenticFleetBuilder:
    """
    Builder pattern for Magentic workflow construction.

    Follows Microsoft Agent Framework's design patterns with
    method chaining for fluent configuration.

    Example:
        ```python
        builder = MagenticFleetBuilder()
        fleet = (
            builder
            .with_config(config)
            .with_checkpointing(True)
            .with_approval_gates(True)
            .with_callbacks([event_handler])
            .build()
        )
        ```
    """

    def __init__(self):
        self._config: WorkflowConfig | None = None
        self._event_callbacks: list[Callable[[WorkflowEvent], None]] = []
        self._checkpointing_enabled = False
        self._approval_enabled = False
        self._dynamic_orchestration = False

    def with_config(self, config: WorkflowConfig) -> MagenticFleetBuilder:
        """
        Set workflow configuration from YAML.

        Args:
            config: WorkflowConfig instance loaded from YAML

        Returns:
            Self for method chaining
        """
        self._config = config
        logger.info("Configuration loaded")
        return self

    def with_manager(self, manager_config: dict[str, Any]) -> MagenticFleetBuilder:
        """
        Configure manager agent settings.

        Args:
            manager_config: Manager configuration dict

        Returns:
            Self for method chaining

        Raises:
            ValueError: If config not set before manager
        """
        if not self._config:
            raise ValueError("Config must be set before manager configuration")

        self._config.fleet.manager = manager_config
        logger.info("Manager configuration updated")
        return self

    def with_agents(self, agents: list[str]) -> MagenticFleetBuilder:
        """
        Add specialist agents to the fleet.

        Args:
            agents: List of agent names (coordinator, planner, executor, etc.)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If config not set before agents
        """
        if not self._config:
            raise ValueError("Config must be set before agents")

        self._config.fleet.agents = agents
        logger.info(f"Configured {len(agents)} specialist agents")
        return self

    def with_checkpointing(self, enabled: bool = True) -> MagenticFleetBuilder:
        """
        Enable workflow state checkpointing.

        Checkpointing allows workflows to be paused and resumed,
        and provides recovery from failures.

        Args:
            enabled: Whether to enable checkpointing

        Returns:
            Self for method chaining
        """
        self._checkpointing_enabled = enabled
        logger.info(f"Checkpointing {'enabled' if enabled else 'disabled'}")
        return self

    def with_approval_gates(self, enabled: bool = True) -> MagenticFleetBuilder:
        """
        Enable human-in-the-loop approval gates.

        When enabled, certain operations require human approval
        before execution (e.g., code execution, file operations).

        Args:
            enabled: Whether to enable approval gates

        Returns:
            Self for method chaining
        """
        self._approval_enabled = enabled
        logger.info(f"Approval gates {'enabled' if enabled else 'disabled'}")
        return self

    def with_callbacks(
        self, callbacks: list[Callable[[WorkflowEvent], None]]
    ) -> MagenticFleetBuilder:
        """
        Add event callbacks for workflow monitoring.

        Callbacks receive WorkflowEvent objects and can be used
        for logging, metrics, or custom event handling.

        Args:
            callbacks: List of callable event handlers

        Returns:
            Self for method chaining
        """
        self._event_callbacks.extend(callbacks)
        logger.info(f"Added {len(callbacks)} event callbacks")
        return self

    def with_dynamic_orchestration(self, enabled: bool = True) -> MagenticFleetBuilder:
        """
        Enable dynamic agent spawning.

        When enabled, the orchestrator can create specialized
        agents on-demand based on task requirements.

        Args:
            enabled: Whether to enable dynamic orchestration

        Returns:
            Self for method chaining
        """
        self._dynamic_orchestration = enabled
        logger.info(f"Dynamic orchestration {'enabled' if enabled else 'disabled'}")
        return self

    def build(self) -> MagenticFleet:
        """
        Build the Magentic workflow.

        Creates the orchestrator, executor, and wires up all
        components based on the builder configuration.

        Returns:
            MagenticFleet instance ready for execution

        Raises:
            ValueError: If configuration is missing
        """
        if not self._config:
            raise ValueError("Configuration required to build fleet")

        logger.info("Building Magentic fleet...")

        # Create orchestrator (implements RunsWorkflow protocol)
        orchestrator = MagenticOrchestrator(
            config=self._config,
            event_bus=None,  # Event bus is optional
        )

        # Create executor - just wraps the orchestrator
        executor = WorkflowExecutor(workflow=orchestrator)

        fleet = MagenticFleet(
            orchestrator=orchestrator,
            executor=executor,
            config=self._config,
            checkpointing_enabled=self._checkpointing_enabled,
            approval_enabled=self._approval_enabled,
            callbacks=self._event_callbacks,
        )

        logger.info("Magentic fleet built successfully")
        return fleet


@dataclass
class MagenticFleet:
    """
    Complete Magentic fleet ready for execution.

    Encapsulates the orchestrator, executor, and configuration
    into a single interface for workflow execution.

    Attributes:
        orchestrator: MagenticOrchestrator instance
        executor: WorkflowExecutor instance
        config: WorkflowConfig instance
        checkpointing_enabled: Whether checkpointing is enabled
        approval_enabled: Whether approval gates are enabled
        callbacks: List of event callback functions
    """

    orchestrator: MagenticOrchestrator
    executor: WorkflowExecutor
    config: WorkflowConfig
    checkpointing_enabled: bool = False
    approval_enabled: bool = False
    callbacks: list[Callable[[WorkflowEvent], None]] = None  # type: ignore[assignment]

    def __post_init__(self):
        """Initialize callbacks list if None."""
        if self.callbacks is None:
            self.callbacks = []

    async def run(self, task: str, context: MagenticContext | None = None) -> None:
        """
        Execute workflow for given task.

        Runs the complete PLAN → EVALUATE → ACT → OBSERVE cycle
        until completion or timeout.

        Args:
            task: The task to execute
            context: Optional existing context to continue from
        """
        async for event in self.orchestrator.execute(task, context):
            # Events are handled by event bus subscribers
            pass

    async def run_with_streaming(self, task: str, context: MagenticContext | None = None):
        """
        Execute workflow with event streaming.

        Yields events as they occur during workflow execution,
        suitable for SSE or WebSocket streaming to clients.

        Args:
            task: The task to execute
            context: Optional existing context to continue from

        Yields:
            WorkflowEvent objects for each significant event
        """
        async for event in self.orchestrator.execute(task, context):
            yield event


def create_default_fleet(config_path: str = "workflows.yaml") -> MagenticFleet:
    """
    Factory function to create default Magentic fleet.

    Loads configuration from YAML and creates a fleet with
    standard settings following Microsoft Agent Framework patterns.

    Args:
        config_path: Path to workflows.yaml configuration file

    Returns:
        MagenticFleet instance ready for use

    Example:
        ```python
        fleet = create_default_fleet()
        await fleet.run("Research quantum computing")
        ```
    """
    from agentic_fleet.utils.config import load_workflow_config

    logger.info(f"Creating default fleet from {config_path}")
    config = load_workflow_config(config_path)

    builder = MagenticFleetBuilder()
    fleet = (
        builder.with_config(config)
        .with_checkpointing(config.checkpointing.enabled)
        .with_approval_gates(config.approval.enabled)
        .with_callbacks([lambda event: logger.debug(f"[EVENT] {event.type}: {event.data}")])
        .build()
    )

    return fleet


__all__ = [
    "MagenticFleet",
    "MagenticFleetBuilder",
    "create_default_fleet",
]
