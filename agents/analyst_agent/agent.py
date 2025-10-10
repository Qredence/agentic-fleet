"""
Analyst Agent Factory

This module provides the factory function to create and configure the Analyst agent.
The agent is responsible for data analysis, insight generation, and visualization
recommendations.

The factory:
1. Loads agent-specific configuration from agent_config.yaml
2. Creates an OpenAI chat client optimized for analytical reasoning
3. Imports and configures data analysis and visualization tools
4. Instantiates a ChatAgent with analytical capabilities

Key Features:
- Multiple analysis types: summary, trends, patterns, comparison, correlation
- Structured insights with confidence levels and supporting evidence
- Visualization recommendations based on data type and analysis goals
- Colorblind-friendly and accessible design suggestions

Usage:
    from agents.analyst_agent.agent import create_analyst_agent

    analyst = create_analyst_agent()
    result = await analyst.run("Analyze sales trends and suggest visualizations")
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from config.settings import settings


def create_analyst_agent() -> ChatAgent:
    """
    Create the Analyst agent with data analysis capabilities.

    This function:
    - Loads configuration from agents/analyst_agent/agent_config.yaml
    - Creates an OpenAI Responses client with analyst-specific settings
    - Enables both data_analysis_tool and visualization_suggestion_tool
    - Returns a fully configured ChatAgent instance

    The agent uses a lower temperature (0.2) to ensure consistent,
    logical analytical reasoning with minimal creativity.

    Returns:
        ChatAgent: Configured analyst agent with analysis and visualization tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("agents/analyst_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI Responses client with analyst-specific parameters
    # API key is read from OPENAI_API_KEY environment variable
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Import and configure analysis tools
    from .tools.data_analysis_tools import (
        data_analysis_tool,
        visualization_suggestion_tool,
    )

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    # Enable tools based on configuration
    # Both data_analysis_tool and visualization_suggestion_tool are typically enabled
    for tool_config in tools_config:
        tool_name = tool_config.get("name")
        if tool_config.get("enabled", True):
            if tool_name == "data_analysis_tool":
                enabled_tools.append(data_analysis_tool)
            elif tool_name == "visualization_suggestion_tool":
                enabled_tools.append(visualization_suggestion_tool)

    # Create the ChatAgent with analytical capabilities
    agent = ChatAgent(
        name=agent_config.get("name", "analyst"),
        instructions=config.get("system_prompt", ""),
        chat_client=client,
        tools=enabled_tools,  # Pass tools directly
    )

    return agent
