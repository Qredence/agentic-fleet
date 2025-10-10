from azure.ai.agent.client import AzureAIAgentClient

from config.settings import settings


def create_analyst_agent(client: AzureAIAgentClient, context_provider):
    """
    Create the Analyst agent with data analysis capabilities.

    This function:
    - Loads configuration from agents/analyst_agent/agent_config.yaml
    - Creates an agent with the provided AzureAIAgentClient
    - Enables the data_analysis_tool and visualization_suggestion_tool if configured
    - Returns a fully configured agent instance

    Args:
        client: The AzureAIAgentClient instance.

    Returns:
        AIAgent: Configured analyst agent with data analysis tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load analyst-specific configuration
    config = settings.load_agent_config("agents/analyst_agent")
    agent_config = config.get("agent", {})

    # Import and configure tools based on agent configuration
    from .tools.data_analysis_tools import data_analysis_tool, visualization_suggestion_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "data_analysis_tool" and tool_config.get("enabled", True):
            enabled_tools.append(data_analysis_tool)
        if tool_config.get("name") == "visualization_suggestion_tool" and tool_config.get("enabled", True):
            enabled_tools.append(visualization_suggestion_tool)

    # Create the agent with configured tools
    agent = client.create_agent(
        name=agent_config.get("name", "analyst"),
        instructions=config.get("system_prompt", ""),
        tools=enabled_tools,
        memory=context_provider,
    )

    return agent
