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

from typing import Any

from agenticfleet.agents.base import FleetAgent
from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.openai import create_chat_client


def create_coder_agent() -> FleetAgent:
    """Create the Coder agent responsible for code drafting and review."""

    # Load coder-specific configuration
    config = settings.load_agent_config("coder")
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

    # No tools currently enabled for coder agent (execution disabled)
    enabled_tools: list[Any] = []

    # Create and return agent with instructions only
    # Note: temperature is not a ChatAgent parameter in Microsoft Agent Framework
    context_providers = settings.create_context_providers(
        agent_id=agent_config.get("name"),
    )
    fleet_agent_kwargs: dict[str, Any] = {}
    if context_providers:
        fleet_agent_kwargs["context_providers"] = context_providers

    agent = FleetAgent(
        chat_client=chat_client,
        instructions=config.get("system_prompt", ""),
        name=agent_config.get("name", "coder"),
        tools=enabled_tools,
        runtime_config=config.get("runtime", {}),
        **fleet_agent_kwargs,
    )
    return agent
