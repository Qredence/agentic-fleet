"""Agent factory for creating ChatAgent instances from YAML configuration."""

from __future__ import annotations

import logging
import os
from typing import Any

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from dotenv import load_dotenv

from agentic_fleet.core.registry import ToolRegistry

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

# Base URL is optional; default OpenAI endpoint is used when unset.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating ChatAgent instances from YAML configuration."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        """Initialize AgentFactory.

        Args:
            tool_registry: Optional tool registry for resolving tool names to instances.
                If None, creates a default registry.
        """
        self.tool_registry = tool_registry or ToolRegistry()

    def create_agent(
        self,
        name: str,
        agent_config: dict[str, Any],
    ) -> ChatAgent:
        """Create a ChatAgent instance from configuration.

        Args:
            name: Agent name/identifier (e.g., "planner", "executor")
            agent_config: Agent configuration dictionary from YAML

        Returns:
            Configured ChatAgent instance

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Extract configuration values
        model_id = agent_config.get("model")
        if not model_id:
            raise ValueError(f"Agent '{name}' missing required 'model' field")

        instructions_raw = agent_config.get("instructions", "")
        instructions = self._resolve_instructions(instructions_raw)
        description = agent_config.get("description", "")
        temperature = agent_config.get("temperature", 0.7)
        max_tokens = agent_config.get("max_tokens", 4096)
        store = agent_config.get("store", True)

        # Extract reasoning settings
        reasoning_config = agent_config.get("reasoning", {})
        reasoning_effort = reasoning_config.get("effort", "medium")
        reasoning_verbosity = reasoning_config.get("verbosity", "normal")

        # Resolve tools
        tool_names = agent_config.get("tools", [])
        tools = self._resolve_tools(tool_names)

        # Create OpenAI client
        chat_client = OpenAIResponsesClient(
            model_id=model_id,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL or None,
            reasoning_effort=reasoning_effort,
            reasoning_verbosity=reasoning_verbosity,
            store=store,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Create agent name in PascalCase format
        agent_name = f"{name.capitalize()}Agent"

        # Create ChatAgent
        # Handle tools: if single tool, pass directly; if multiple, pass as tuple/sequence
        # ChatAgent accepts tools as a single tool instance or sequence
        tools_param: Any = None
        if tools:
            tools_param = tools[0] if len(tools) == 1 else tuple(tools)

        agent = ChatAgent(
            name=agent_name,
            description=description or instructions[:100],  # Use instructions as fallback
            instructions=instructions,
            chat_client=chat_client,
            tools=tools_param,
        )

        logger.debug(
            f"Created agent '{agent_name}' with model '{model_id}', "
            f"reasoning_effort='{reasoning_effort}', {len(tools)} tools"
        )

        return agent

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to tool instances.

        Args:
            tool_names: List of tool names from YAML (e.g., ["HostedCodeInterpreterTool"])

        Returns:
            List of tool instances
        """
        tools: list[Any] = []
        for tool_name in tool_names:
            if not isinstance(tool_name, str):
                logger.warning(f"Invalid tool name: {tool_name}, skipping")
                continue

            tool = self.tool_registry.get_tool(tool_name)
            if tool is None:
                logger.warning(f"Tool '{tool_name}' not found in registry, skipping")
                continue

            tools.append(tool)

        return tools

    def _resolve_instructions(self, instructions: Any) -> str:
        """Resolve instructions from Python module reference or return as-is.

        Supports:
        - `prompts.{module_name}` - Import from prompts module and call get_instructions()
        - Plain string - Return as-is (backward compatible)

        Args:
            instructions: Instructions string, possibly a module reference like "prompts.planner"

        Returns:
            Resolved instructions string
        """
        if not isinstance(instructions, str):
            # Coerce non-string instructions to string to satisfy return type contract.
            return str(instructions)

        # Check if it's a prompt module reference (e.g., "prompts.planner")
        if instructions.startswith("prompts."):
            try:
                module_name = instructions[len("prompts.") :]
                # Import the prompt module dynamically
                import importlib

                prompt_module = importlib.import_module(f"agentic_fleet.prompts.{module_name}")
                if hasattr(prompt_module, "get_instructions"):
                    # Cast return to str to satisfy strict typing (legacy modules may return Any)
                    resolved_instructions = str(prompt_module.get_instructions())
                    logger.debug(
                        f"Resolved instructions from module 'prompts.{module_name}' "
                        f"({len(resolved_instructions)} chars)"
                    )
                    return resolved_instructions
                else:
                    logger.warning(
                        f"Prompt module 'prompts.{module_name}' missing get_instructions() function, "
                        "using instructions as-is"
                    )
                    return instructions
            except ImportError as e:
                logger.warning(
                    f"Failed to import prompt module 'prompts.{instructions[len('prompts.') :]}': {e}, "
                    "using instructions as-is"
                )
                return instructions
            except Exception as e:
                logger.warning(
                    f"Error resolving instructions from '{instructions}': {e}, "
                    "using instructions as-is"
                )
                return instructions

        # Plain string - return as-is (backward compatible)
        return instructions


class MagenticCoordinator:
    """Orchestrator for MagenticFleetWorkflow coordination."""

    def __init__(self, agent_factory: AgentFactory | None = None) -> None:
        """Initialize coordinator.

        Args:
            agent_factory: Optional agent factory. If None, creates a default one.
        """
        self.agent_factory = agent_factory or AgentFactory()
