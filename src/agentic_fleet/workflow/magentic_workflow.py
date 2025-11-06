"""Magentic Fleet workflow builder and implementation."""

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from agent_framework import MagenticBuilder
from agent_framework.openai import OpenAIResponsesClient

from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent
from agentic_fleet.models.workflow import WorkflowConfig
from agentic_fleet.workflow.events import WorkflowEventBridge

logger = logging.getLogger(__name__)


class MagenticFleetWorkflow(RunsWorkflow):
    """Magentic Fleet workflow implementation."""

    def __init__(self, workflow: Any) -> None:
        """Initialize workflow.

        Args:
            workflow: Built Magentic workflow instance from MagenticBuilder
        """
        self._workflow = workflow
        self._event_bridge = WorkflowEventBridge()

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        """Run the workflow and stream events.

        Args:
            message: Input message to process

        Yields:
            WorkflowEvent instances as workflow executes
        """
        try:
            logger.info(
                f"[MAGENTIC] Processing message with multi-agent orchestration: {message[:100]}"
            )

            last_agent_id: str | None = None
            last_kind: str | None = None
            accumulated_content = ""
            agent_buffers: dict[str, str] = {}

            async for event in self._workflow.run_stream(message):
                # Zero-copy conversion: convert and yield immediately
                converted_event = self._event_bridge.convert_event(event, openai_format=True)

                # Emit progress events based on orchestrator message kind
                if converted_event.get("type") == "orchestrator.message":
                    kind = converted_event.get("data", {}).get("kind", "")
                    if kind != last_kind:
                        if kind == "task_ledger":
                            yield {
                                "type": "progress",
                                "data": {
                                    "stage": "planning",
                                    "message": "Manager creating task plan",
                                },
                            }
                        elif kind == "progress_ledger":
                            yield {
                                "type": "progress",
                                "data": {
                                    "stage": "evaluating",
                                    "message": "Manager evaluating progress",
                                },
                            }
                        last_kind = kind

                # Track accumulated content for delta events (similar to fast-path)
                if converted_event.get("type") == "message.delta":
                    agent_id = converted_event.get("data", {}).get("agent_id")
                    delta = converted_event.get("data", {}).get("delta", "")

                    # Accumulate content globally and per-agent
                    if delta:
                        accumulated_content += delta
                        if agent_id:
                            agent_buffers.setdefault(agent_id, "")
                            agent_buffers[agent_id] += delta

                    # Emit progress events for agent transitions
                    if agent_id and agent_id != last_agent_id:
                        # Agent change detected - emit progress event
                        if last_agent_id is not None:
                            yield {
                                "type": "progress",
                                "data": {
                                    "stage": "agent.complete",
                                    "agent_id": last_agent_id,
                                    "message": f"{last_agent_id} completed",
                                    "accumulated": agent_buffers.get(last_agent_id, ""),
                                },
                            }
                        yield {
                            "type": "progress",
                            "data": {
                                "stage": "agent.starting",
                                "agent_id": agent_id,
                                "message": f"{agent_id} starting",
                            },
                        }
                        last_agent_id = agent_id

                    # Add accumulated content to delta event (matching fast-path pattern)
                    converted_event["data"]["accumulated"] = accumulated_content
                    if agent_id:
                        converted_event["data"]["agent_accumulated"] = agent_buffers.get(
                            agent_id, ""
                        )

                # Yield immediately without buffering (zero-copy passthrough)
                yield converted_event

            # Log completion with metrics (similar to fast-path)
            logger.info(
                f"[MAGENTIC] Completed response ({len(accumulated_content)} chars total, "
                f"{len(agent_buffers)} agents participated)"
            )

        except Exception as e:
            logger.error(f"[MAGENTIC] Workflow execution failed: {e}")
            logger.exception("Full traceback:", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "message": f"Magentic workflow error: {e!s}",
                    "error": str(e),
                },
            }
            raise


class MagenticFleetWorkflowBuilder:
    """Builder for creating Magentic Fleet workflows from configuration."""

    def __init__(self) -> None:
        """Initialize workflow builder."""
        from agentic_fleet.agents import AgentFactory

        self.agent_factory = AgentFactory()

    def build(self, config: WorkflowConfig) -> MagenticFleetWorkflow:
        """Build a Magentic Fleet workflow from configuration.

        Args:
            config: Workflow configuration from YAML

        Returns:
            Configured MagenticFleetWorkflow instance

        Raises:
            ValueError: If configuration is invalid
        """
        if config.id != "magentic_fleet":
            raise ValueError(
                f"Workflow builder only supports 'magentic_fleet' workflow, got '{config.id}'"
            )

        # Create specialist agents
        # Note: config.agents is already resolved by WorkflowFactory, no need to resolve strings
        specialist_agents: dict[str, Any] = {}
        for agent_name, agent_config in config.agents.items():
            # agent_config should already be a dict from WorkflowFactory resolution
            if not isinstance(agent_config, dict):
                raise ValueError(
                    f"Agent config for '{agent_name}' must be a dict, got {type(agent_config).__name__}"
                )

            # Create agent using AgentFactory
            try:
                agent = self.agent_factory.create_agent(agent_name, agent_config)
                specialist_agents[agent_name] = agent
                logger.info(f"Created agent '{agent_name}' successfully")
            except Exception as e:
                logger.error(f"Failed to create agent '{agent_name}': {e}")
                raise ValueError(f"Agent creation failed for '{agent_name}': {e}") from e

        # Create manager agent
        manager_config = config.manager
        manager_model = manager_config.get("model")
        if not manager_model:
            raise ValueError("Manager configuration missing 'model' field")

        # Extract manager settings
        manager_instructions = manager_config.get("instructions", "")
        reasoning_config = manager_config.get("reasoning", {})
        reasoning_effort = reasoning_config.get("effort", "high")
        reasoning_verbosity = reasoning_config.get("verbosity", "verbose")
        temperature = manager_config.get("temperature", 0.6)
        max_tokens = manager_config.get("max_tokens", 8192)
        store = manager_config.get("store", True)

        # Manager limits
        max_round_count = manager_config.get("max_round_count", 6)
        max_stall_count = manager_config.get("max_stall_count", 3)
        max_reset_count = manager_config.get("max_reset_count", 2)

        # Create manager chat client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it before creating the workflow."
            )

        manager_client = OpenAIResponsesClient(
            model_id=manager_model,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            reasoning_verbosity=reasoning_verbosity,
            store=store,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Build workflow using MagenticBuilder
        builder = MagenticBuilder()

        # Register participants (specialist agents)
        builder = builder.participants(**specialist_agents)

        # Configure manager
        builder = builder.with_standard_manager(
            chat_client=manager_client,
            instructions=manager_instructions if manager_instructions else None,
            max_round_count=max_round_count,
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
        )

        # Build workflow
        workflow = builder.build()

        logger.info(
            f"Built Magentic Fleet workflow with {len(specialist_agents)} agents, "
            f"manager model '{manager_model}', max_round_count={max_round_count}"
        )

        return MagenticFleetWorkflow(workflow)
