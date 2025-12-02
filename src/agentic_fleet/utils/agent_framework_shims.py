"""Runtime shims for optional ``agent_framework`` dependency.

These helpers ensure core ``agent_framework`` modules exist in ``sys.modules``
when the real package is not installed (e.g., in tests or lightweight
workspaces). Only the subset of the API referenced inside AgenticFleet is
implemented, providing just enough surface area for imports to succeed.
"""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

__all__ = ["ensure_agent_framework_shims"]


def _import_or_stub(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module

    try:  # pragma: no cover - best effort import
        module = importlib.import_module(name)
        return module
    except Exception:
        module = types.ModuleType(name)
        module.__dict__.setdefault("__path__", [])
        sys.modules[name] = module
        return module


def _ensure_submodule(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module

    try:  # pragma: no cover - passthrough when dependency is installed
        module = importlib.import_module(name)
    except Exception:  # pragma: no cover - fallback shim path
        module = types.ModuleType(name)
        module.__dict__.setdefault("__path__", [])

    sys.modules[name] = module
    return module


def _maybe_define(module: types.ModuleType, attr: str, factory: Any) -> None:
    if not hasattr(module, attr):
        setattr(module, attr, factory)


def ensure_agent_framework_shims() -> None:
    """Ensure ``agent_framework`` symbols exist even when dependency is absent."""

    root = cast(Any, _import_or_stub("agent_framework"))

    exceptions = cast(Any, _ensure_submodule("agent_framework.exceptions"))
    root.exceptions = exceptions  # type: ignore[attr-defined]

    if not hasattr(exceptions, "AgentFrameworkException"):

        class AgentFrameworkException(Exception):  # noqa: N818
            """Compatibility shim for agent-framework base exception."""

        exceptions.AgentFrameworkException = AgentFrameworkException

    base_exception = cast(type[Exception], exceptions.AgentFrameworkException)

    if not hasattr(exceptions, "ToolException"):
        exceptions.ToolException = type(
            "ToolException",
            (base_exception,),
            {"__doc__": "Fallback tool exception shim."},
        )

    if not hasattr(exceptions, "ToolExecutionException"):
        exceptions.ToolExecutionException = type(
            "ToolExecutionException",
            (base_exception,),
            {"__doc__": "Fallback tool execution exception shim."},
        )

    # -- Core agent-framework symbols (used heavily across the codebase) --

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

    if not hasattr(root, "ToolProtocol"):

        class ToolProtocol:  # pragma: no cover - shim
            name: str | None = None
            description: str | None = None

            async def run(self, *args: Any, **kwargs: Any) -> Any:
                raise NotImplementedError

        root.ToolProtocol = ToolProtocol  # type: ignore[attr-defined]

    if not hasattr(root, "HostedCodeInterpreterTool"):

        class HostedCodeInterpreterTool(root.ToolProtocol):  # type: ignore[name-defined]
            async def run(self, code: str, **kwargs: Any) -> dict[str, Any]:
                return {"result": f"Executed: {code}", "kwargs": kwargs}

        root.HostedCodeInterpreterTool = HostedCodeInterpreterTool  # type: ignore[attr-defined]

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

            async def run(self, task: str) -> AgentRunResponse:  # type: ignore[name-defined]
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

    # -- OpenAI submodule stub (needed for agent factory) --
    openai_module = _ensure_submodule("agent_framework.openai")

    if not hasattr(openai_module, "OpenAIChatClient"):

        class OpenAIChatClient:  # pragma: no cover - shim
            def __init__(
                self, model_id: str | None = None, async_client: Any | None = None, **kwargs: Any
            ) -> None:
                self.model_id = model_id
                self.async_client = async_client
                self.extra_body = kwargs.get("extra_body", {})

            async def complete(self, prompt: str) -> str:
                return f"{self.model_id or 'model'}:{prompt}"

        openai_module.OpenAIChatClient = OpenAIChatClient  # type: ignore[attr-defined]

    # Add OpenAIResponsesClient shim (preferred over ChatClient for Responses API)
    if not hasattr(openai_module, "OpenAIResponsesClient"):

        class OpenAIResponsesClient:  # pragma: no cover - shim
            """Shim for OpenAI Responses API client.

            This is the preferred client for agent-framework as it uses the
            OpenAI Responses API format instead of Chat Completions.
            """

            def __init__(
                self,
                model_id: str | None = None,
                async_client: Any | None = None,
                api_key: str | None = None,
                base_url: str | None = None,
                reasoning_effort: str = "medium",
                reasoning_verbosity: str = "normal",
                store: bool = True,
                temperature: float = 0.7,
                max_tokens: int = 4096,
                **kwargs: Any,
            ) -> None:
                self.model_id = model_id
                self.async_client = async_client
                self.api_key = api_key
                self.base_url = base_url
                self.reasoning_effort = reasoning_effort
                self.reasoning_verbosity = reasoning_verbosity
                self.store = store
                self.temperature = temperature
                self.max_tokens = max_tokens
                self.extra_body = kwargs.get("extra_body", {})

            async def complete(self, prompt: str) -> str:
                return f"{self.model_id or 'model'}:{prompt}"

            async def get_response(self, messages: list[Any]) -> Any:  # noqa: ARG002
                """Responses API style interface."""
                return SimpleNamespace(messages=[SimpleNamespace(text=f"{self.model_id}:response")])

        openai_module.OpenAIResponsesClient = OpenAIResponsesClient  # type: ignore[attr-defined]
