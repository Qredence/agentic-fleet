"""Coder Agent Factory

Provides factory function to create the Coder agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The coder is responsible for writing, executing, and debugging code.

Key Features:
- Safe code execution in restricted environment
- Support for Python (Phase 1), extensible to other languages
- Comprehensive error handling and output capture
- Follows PEP 8 and best coding practices

Usage:
    from agenticfleet.agents.coder import create_coder_agent

    coder = create_coder_agent()
    result = await coder.run("Write a function to calculate fibonacci numbers")
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.config import settings


def create_coder_agent() -> ChatAgent:
    """
    Create the Coder agent with code interpretation capabilities.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Tools are plain Python functions passed as a list.

    Returns:
        ChatAgent: Configured coder agent with code interpreter tools

    Raises:
        AgentConfigurationError: If required configuration is missing
    """
    # Load coder-specific configuration
    config = settings.load_agent_config("coder")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Import tool - use the original tool which will be wrapped at runtime
    from agenticfleet.agents.coder.tools.code_interpreter import code_interpreter_tool

    # Check which tools are enabled in the configuration
    tools_config = config.get("tools", [])
    enabled_tools = []

    for tool_config in tools_config:
        if tool_config.get("name") == "code_interpreter_tool" and tool_config.get("enabled", True):
            enabled_tools.append(code_interpreter_tool)

    # Create and return agent with tools
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    return ChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "coder"),
        tools=enabled_tools,
    )
