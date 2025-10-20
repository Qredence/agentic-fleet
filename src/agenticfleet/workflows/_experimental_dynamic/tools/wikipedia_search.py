"""Wikipedia search tool participant."""

from __future__ import annotations

from agent_framework import AgentProtocol, HostedWebSearchTool

from agenticfleet.core.logging import get_logger

from ..prompts import WIKIPEDIA_SEARCH_PROMPT
from ..settings import make_responses_client, tool_model_name

logger = get_logger(__name__)


def create_wikipedia_search_participant(
    *,
    name: str = "wikipedia_search",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the Wikipedia search participant."""
    if HostedWebSearchTool is None:  # pragma: no cover - dependency optional
        raise RuntimeError("HostedWebSearchTool is not available in this environment.")

    prompt = instructions or WIKIPEDIA_SEARCH_PROMPT
    effective_model = model or tool_model_name()
    client = make_responses_client(model=effective_model)
    logger.debug("Creating wikipedia_search participant with model=%s", model or "default")
    return client.create_agent(
        name=name,
        instructions=prompt,
        tools=[
            HostedWebSearchTool(
                description="Search the public web with a focus on Wikipedia",
            )
        ],
    )


__all__ = ["create_wikipedia_search_participant"]
