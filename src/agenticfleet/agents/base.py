"""Shared agent primitives for AgenticFleet-specific extensions."""

from __future__ import annotations

from typing import Any

from agent_framework import ChatAgent


class AgenticFleetChatAgent(ChatAgent):
    """ChatAgent variant that exposes runtime configuration explicitly."""

    runtime_config: dict[str, Any]

    def __init__(
        self,
        *args: Any,
        runtime_config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the agent and attach runtime metadata."""

        super().__init__(*args, **kwargs)
        self.runtime_config = runtime_config or {}


__all__ = ["AgenticFleetChatAgent"]
