"""Shared agent primitives for AgenticFleet-specific extensions."""

from __future__ import annotations

from typing import Any

try:
    from agent_framework import ChatAgent as _ChatAgent
except ImportError:
    _ChatAgent = None  # type: ignore[assignment, misc]

from agenticfleet.core.exceptions import AgentConfigurationError


class ChatAgent:
    """Fallback ChatAgent that raises when instantiated without the dependency."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise AgentConfigurationError(
            "agent_framework is required to instantiate fleet agents. "
            "Install the 'agent-framework' package to enable this functionality."
        )


class FleetAgent(_ChatAgent if _ChatAgent else ChatAgent):  # type: ignore[misc]
    """ChatAgent variant that exposes runtime configuration metadata.

    This class extends the base ChatAgent from agent_framework and adds
    support for runtime configuration metadata. It accepts any chat client
    that implements ChatClientProtocol, including OpenAIResponsesClient
    and LiteLLMClient.
    """

    runtime_config: dict[str, Any]

    def __init__(
        self,
        *args: Any,
        runtime_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if _ChatAgent is None:
            raise AgentConfigurationError(
                "agent_framework is required to instantiate fleet agents. "
                "Install the 'agent-framework' package to enable this functionality."
            )
        super().__init__(*args, **kwargs)
        self.runtime_config = runtime_config or {}


__all__ = ["FleetAgent"]
