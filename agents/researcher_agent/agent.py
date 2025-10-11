"""Researcher Agent Factory

Provides factory function to create the Researcher agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The researcher is responsible for information gathering and web search operations.

Usage:
    from agents.researcher_agent.agent import create_researcher_agent

    researcher = create_researcher_agent()
    result = await researcher.run("Search for Python best practices")
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from config.settings import settings


def create_researcher_agent() -> ChatAgent:
    """
    Create the Researcher agent with web search capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Tools are plain Python functions passed as a list.

    Returns:
        ChatAgent: Configured researcher agent with web search tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load researcher-specific configuration
    config = settings.load_agent_config("agents/researcher_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Import and configure tools based on agent configuration
    from .tools.web_search_tools import web_search_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "web_search_tool" and tool_config.get("enabled", True):
            enabled_tools.append(web_search_tool)

    # Create and return agent with tools
    return ChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "researcher"),
        temperature=agent_config.get("temperature", 0.3),
        tools=enabled_tools,
    )
