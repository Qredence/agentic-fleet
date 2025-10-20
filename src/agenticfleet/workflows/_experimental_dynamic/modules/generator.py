"""Generator participant creation."""

from __future__ import annotations

from agent_framework import AgentProtocol

from agenticfleet.core.logging import get_logger

from ..prompts import GENERATOR_PROMPT
from ..settings import make_responses_client

logger = get_logger(__name__)


def create_generator_participant(
    *,
    name: str = "generator",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the generator participant."""
    prompt = instructions or GENERATOR_PROMPT
    client = make_responses_client(model=model)
    logger.debug("Creating generator participant with model=%s", model or "default")
    return client.create_agent(name=name, instructions=prompt)


__all__ = ["create_generator_participant"]
