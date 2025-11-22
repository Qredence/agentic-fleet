"""Base agent classes for the fleet.

This module defines the base agent classes used throughout the system,
including the DSPy-enhanced agent that integrates with the Agent Framework.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Any

from agent_framework import (
    AgentRunResponse,
    AgentRunResponseUpdate,
    AgentThread,
    ChatAgent,
    ChatMessage,
    Role,
)

from ..dspy_modules.reasoning import FleetPoT, FleetReAct
from ..utils.cache import TTLCache
from ..utils.logger import setup_logger
from ..utils.telemetry import PerformanceTracker, optional_span

if TYPE_CHECKING:
    from agent_framework.openai import OpenAIResponsesClient

logger = setup_logger(__name__)


class DSPyEnhancedAgent(ChatAgent):
    """Agent that uses DSPy for enhanced reasoning capabilities.

    This agent wraps the standard ChatAgent and injects DSPy-powered
    reasoning strategies (Chain of Thought, ReAct, Program of Thought)
    to improve performance on complex tasks. It inherits from ChatAgent
    to have full control over the execution flow, while maintaining
    compatibility with the Agent Framework.
    """

    def __init__(
        self,
        name: str,
        chat_client: OpenAIResponsesClient,
        instructions: str = "",
        description: str = "",
        tools: Any = None,
        enable_dspy: bool = True,
        timeout: int = 30,
        cache_ttl: int = 300,
        reasoning_strategy: str = "chain_of_thought",
        **_kwargs: Any,
    ) -> None:
        """Initialize the DSPy-enhanced agent.

        Args:
            name: Agent name (e.g., "ResearcherAgent")
            chat_client: OpenAI client for LLM calls
            instructions: Agent instructions/system prompt
            description: Agent description
            tools: Tool instance or tuple of tools
            enable_dspy: Whether to enable DSPy task enhancement
            timeout: Maximum execution time per task in seconds
            cache_ttl: Cache time-to-live in seconds (0 to disable)
            reasoning_strategy: Strategy to use (chain_of_thought, react, program_of_thought)
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            chat_client=chat_client,
            tools=tools,
        )

        self.enable_dspy = enable_dspy
        self.timeout = timeout
        self.reasoning_strategy = reasoning_strategy
        self.cache = TTLCache(ttl_seconds=cache_ttl)
        self.tracker = PerformanceTracker()

        # Initialize reasoning modules using the agent's tools
        self.react_module = FleetReAct(tools=self.tools) if reasoning_strategy == "react" else None
        self.pot_module = FleetPoT() if reasoning_strategy == "program_of_thought" else None

    @property
    def tools(self) -> Any:
        """Expose tools from the internal chat agent."""
        return getattr(self, "_tools", [])

    def _get_agent_role_description(self) -> str:
        """Get agent role description for DSPy enhancement."""
        instructions = getattr(self.chat_options, "instructions", None)
        role_description = self.description or instructions or ""
        return role_description[:200]

    def _enhance_task_with_dspy(self, task: str, context: str = "") -> tuple[str, dict[str, Any]]:
        """Enhance task using DSPy for better agent understanding.

        Args:
            task: Original task string
            context: Optional conversation context

        Returns:
            Tuple of (enhanced_task, metadata)
        """
        if not self.enable_dspy or not self.task_enhancer:
            return task, {}

        try:
            with optional_span(
                "dspy_task_enhancement", tracer_name=__name__, attributes={"agent.name": self.name}
            ):
                result = self.task_enhancer(
                    task=task,
                    agent_role=self._get_agent_role_description(),
                    conversation_context=context or "No prior context",
                )

                metadata = {
                    "key_requirements": result.key_requirements,
                    "expected_format": result.expected_output_format,
                    "enhanced": True,
                }

                logger.debug(
                    f"DSPy enhanced task for {self.name}: "
                    f"{task[:50]}... -> {result.enhanced_task[:50]}..."
                )

                return result.enhanced_task, metadata

        except Exception as e:
            logger.warning(f"DSPy enhancement failed for {self.name}: {e}")
            return task, {"enhanced": False, "error": str(e)}

    async def execute_with_timeout(self, task: str) -> ChatMessage:
        """Execute the task with a timeout constraint.

        Note: This is a legacy helper method used by some workflows.
        Ideally workflows should call run() directly.
        """
        start_time = time.time()
        success = False
        try:
            # Use run() which returns AgentRunResponse, then extract message
            coro = self.run(task)
            response_obj = await asyncio.wait_for(coro, timeout=self.timeout)

            # Handle direct ChatMessage return (e.g. from mocks or legacy agents)
            if isinstance(response_obj, ChatMessage):
                success = True
                return response_obj

            # Extract first message or text
            if response_obj.messages:
                response = response_obj.messages[0]
            else:
                response = ChatMessage(role=Role.ASSISTANT, text=response_obj.text)

            success = True
            return response

        except TimeoutError:
            logger.warning(f"Agent {self.name} timed out after {self.timeout}s")
            return self._create_timeout_response(self.timeout)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return ChatMessage(
                role=Role.ASSISTANT,
                text=f"Error: {e}",
                metadata={"status": "error", "error": str(e)},
            )
        finally:
            duration = time.time() - start_time
            self.tracker.record_execution(
                agent_name=self.name or "unknown", duration=duration, success=success
            )

    def _normalize_input_to_text(
        self, messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> str:
        """Extract text prompt from various message formats."""
        if not messages:
            return ""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, ChatMessage):
            return messages.text
        if isinstance(messages, list):
            # Return the text of the last message if it's a list
            last_msg = messages[-1]
            return last_msg.text if isinstance(last_msg, ChatMessage) else str(last_msg)
        return str(messages)

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AgentRunResponse:
        """Execute the agent's logic.

        Returns:
            AgentRunResponse containing the result.
        """
        prompt = self._normalize_input_to_text(messages)
        agent_kwargs = dict(kwargs)
        logger.info(f"Agent {self.name} running with strategy: {self.reasoning_strategy}")

        # Check if DSPy is enabled
        if self.enable_dspy:
            # Check cache
            cached_result = self.cache.get(prompt)
            if cached_result:
                logger.info(f"Cache hit for agent {self.name}")
                return AgentRunResponse(
                    messages=ChatMessage(role=Role.ASSISTANT, text=cached_result),
                    additional_properties={"cached": True, "strategy": self.reasoning_strategy},
                )

            try:
                response_text = ""
                if self.reasoning_strategy == "react" and self.react_module:
                    # Use ReAct strategy
                    result = self.react_module(question=prompt, tools=self.tools)
                    response_text = getattr(result, "answer", str(result))

                elif self.reasoning_strategy == "program_of_thought" and self.pot_module:
                    # Use Program of Thought strategy
                    try:
                        result = self.pot_module(question=prompt)
                    except RuntimeError as exc:
                        return await self._handle_pot_failure(
                            messages=messages,
                            thread=thread,
                            agent_kwargs=agent_kwargs,
                            error=exc,
                        )
                    response_text = getattr(result, "answer", str(result))

                if response_text:
                    # Cache the result
                    self.cache.set(prompt, response_text)

                    return AgentRunResponse(
                        messages=ChatMessage(role=Role.ASSISTANT, text=response_text),
                        additional_properties={"strategy": self.reasoning_strategy},
                    )

                # If strategy didn't produce specific output (or was CoT/Default), fallback might be better
                # unless we implement explicit CoT module here. For now, if no specific module result,
                # fall through to fallback.

            except Exception as e:
                logger.error(f"DSPy strategy failed for {self.name}: {e}")
                # Fall through to fallback

        # Fallback to standard ChatAgent execution
        return await super().run(messages=messages, thread=thread, **kwargs)

    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Run the agent as a stream."""
        prompt = self._normalize_input_to_text(messages)

        # If DSPy is enabled and strategy is specialized (ReAct/PoT), we might want to run it.
        # However, our current DSPy modules are blocking.
        # We can yield a "Thinking" status then the result.

        should_use_dspy = self.enable_dspy and (
            (self.reasoning_strategy == "react" and self.react_module)
            or (self.reasoning_strategy == "program_of_thought" and self.pot_module)
        )

        if should_use_dspy:
            # Check cache
            cached_result = self.cache.get(prompt)
            if cached_result:
                yield AgentRunResponseUpdate(
                    text=cached_result, role=Role.ASSISTANT, additional_properties={"cached": True}
                )
                return

            try:
                # Yield a "Thinking" status if possible, or just block.
                # Since we can't easily stream partial DSPy steps yet without deep hooks,
                # we'll just await the result and yield it.

                response_text = ""
                if self.reasoning_strategy == "react" and self.react_module:
                    result = self.react_module(question=prompt, tools=self.tools)
                    response_text = getattr(result, "answer", str(result))
                elif self.reasoning_strategy == "program_of_thought" and self.pot_module:
                    result = self.pot_module(question=prompt)
                    response_text = getattr(result, "answer", str(result))

                if response_text:
                    self.cache.set(prompt, response_text)
                    yield AgentRunResponseUpdate(
                        text=response_text,
                        role=Role.ASSISTANT,
                        additional_properties={"strategy": self.reasoning_strategy},
                    )
                    return

            except RuntimeError as exc:
                async for update in self._yield_pot_stream_fallback(
                    messages=messages,
                    thread=thread,
                    agent_kwargs=kwargs,
                    error=exc,
                ):
                    yield update
                return

            except Exception as e:
                logger.error(f"DSPy streaming strategy failed for {self.name}: {e}")
                # Fall through to fallback

        # Fallback to standard streaming
        async for update in super().run_stream(messages=messages, thread=thread, **kwargs):
            yield update

    async def _handle_pot_failure(
        self,
        messages: Any,
        thread: AgentThread | None,
        agent_kwargs: dict[str, Any],
        error: Exception,
    ) -> AgentRunResponse:
        """Run fallback ChatAgent when Program of Thought fails."""

        note = self._build_pot_error_note(error)
        logger.warning("Program of Thought failed for %s: %s", self.name, note)

        fallback_response = await super().run(messages=messages, thread=thread, **agent_kwargs)
        # Prepend note to the first message text
        first_msg = None
        if fallback_response.messages:
            first_msg = fallback_response.messages[0]
            first_msg.text = self._apply_note_to_text(first_msg.text, note)
        else:
            fallback_response_text = getattr(fallback_response, "text", "")
            fallback_response.text = self._apply_note_to_text(fallback_response_text, note)  # type: ignore[attr-defined]

        existing_props = dict(fallback_response.additional_properties or {})
        existing_props.update(
            {
                "strategy": self.reasoning_strategy,
                "pot_error": note,
            }
        )
        fallback_response.additional_properties = existing_props
        return fallback_response

    async def _yield_pot_stream_fallback(
        self,
        messages: Any,
        thread: AgentThread | None,
        agent_kwargs: dict[str, Any],
        error: Exception,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Yield fallback streaming updates when PoT fails."""

        note = self._build_pot_error_note(error)
        note_update = AgentRunResponseUpdate(
            text=note,
            role=Role.ASSISTANT,
            additional_properties={"strategy": self.reasoning_strategy, "pot_error": note},
        )
        yield note_update

        async for update in super().run_stream(messages=messages, thread=thread, **agent_kwargs):
            props = dict(update.additional_properties or {})
            props.update({"strategy": self.reasoning_strategy, "pot_error": note})
            update.additional_properties = props
            yield update

    def _build_pot_error_note(self, error: Exception) -> str:
        """Create a user-facing note describing why PoT fell back."""

        fallback_reason = None
        if self.pot_module:
            fallback_reason = getattr(self.pot_module, "last_error", None)
        base = fallback_reason or str(error)
        return f"Program of Thought fallback: {base}"

    @staticmethod
    def _apply_note_to_text(text: str, note: str) -> str:
        """Prepend note to existing text while preserving whitespace."""

        if not text:
            return note
        if text.startswith(note):
            return text
        return f"{note}\n\n{text}"
