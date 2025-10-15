"""Analyst Agent Factory

Provides factory function to create the Analyst agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The analyst is responsible for data analysis and generating insights.
"""

from typing import Any

from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.agents.base import AgenticFleetChatAgent
from agenticfleet.config import settings


def create_analyst_agent() -> AgenticFleetChatAgent:
    """
    Create the Analyst agent with data analysis capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Tools are plain Python functions passed as a list.

    Returns:
        AgenticFleetChatAgent: Configured analyst agent with data analysis tools
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("analyst")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

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
    agent = AgenticFleetChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "analyst"),
        tools=enabled_tools,
        runtime_config=config.get("runtime", {}),
    )

    return agent
