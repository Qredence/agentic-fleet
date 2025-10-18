"""Researcher Agent Factory

Provides factory function to create the Researcher agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The researcher is responsible for information gathering and web search operations.

Usage:
    from agenticfleet.agents.researcher import create_researcher_agent

    researcher = create_researcher_agent()
    result = await researcher.run("Search for Python best practices")
"""

try:
    from agent_framework.openai import OpenAIResponsesClient
except ImportError:
    OpenAIResponsesClient = None  # type: ignore[misc, assignment]

from typing import Any

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import get_responses_model_parameter


def create_researcher_agent() -> FleetAgent:
    """
    Create the Researcher agent with web search capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Tools are plain Python functions passed as a list.

    Returns:
        FleetAgent: Configured researcher agent with web search tools
    """
    # Load researcher-specific configuration
    config = settings.load_agent_config("researcher")
    agent_config = config.get("agent", {})

    if OpenAIResponsesClient is None:
        raise AgentConfigurationError(
            "agent_framework is required to create the researcher agent. "
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
    from agenticfleet.agents.researcher.tools.web_search_tools import web_search_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "web_search_tool" and tool_config.get("enabled", True):
            enabled_tools.append(web_search_tool)

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
        name=agent_config.get("name", "researcher"),
        tools=enabled_tools,
        runtime_config=config.get("runtime", {}),
        **fleet_agent_kwargs,
    )
    return agent
