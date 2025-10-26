"""Orchestrator Agent Factory

Provides factory function to create the Orchestrator agent using official
Microsoft Agent Framework Python APIs (ChatAgent pattern).

The orchestrator is responsible for analyzing user requests, delegating tasks
to specialized agents (researcher, coder, analyst), and synthesizing results.
"""

from typing import Any

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import create_chat_client


def create_orchestrator_agent() -> FleetAgent:
    """
    Create the Orchestrator agent.

    Uses official Python Agent Framework pattern with ChatAgent and
    OpenAIResponsesClient or LiteLLMClient based on configuration.
    Loads configuration from config.yaml.

    Returns:
    FleetAgent: Configured orchestrator agent
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("orchestrator")
    agent_config = config.get("agent", {})

    # Get model from config or use default
    model = agent_config.get("model", settings.openai_model)

    # Determine which client to use based on settings
    use_litellm = settings.use_litellm
    if use_litellm and settings.litellm_model:
        # Use LiteLLM model if configured
        model = settings.litellm_model

    try:
        # Create chat client using factory
        chat_client = create_chat_client(
            model=model,
            use_litellm=use_litellm,
            api_key=settings.litellm_api_key if use_litellm else None,
            base_url=settings.litellm_base_url if use_litellm else None,
            timeout=settings.litellm_timeout if use_litellm else None,
        )
    except ImportError as e:
        raise AgentConfigurationError(
            f"Required client library not available: {e}. "
            "Install the appropriate package to enable this agent."
        ) from e

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
