"""Agent classes for agent_framework."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

__all__ = ["patch_agent_classes"]


def patch_agent_classes(root: Any) -> None:
    """Patch ChatAgent and related agent builder classes."""
    if not hasattr(root, "ChatAgent"):

        class ChatAgent:  # pragma: no cover - shim
            def __init__(
                self,
                name: str,
                description: str = "",
                instructions: str = "",
                chat_client: Any | None = None,
                tools: Any = None,
            ) -> None:
                self.name = name
                self.description = description or name
                self.instructions = instructions
                tool_list = (
                    tools
                    if isinstance(tools, list | tuple)
                    else [tools]
                    if tools is not None
                    else []
                )
                self.chat_client = chat_client
                self.chat_options = SimpleNamespace(tools=tool_list, instructions=instructions)

            async def run(self, task: str) -> Any:  # AgentRunResponse
                role_cls = getattr(root, "Role", None)
                role_value = (
                    getattr(role_cls, "ASSISTANT", "assistant") if role_cls else "assistant"
                )
                message = root.ChatMessage(role=role_value, text=f"{self.name}:{task}")  # type: ignore[attr-defined]
                return root.AgentRunResponse(messages=[message])  # type: ignore[attr-defined]

            async def run_stream(self, task: str):  # pragma: no cover - shim
                role_cls = getattr(root, "Role", None)
                role_value = (
                    getattr(role_cls, "ASSISTANT", "assistant") if role_cls else "assistant"
                )
                yield root.MagenticAgentMessageEvent(
                    agent_id=self.name,
                    message=root.ChatMessage(role=role_value, text=f"{self.name}:{task}"),  # type: ignore[attr-defined]
                )

        root.ChatAgent = ChatAgent  # type: ignore[attr-defined]

    if not hasattr(root, "GroupChatBuilder"):

        class GroupChatBuilder:  # pragma: no cover - shim
            def __init__(self) -> None:
                self.agents: list[Any] = []

            def add_agent(self, agent: Any) -> GroupChatBuilder:
                self.agents.append(agent)
                return self

            def build(self) -> Any:
                return root.ChatAgent(name="GroupChat", description="Group Chat Shim")  # type: ignore[attr-defined]

        root.GroupChatBuilder = GroupChatBuilder  # type: ignore[attr-defined]
