"""Base generator tool participant."""

from __future__ import annotations

from agent_framework import AgentProtocol

from agenticfleet.core.logging import get_logger

from ..prompts import BASE_GENERATOR_PROMPT
from ..settings import make_responses_client

logger = get_logger(__name__)


def create_base_generator_participant(
    *,
    name: str = "base_generator",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the baseline generator participant."""
    prompt = instructions or BASE_GENERATOR_PROMPT
    client = make_responses_client(model=model)
    logger.debug("Creating base_generator participant with model=%s", model or "default")
    return client.create_agent(name=name, instructions=prompt)


__all__ = ["create_base_generator_participant"]
