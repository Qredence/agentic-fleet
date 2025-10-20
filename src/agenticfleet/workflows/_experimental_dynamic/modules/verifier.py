"""Verifier participant creation."""

from __future__ import annotations

from agent_framework import AgentProtocol

from agenticfleet.core.logging import get_logger

from ..prompts import VERIFIER_PROMPT
from ..settings import make_responses_client

logger = get_logger(__name__)


def create_verifier_participant(
    *,
    name: str = "verifier",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the verifier participant."""
    prompt = instructions or VERIFIER_PROMPT
    client = make_responses_client(model=model)
    logger.debug("Creating verifier participant with model=%s", model or "default")
    return client.create_agent(name=name, instructions=prompt)


__all__ = ["create_verifier_participant"]
