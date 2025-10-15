"""Orchestrator Agent Factory

Provides factory function to create the Orchestrator agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The orchestrator is responsible for analyzing user requests, delegating tasks
to specialized agents (researcher, coder, analyst), and synthesizing results.
"""

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.config import settings


def create_orchestrator_agent() -> ChatAgent:
    """
    Create the Orchestrator agent.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Loads configuration from config.yaml.

    Returns:
        ChatAgent: Configured orchestrator agent

    Raises:
        AgentConfigurationError: If required configuration is missing
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("orchestrator")
    agent_config = config.get("agent", {})

    # Create OpenAI chat client
    chat_client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    # Create and return agent (orchestrator typically has no tools)
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    # It's model-specific and some models (like o1) don't support it
    agent = ChatAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "orchestrator"),
    )

    runtime_config = config.get("runtime", {})
    setattr(agent, "runtime_config", runtime_config)

    return agent
