"""Orchestrator Agent Factory

Provides factory function to create the Orchestrator agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The orchestrator is responsible for analyzing user requests, delegating tasks
to specialized agents (researcher, coder, analyst), and synthesizing results.
"""

from typing import Any

try:
    from agent_framework.openai import OpenAIResponsesClient
except ImportError:
    OpenAIResponsesClient = None  # type: ignore[assignment, misc]

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import get_responses_model_parameter


def create_orchestrator_agent() -> FleetAgent:
    """
    Create the Orchestrator agent.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient. Loads configuration from config.yaml.

    Returns:
    FleetAgent: Configured orchestrator agent
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("orchestrator")
    agent_config = config.get("agent", {})

    if OpenAIResponsesClient is None:
        raise AgentConfigurationError(
            "agent_framework is required to create the orchestrator agent. "
            "Install the 'agent-framework' package to enable this agent."
        )

    # Create OpenAI chat client
    chat_client_kwargs = {
        get_responses_model_parameter(OpenAIResponsesClient): agent_config.get(
            "model", settings.openai_model
        )
    }
    chat_client = OpenAIResponsesClient(**chat_client_kwargs)

    # Create and return agent (orchestrator typically has no tools)
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    # It's model-specific and some models (like o1) don't support it
    context_providers = settings.create_context_providers(
        agent_id=agent_config.get("name"),
    )
    fleet_agent_kwargs: dict[str, Any] = {}
    if context_providers:
        fleet_agent_kwargs["context_providers"] = context_providers

    agent = FleetAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "orchestrator"),
        runtime_config=config.get("runtime", {}),
        **fleet_agent_kwargs,
    )
    return agent
