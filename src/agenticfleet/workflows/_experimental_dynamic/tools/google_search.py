"""Google search tool participant."""

from __future__ import annotations

from agent_framework import AgentProtocol, HostedWebSearchTool

from agenticfleet.core.logging import get_logger

from ..prompts import GOOGLE_SEARCH_PROMPT
from ..settings import make_responses_client, tool_model_name

logger = get_logger(__name__)


def create_google_search_participant(
    *,
    name: str = "google_search",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the Google search participant."""
    if HostedWebSearchTool is None:  # pragma: no cover - dependency optional
        raise RuntimeError("HostedWebSearchTool is not available in this environment.")

    prompt = instructions or GOOGLE_SEARCH_PROMPT
    effective_model = model or tool_model_name()
    client = make_responses_client(model=effective_model)
    logger.debug("Creating google_search participant with model=%s", model or "default")
    return client.create_agent(
        name=name,
        instructions=prompt,
        tools=[HostedWebSearchTool(description="General purpose web search")],
    )


__all__ = ["create_google_search_participant"]
