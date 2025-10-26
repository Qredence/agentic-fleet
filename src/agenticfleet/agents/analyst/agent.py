"""Analyst Agent Factory

Provides factory function to create the Analyst agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The analyst is responsible for data analysis and generating insights.
"""

from typing import Any

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import create_chat_client


def create_analyst_agent() -> FleetAgent:
    """
    Create the Analyst agent with data analysis capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient or LiteLLMClient based on configuration.
    Tools are plain Python functions passed as a list.

    Returns:
    FleetAgent: Configured analyst agent with data analysis tools
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("analyst")
    agent_config = config.get("agent", {})

    # Get model from config or use default
    model = agent_config.get("model", settings.openai_model)

    # Determine which client to use based on settings
    use_litellm = settings.use_litellm
    if use_litellm and settings.litellm_model:
        # Use LiteLLM model if configured
        model = settings.litellm_model

    try:
        # Create chat client using factory
        chat_client = create_chat_client(
            model=model,
            use_litellm=use_litellm,
            api_key=settings.litellm_api_key if use_litellm else None,
            base_url=settings.litellm_base_url if use_litellm else None,
            timeout=settings.litellm_timeout if use_litellm else None,
        )
    except ImportError as e:
        raise AgentConfigurationError(
            f"Required client library not available: {e}. "
            "Install the appropriate package to enable this agent."
        ) from e

    # Import and configure tools based on agent configuration
    from agenticfleet.agents.analyst.tools.data_analysis_tools import (
        data_analysis_tool,
        visualization_suggestion_tool,
    )

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools: list[Any] = []

    for tool_config in tools_config:
        if tool_config.get("name") == "data_analysis_tool" and tool_config.get("enabled", True):
            enabled_tools.append(data_analysis_tool)
        if tool_config.get("name") == "visualization_suggestion_tool" and tool_config.get(
            "enabled", True
        ):
            enabled_tools.append(visualization_suggestion_tool)

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
