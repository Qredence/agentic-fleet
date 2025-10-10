"""Orchestrator Agent Factory

Provides factory function to create the Orchestrator agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The orchestrator is responsible for analyzing user requests, delegating tasks
to specialized agents (researcher, coder, analyst), and synthesizing results.
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from config.settings import settings


def create_orchestrator_agent() -> ChatAgent:
    """
    Create the Orchestrator agent.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIChatClient. Loads configuration from agent_config.yaml.

    Returns:
        ChatAgent: Configured orchestrator agent

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("agents/orchestrator_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIChatClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Create and return agent (orchestrator typically has no tools)
    return ChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "orchestrator"),
        temperature=agent_config.get("temperature", 0.1),
    )
