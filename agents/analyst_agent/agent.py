"""Analyst Agent Factory

Provides factory function to create the Analyst agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The analyst is responsible for data analysis and generating insights.
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from config.settings import settings


def create_analyst_agent() -> ChatAgent:
    """
    Create the Analyst agent with data analysis capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIChatClient. Tools are plain Python functions passed as a list.

    Returns:
        ChatAgent: Configured analyst agent with data analysis tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("agents/analyst_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIChatClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Import and configure tools based on agent configuration
    from .tools.data_analysis_tools import (
        data_analysis_tool,
        visualization_suggestion_tool,
    )

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "data_analysis_tool" and tool_config.get("enabled", True):
            enabled_tools.append(data_analysis_tool)
        if tool_config.get("name") == "visualization_suggestion_tool" and tool_config.get(
            "enabled", True
        ):
            enabled_tools.append(visualization_suggestion_tool)

    # Create and return agent with tools
    return ChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "analyst"),
        temperature=agent_config.get("temperature", 0.2),
        tools=enabled_tools,
    )
