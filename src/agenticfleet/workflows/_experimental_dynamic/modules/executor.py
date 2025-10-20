"""Executor participant creation."""

from __future__ import annotations

from agent_framework import AgentProtocol

from agenticfleet.core.logging import get_logger

from ..prompts import EXECUTOR_PROMPT
from ..settings import make_responses_client

logger = get_logger(__name__)


def create_executor_participant(
    *,
    name: str = "executor",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the executor participant."""
    prompt = instructions or EXECUTOR_PROMPT
    client = make_responses_client(model=model)
    logger.debug("Creating executor participant with model=%s", model or "default")
    return client.create_agent(name=name, instructions=prompt)


__all__ = ["create_executor_participant"]
