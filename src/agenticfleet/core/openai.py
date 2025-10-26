"""Helpers for working with OpenAI and LiteLLM clients used across AgenticFleet."""

from __future__ import annotations

import inspect
from typing import Any

try:
    from agent_framework.openai import OpenAIResponsesClient
except ImportError:
    OpenAIResponsesClient = None  # type: ignore[assignment, misc]


def get_responses_model_parameter(client_cls: type[object]) -> str:
    """Return the parameter name used for the responses model on the client."""

    try:
        signature = inspect.signature(client_cls.__init__)
    except (TypeError, ValueError):
        return "model"

    parameters = signature.parameters

    if "model_id" in parameters:
        return "model_id"

    if "model" in parameters:
        return "model"

    for parameter in parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            return "model"

    return "model"


def create_chat_client(
    model: str,
    *,
    use_litellm: bool = False,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Any:
    """
    Create a chat client for use with Agent Framework.

    This factory function creates either an OpenAIResponsesClient or LiteLLMClient
    based on configuration. When use_litellm is True, it provides access to multiple
    LLM providers through a unified interface.

    Args:
        model: Model identifier (e.g., "gpt-4o-mini" for OpenAI,
               "anthropic/claude-3-5-sonnet-20241022" for LiteLLM)
        use_litellm: If True, use LiteLLM client for universal provider support
        api_key: Optional API key
        base_url: Optional base URL for custom endpoints
        temperature: Optional default temperature
        max_tokens: Optional default max tokens
        timeout: Optional timeout in seconds
        **kwargs: Additional parameters passed to the client

    Returns:
        Chat client instance implementing ChatClientProtocol

    Raises:
        ImportError: If required client library is not installed
    """
    if use_litellm:
        from agenticfleet.core.litellm_client import LiteLLMClient

        return LiteLLMClient(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
    else:
        if OpenAIResponsesClient is None:
            raise ImportError(
                "agent_framework is required. " "Install it with: pip install agent-framework"
            )

        # Build kwargs for OpenAIResponsesClient
        client_kwargs: dict[str, Any] = {}

        # Use model_id parameter for OpenAIResponsesClient
        param_name = get_responses_model_parameter(OpenAIResponsesClient)
        client_kwargs[param_name] = model

        if api_key is not None:
            client_kwargs["api_key"] = api_key
        if base_url is not None:
            client_kwargs["base_url"] = base_url

        # Note: OpenAIResponsesClient doesn't take temperature/max_tokens at init
        # Those are passed to ChatAgent or in request params
        client_kwargs.update(kwargs)

        return OpenAIResponsesClient(**client_kwargs)


__all__ = ["create_chat_client", "get_responses_model_parameter"]
