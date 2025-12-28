"""Core type classes for agent_framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["patch_core_types"]


def patch_core_types(root: Any) -> None:
    """Patch core agent-framework type classes."""
    if not hasattr(root, "Role"):

        class Role:  # pragma: no cover - shim
            ASSISTANT = "assistant"
            USER = "user"
            SYSTEM = "system"

        root.Role = Role  # type: ignore[attr-defined]

    if not hasattr(root, "ChatMessage"):

        class ChatMessage:  # pragma: no cover - shim
            def __init__(
                self, role: str | None = None, text: str = "", content: str | None = None, **_: Any
            ):
                self.role = role
                self.text = text or (content or "")
                self.content = content or self.text
                self.additional_properties: dict[str, Any] = {}

            def __repr__(self) -> str:  # pragma: no cover - debugging helper
                return f"ChatMessage(role={self.role!r}, text={self.text!r})"

        root.ChatMessage = ChatMessage  # type: ignore[attr-defined]

    if not hasattr(root, "AgentRunResponse"):

        class AgentRunResponse:  # pragma: no cover - shim
            def __init__(
                self,
                messages: list[Any] | None = None,
                additional_properties: dict[str, Any] | None = None,
            ):
                self.messages = messages or []
                self.additional_properties = additional_properties or {}

            def get_outputs(self) -> list[Any]:
                return [getattr(msg, "text", msg) for msg in self.messages]

        root.AgentRunResponse = AgentRunResponse  # type: ignore[attr-defined]

    if not hasattr(root, "WorkflowOutputEvent"):

        @dataclass
        class WorkflowOutputEvent:  # pragma: no cover - shim
            data: Any | None = None
            source_executor_id: str = ""
            event_type: str = "workflow_output"

        root.WorkflowOutputEvent = WorkflowOutputEvent  # type: ignore[attr-defined]

    if not hasattr(root, "MagenticAgentMessageEvent"):

        @dataclass
        class MagenticAgentMessageEvent:  # pragma: no cover - shim
            agent_id: str | None = None
            message: Any | None = None

        root.MagenticAgentMessageEvent = MagenticAgentMessageEvent  # type: ignore[attr-defined]

    if not hasattr(root, "MagenticBuilder"):

        class MagenticBuilder:  # pragma: no cover - shim
            pass

        root.MagenticBuilder = MagenticBuilder  # type: ignore[attr-defined]
