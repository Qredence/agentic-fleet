"""LiteLLM Client for AgenticFleet

This module provides a LiteLLM-based chat client that implements the ChatClientProtocol
from Microsoft Agent Framework. LiteLLM provides a unified interface to multiple LLM
providers (OpenAI, Anthropic, Azure, etc.) with built-in caching and tracing capabilities.

Usage:
    from agenticfleet.core.litellm_client import LiteLLMClient

    client = LiteLLMClient(model="gpt-4o-mini")
    # or use with custom provider
    client = LiteLLMClient(model="anthropic/claude-3-5-sonnet-20241022")
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Mapping
from typing import Any

try:
    import litellm
    from litellm import ModelResponse
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
except ImportError:
    litellm = None  # type: ignore[assignment]
    ModelResponse = None  # type: ignore[assignment, misc]
    CustomStreamWrapper = None  # type: ignore[assignment, misc]

from agent_framework._clients import ChatClientProtocol
from agent_framework._types import (
    ChatMessage,
    FunctionCallContent,
    FunctionResultContent,
    TextContent,
)

logger = logging.getLogger(__name__)


class LiteLLMClient(ChatClientProtocol):
    """
    LiteLLM-based chat client implementing ChatClientProtocol.

    This client provides a unified interface to multiple LLM providers through LiteLLM,
    supporting features like caching, tracing, and provider-agnostic model switching.

    Args:
        model: Model identifier (e.g., "gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022")
        api_key: Optional API key (can be set via environment variables)
        base_url: Optional base URL for custom endpoints
        temperature: Default temperature for completions
        max_tokens: Default max tokens for completions
        timeout: Request timeout in seconds
        **kwargs: Additional parameters passed to litellm.acompletion
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        if litellm is None:
            raise ImportError(
                "litellm is required to use LiteLLMClient. " "Install it with: pip install litellm"
            )

        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._extra_kwargs = kwargs

        logger.info(f"Initialized LiteLLMClient with model: {model}")

    @property
    def additional_properties(self) -> Mapping[str, Any]:
        """Return additional properties for this client."""
        return {
            "model": self._model,
            "base_url": self._base_url,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "timeout": self._timeout,
        }

    async def get_response(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs: Any,
    ) -> ChatMessage:
        """
        Get a non-streaming response from the LLM.

        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            top_p: Optional top_p parameter
            frequency_penalty: Optional frequency penalty
            presence_penalty: Optional presence penalty
            stop: Optional stop sequences
            **kwargs: Additional parameters

        Returns:
            ChatMessage with the LLM response
        """
        # Convert ChatMessage to LiteLLM format
        litellm_messages = self._convert_messages_to_litellm(messages)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self._model,
            "messages": litellm_messages,
            "stream": False,
        }

        # Add optional parameters
        if self._api_key:
            request_params["api_key"] = self._api_key
        if self._base_url:
            request_params["base_url"] = self._base_url
        if temperature is not None:
            request_params["temperature"] = temperature
        elif self._temperature is not None:
            request_params["temperature"] = self._temperature
        if max_tokens is not None:
            request_params["max_tokens"] = max_tokens
        elif self._max_tokens is not None:
            request_params["max_tokens"] = self._max_tokens
        if self._timeout is not None:
            request_params["timeout"] = self._timeout
        if top_p is not None:
            request_params["top_p"] = top_p
        if frequency_penalty is not None:
            request_params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            request_params["presence_penalty"] = presence_penalty
        if stop is not None:
            request_params["stop"] = stop
        if tools:
            request_params["tools"] = tools

        # Merge extra kwargs
        request_params.update(self._extra_kwargs)
        request_params.update(kwargs)

        # Make async request
        response = await litellm.acompletion(**request_params)

        # Convert response to ChatMessage
        return self._convert_response_to_message(response)

    async def get_streaming_response(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[ChatMessage, None]:
        """
        Get a streaming response from the LLM.

        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            top_p: Optional top_p parameter
            frequency_penalty: Optional frequency penalty
            presence_penalty: Optional presence penalty
            stop: Optional stop sequences
            **kwargs: Additional parameters

        Yields:
            ChatMessage deltas as they arrive
        """
        # Convert ChatMessage to LiteLLM format
        litellm_messages = self._convert_messages_to_litellm(messages)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self._model,
            "messages": litellm_messages,
            "stream": True,
        }

        # Add optional parameters (same as get_response)
        if self._api_key:
            request_params["api_key"] = self._api_key
        if self._base_url:
            request_params["base_url"] = self._base_url
        if temperature is not None:
            request_params["temperature"] = temperature
        elif self._temperature is not None:
            request_params["temperature"] = self._temperature
        if max_tokens is not None:
            request_params["max_tokens"] = max_tokens
        elif self._max_tokens is not None:
            request_params["max_tokens"] = self._max_tokens
        if self._timeout is not None:
            request_params["timeout"] = self._timeout
        if top_p is not None:
            request_params["top_p"] = top_p
        if frequency_penalty is not None:
            request_params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            request_params["presence_penalty"] = presence_penalty
        if stop is not None:
            request_params["stop"] = stop
        if tools:
            request_params["tools"] = tools

        # Merge extra kwargs
        request_params.update(self._extra_kwargs)
        request_params.update(kwargs)

        # Make async streaming request
        response = await litellm.acompletion(**request_params)

        # Stream chunks
        async for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                delta = choice.delta if hasattr(choice, "delta") else None

                if delta:
                    # Convert delta to ChatMessage
                    contents: list[TextContent | FunctionCallContent] = []

                    # Add text content if present
                    if hasattr(delta, "content") and delta.content:
                        contents.append(TextContent(text=delta.content))

                    # Add tool calls if present
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if hasattr(tool_call, "function"):
                                contents.append(
                                    FunctionCallContent(
                                        call_id=tool_call.id if hasattr(tool_call, "id") else "",
                                        name=(
                                            tool_call.function.name
                                            if hasattr(tool_call.function, "name")
                                            else ""
                                        ),
                                        arguments=(
                                            tool_call.function.arguments
                                            if hasattr(tool_call.function, "arguments")
                                            else ""
                                        ),
                                    )
                                )

                    # Create message
                    message = ChatMessage(role="assistant", contents=contents if contents else None)

                    yield message

    def _convert_messages_to_litellm(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert Agent Framework ChatMessages to LiteLLM format."""
        litellm_messages: list[dict[str, Any]] = []

        for msg in messages:
            litellm_msg: dict[str, Any] = {"role": str(msg.role)}

            # Handle text content
            if msg.text:
                litellm_msg["content"] = msg.text
            elif msg.contents:
                # Convert contents to string or structured format
                content_parts = []
                tool_calls = []

                for content in msg.contents:
                    if isinstance(content, TextContent) and content.text:
                        content_parts.append(content.text)
                    elif isinstance(content, FunctionCallContent):
                        tool_calls.append(
                            {
                                "id": content.call_id,
                                "type": "function",
                                "function": {
                                    "name": content.name,
                                    "arguments": content.arguments,
                                },
                            }
                        )
                    elif isinstance(content, FunctionResultContent):
                        # Handle function results
                        litellm_msg["tool_call_id"] = content.call_id
                        if hasattr(content, "result"):
                            content_parts.append(str(content.result))

                if content_parts:
                    litellm_msg["content"] = " ".join(content_parts)
                elif not tool_calls:
                    litellm_msg["content"] = ""

                if tool_calls:
                    litellm_msg["tool_calls"] = tool_calls

            else:
                litellm_msg["content"] = ""

            litellm_messages.append(litellm_msg)

        return litellm_messages

    def _convert_response_to_message(self, response: Any) -> ChatMessage:
        """Convert LiteLLM response to Agent Framework ChatMessage."""
        if not hasattr(response, "choices") or len(response.choices) == 0:
            return ChatMessage(role="assistant", contents=[])

        choice = response.choices[0]
        message = choice.message

        # Extract content
        contents: list[TextContent | FunctionCallContent] = []

        if hasattr(message, "content") and message.content:
            contents.append(TextContent(text=message.content))

        # Extract tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                if hasattr(tool_call, "function"):
                    contents.append(
                        FunctionCallContent(
                            call_id=tool_call.id if hasattr(tool_call, "id") else "",
                            name=(
                                tool_call.function.name
                                if hasattr(tool_call.function, "name")
                                else ""
                            ),
                            arguments=(
                                tool_call.function.arguments
                                if hasattr(tool_call.function, "arguments")
                                else ""
                            ),
                        )
                    )

        return ChatMessage(role="assistant", contents=contents if contents else None)


__all__ = ["LiteLLMClient"]
