"""Analyst Agent Factory

Provides factory function to create the Analyst agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The analyst is responsible for data analysis and generating insights.
"""

try:
    from agent_framework.openai import OpenAIResponsesClient
except ImportError:
    OpenAIResponsesClient = None  # type: ignore[assignment,misc]

from typing import Any

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import get_responses_model_parameter


def create_analyst_agent() -> FleetAgent:
    """
    Create the Analyst agent with data analysis capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Tools are plain Python functions passed as a list.

    Returns:
        FleetAgent: Configured analyst agent with data analysis tools
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("analyst")
    agent_config = config.get("agent", {})

    if OpenAIResponsesClient is None:
        raise AgentConfigurationError(
            "agent_framework is required to create the analyst agent. "
            "Install the 'agent-framework' package to enable this agent."
        )

    # Create OpenAI chat client
    chat_client_kwargs = {
        get_responses_model_parameter(OpenAIResponsesClient): agent_config.get(
            "model", settings.openai_model
        )
    }
    chat_client = OpenAIResponsesClient(**chat_client_kwargs)

    # Import and configure tools based on agent configuration
    from agenticfleet.tools.tool_calling import registry

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = registry.resolve_tools_from_config(tools_config)

    # Fallback to legacy wiring if registry didn't resolve anything
    if not enabled_tools:
        try:
            from agenticfleet.agents.analyst.tools.data_analysis_tools import (
                data_analysis_tool,
                visualization_suggestion_tool,
            )

            for tool_config in tools_config:
                if tool_config.get("name") == "data_analysis_tool" and tool_config.get(
                    "enabled", True
                ):
                    enabled_tools.append(data_analysis_tool)
                if tool_config.get("name") == "visualization_suggestion_tool" and tool_config.get(
                    "enabled", True
                ):
                    enabled_tools.append(visualization_suggestion_tool)
        except Exception:  # pragma: no cover - defensive fallback
            enabled_tools = []

    # Create and return agent with tools
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    context_providers = settings.create_context_providers(
        agent_id=agent_config.get("name"),
    )
    fleet_agent_kwargs: dict[str, Any] = {}
    if context_providers:
        fleet_agent_kwargs["context_providers"] = context_providers

    agent = FleetAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "analyst"),
        tools=enabled_tools,
        runtime_config=config.get("runtime", {}),
        **fleet_agent_kwargs,
    )
    return agent
