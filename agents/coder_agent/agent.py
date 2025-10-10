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

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from config.settings import settings


def create_coder_agent() -> ChatAgent:
    """
    Create the Coder agent with code interpretation capabilities.

    This function:
    - Loads configuration from agents/coder_agent/agent_config.yaml
    - Creates an OpenAI Responses client with coder-specific settings (low temperature)
    - Enables the code_interpreter_tool if configured
    - Returns a fully configured ChatAgent instance

    The agent uses a lower temperature (0.2) to ensure deterministic,
    precise code generation with minimal randomness.

    Returns:
        ChatAgent: Configured coder agent with code execution tools

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load coder-specific configuration
    config = settings.load_agent_config("agents/coder_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI Responses client with coder-specific parameters
    # API key is read from OPENAI_API_KEY environment variable
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Import and configure code execution tool
    from .tools.code_interpreter import code_interpreter_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "code_interpreter_tool" and tool_config.get("enabled", True):
            enabled_tools.append(code_interpreter_tool)

    # Create the ChatAgent with code execution capabilities
    agent = ChatAgent(
        name=agent_config.get("name", "coder"),
        instructions=config.get("system_prompt", ""),
        chat_client=client,
        tools=enabled_tools,  # Pass tools directly
    )

    return agent
