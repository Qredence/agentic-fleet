"""Magentic Agent Framework wrapper for cleaner integration.

This module provides a high-level interface for working with Magentic workflows,
similar to the notebook example pattern. It abstracts the underlying
MagenticOrchestratorExecutor and StandardMagenticManager components.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent_framework import ChatAgent, MagenticBuilder
from agent_framework.openai import OpenAIResponsesClient

logger = logging.getLogger(__name__)


class MagenticAgentFramework:
    """Wrapper class for Magentic agent-framework integration.

    Provides a clean interface for creating agents and workflows, similar to
    the notebook example pattern. Abstracts the underlying Magentic components
    while maintaining compatibility with YAML-driven configuration.
    """

    @staticmethod
    def configure_logging(level: str | int = logging.INFO) -> None:
        """Configure console-friendly logging similar to notebook example.

        Args:
            level: Logging level (string like "INFO", "DEBUG", or logging constant)
        """
        if isinstance(level, str):
            numeric_level = getattr(logging, level.upper(), logging.INFO)
        else:
            numeric_level = level

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )

        logger.info(f"✓ Logging configured at {logging.getLevelName(numeric_level)} level")

    @staticmethod
    def create_agent(
        name: str,
        description: str,
        instructions: str,
        model_id: str = "gpt-5-mini",
        reasoning_effort: str = "medium",
        reasoning_verbosity: str = "normal",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        store: bool = True,
        tools: Any = None,
    ) -> ChatAgent:
        """Create a ChatAgent with standardized configuration.

        Args:
            name: Agent name (e.g., "ExecutorAgent")
            description: Agent description for manager understanding
            instructions: System instructions for the agent
            model_id: Model identifier (default: "gpt-5-mini")
            reasoning_effort: Reasoning effort level ("low", "medium", "high")
            reasoning_verbosity: Reasoning verbosity ("normal", "verbose")
            temperature: Temperature setting (0.0-2.0)
            max_tokens: Maximum tokens in response
            store: Whether to store conversations
            tools: Optional tools to attach to agent

        Returns:
            Configured ChatAgent instance
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. " "Set it before creating agents."
            )

        chat_client = OpenAIResponsesClient(
            model_id=model_id,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            reasoning_verbosity=reasoning_verbosity,
            store=store,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        agent = ChatAgent(
            name=name,
            description=description,
            instructions=instructions,
            chat_client=chat_client,
            tools=tools,
        )

        logger.debug(
            f"Created agent '{name}' with model '{model_id}', "
            f"reasoning_effort='{reasoning_effort}'"
        )

        return agent

    @staticmethod
    def create_workflow(
        participants: dict[str, ChatAgent],
        manager_model: str = "gpt-5-mini",
        manager_instructions: str | None = None,
        reasoning_effort: str = "high",
        reasoning_verbosity: str = "verbose",
        temperature: float = 0.6,
        max_tokens: int = 8192,
        store: bool = True,
        max_round_count: int = 6,
        max_stall_count: int = 3,
        max_reset_count: int = 2,
    ) -> Any:
        """Create a Magentic workflow with proper manager setup.

        Args:
            participants: Dictionary of agent name -> ChatAgent instances
            manager_model: Model identifier for manager (default: "gpt-5-mini")
            manager_instructions: Optional instructions for manager
            reasoning_effort: Manager reasoning effort ("low", "medium", "high")
            reasoning_verbosity: Manager reasoning verbosity ("normal", "verbose")
            temperature: Manager temperature setting
            max_tokens: Manager max tokens
            store: Whether manager stores conversations
            max_round_count: Maximum conversation rounds
            max_stall_count: Maximum stalls before replanning
            max_reset_count: Maximum resets before termination

        Returns:
            Built Magentic workflow instance
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it before creating workflows."
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

        builder = MagenticBuilder()
        builder = builder.participants(**participants)
        builder = builder.with_standard_manager(
            chat_client=manager_client,
            instructions=manager_instructions,
            max_round_count=max_round_count,
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
        )

        workflow = builder.build()

        logger.info(
            f"Created Magentic workflow with {len(participants)} participants, "
            f"manager model '{manager_model}', max_round_count={max_round_count}"
        )

        return workflow

    @staticmethod
    def from_yaml(workflow_id: str = "magentic_fleet") -> Any:
        """Load workflow from YAML configuration.

        This complements the existing YAML-driven approach by providing
        a programmatic interface.

        Args:
            workflow_id: Workflow identifier from YAML config

        Returns:
            Workflow instance
        """
        from agentic_fleet.api.workflow_factory import WorkflowFactory

        factory = WorkflowFactory()
        workflow = factory.create_from_yaml(workflow_id)

        logger.info(f"Loaded workflow '{workflow_id}' from YAML configuration")

        return workflow
