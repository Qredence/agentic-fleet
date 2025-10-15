"""Coder Agent Factory

Provides factory function to create the Coder agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The coder is responsible for drafting and reviewing code, producing
annotated snippets and manual run guidance. Automated execution tooling
is temporarily unavailable.

Usage:
    from agenticfleet.agents.coder import create_coder_agent

    coder = create_coder_agent()
    result = await coder.run("Write a function to calculate fibonacci numbers")
"""

from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.agents.base import AgenticFleetChatAgent
from agenticfleet.config import settings


def create_coder_agent() -> AgenticFleetChatAgent:
    """Create the Coder agent responsible for code drafting and review."""

    # Load coder-specific configuration
    config = settings.load_agent_config("coder")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # No tools currently enabled for coder agent (execution disabled)
    enabled_tools: list = []

    # Create and return agent with instructions only
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    agent = AgenticFleetChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "coder"),
        tools=enabled_tools,
        runtime_config=config.get("runtime", {}),
    )

    return agent
