"""Python coder tool participant."""

from __future__ import annotations

from agent_framework import AgentProtocol, HostedCodeInterpreterTool

from agenticfleet.core.logging import get_logger

from ..prompts import PYTHON_CODER_PROMPT
from ..settings import make_responses_client, tool_model_name

logger = get_logger(__name__)


def create_python_coder_participant(
    *,
    name: str = "python_coder",
    instructions: str | None = None,
    model: str | None = None,
) -> AgentProtocol:
    """Create the Python coder participant."""
    if HostedCodeInterpreterTool is None:  # pragma: no cover - dependency optional
        raise RuntimeError("HostedCodeInterpreterTool is not available in this environment.")

    prompt = instructions or PYTHON_CODER_PROMPT
    effective_model = model or tool_model_name()
    client = make_responses_client(model=effective_model)
    logger.debug("Creating python_coder participant with model=%s", model or "default")
    return client.create_agent(
        name=name,
        instructions=prompt,
        tools=[HostedCodeInterpreterTool(description="Execute Python code snippets")],
    )


__all__ = ["create_python_coder_participant"]
