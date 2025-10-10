"""
Coder Agent Factory

This module provides the factory function to create and configure the Coder agent.
The agent is responsible for writing, executing, and debugging code.

The factory:
1. Loads agent-specific configuration from agent_config.yaml
2. Creates an OpenAI chat client optimized for code generation
3. Imports and configures the code interpreter tool
4. Instantiates a ChatAgent with code execution capabilities

Key Features:
- Safe code execution in restricted environment
- Support for Python (Phase 1), extensible to other languages
- Comprehensive error handling and output capture
- Follows PEP 8 and best coding practices

Usage:
    from agents.coder_agent.agent import create_coder_agent

    coder = create_coder_agent()
    result = await coder.run("Write a function to calculate fibonacci numbers")
"""

from azure.ai.agent.client import AzureAIAgentClient

from config.settings import settings


def create_coder_agent(client: AzureAIAgentClient, context_provider):
    """
    Create the Coder agent with code interpretation capabilities.

    This function:
    - Loads configuration from agents/coder_agent/agent_config.yaml
    - Creates an agent with the provided AzureAIAgentClient
    - Enables the code_interpreter_tool if configured
    - Returns a fully configured agent instance

    Args:
        client: The AzureAIAgentClient instance.

    Returns:
        AIAgent: Configured coder agent with code interpreter tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load coder-specific configuration
    config = settings.load_agent_config("agents/coder_agent")
    agent_config = config.get("agent", {})

    # Import and configure tools based on agent configuration
    from .tools.code_interpreter import code_interpreter_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "code_interpreter_tool" and tool_config.get("enabled", True):
            enabled_tools.append(code_interpreter_tool)

    # Create the agent with configured tools
    agent = client.create_agent(
        name=agent_config.get("name", "coder"),
        instructions=config.get("system_prompt", ""),
        tools=enabled_tools,
        memory=context_provider,
    )

    return agent
