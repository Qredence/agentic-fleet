"""
Researcher Agent Factory

This module provides the factory function to create and configure the Researcher agent.
The agent is responsible for information gathering and web search operations.

The factory:
1. Loads agent-specific configuration from agent_config.yaml
2. Creates an OpenAI chat client with appropriate settings
3. Imports and configures the web search tool
4. Instantiates a ChatAgent with tools enabled

Usage:
    from agents.researcher_agent.agent import create_researcher_agent

    researcher = create_researcher_agent()
    result = await researcher.run("Search for Python best practices")
"""

from azure.ai.agent.client import AzureAIAgentClient

from config.settings import settings


def create_researcher_agent(client: AzureAIAgentClient, context_provider):
    """
    Create the Researcher agent with web search capabilities.

    This function:
    - Loads configuration from agents/researcher_agent/agent_config.yaml
    - Creates an agent with the provided AzureAIAgentClient
    - Enables the web_search_tool if configured
    - Returns a fully configured agent instance

    Args:
        client: The AzureAIAgentClient instance.

    Returns:
        AIAgent: Configured researcher agent with web search tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load researcher-specific configuration
    config = settings.load_agent_config("agents/researcher_agent")
    agent_config = config.get("agent", {})

    # Import and configure tools based on agent configuration
    from .tools.web_search_tools import web_search_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "web_search_tool" and tool_config.get("enabled", True):
            enabled_tools.append(web_search_tool)

    # Create the agent with configured tools
    agent = client.create_agent(
        name=agent_config.get("name", "researcher"),
        instructions=config.get("system_prompt", ""),
        tools=enabled_tools,
        memory=context_provider,
    )

    return agent
