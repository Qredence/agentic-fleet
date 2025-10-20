"""Shared agent primitives for AgenticFleet-specific extensions."""

from __future__ import annotations

from typing import Any

from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.core.exceptions import AgentConfigurationError


class ChatAgent:  # type: ignore[no-redef,override]
    """Fallback ChatAgent that raises when instantiated without the dependency."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise AgentConfigurationError(
            "agent_framework is required to instantiate fleet agents. "
            "Install the 'agent-framework' package to enable this functionality."
        )


class FleetAgent(OpenAIResponsesClient):
    """ChatAgent variant that exposes runtime configuration metadata."""

    runtime_config: dict[str, Any]

    def __init__(
        self,
        *args: Any,
        runtime_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.runtime_config = runtime_config or {}


__all__ = ["FleetAgent"]
