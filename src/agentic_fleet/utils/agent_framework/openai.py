"""OpenAI client shims for agent_framework."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .utils import _ensure_submodule

__all__ = ["patch_openai_module"]


def patch_openai_module() -> None:
    """Patch OpenAI client classes."""
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
