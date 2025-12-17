"""Base agent classes for the fleet.

This module defines the base agent classes used throughout the system,
including the DSPy-enhanced agent that integrates with the Agent Framework.
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Any, cast

from agent_framework._agents import ChatAgent
from agent_framework._threads import AgentThread
from agent_framework._types import AgentRunResponse, AgentRunResponseUpdate, ChatMessage, Role

from ..dspy_modules.signatures import FleetPoT, FleetReAct
from ..utils.cache import TTLCache
from ..utils.logger import setup_logger
from ..utils.telemetry import PerformanceTracker, optional_span

if TYPE_CHECKING:
    from agent_framework.openai import OpenAIChatClient, OpenAIResponsesClient

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
        chat_client: OpenAIResponsesClient | OpenAIChatClient,
        instructions: str = "",
        description: str = "",
        tools: Any = None,
        enable_dspy: bool = True,
        timeout: int = 30,
        cache_ttl: int = 300,
        reasoning_strategy: str = "chain_of_thought",
        context_providers: Any = None,
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
            context_providers: Context providers for the agent
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            chat_client=chat_client,
            tools=tools,
            context_providers=context_providers,
        )

        self.enable_dspy = enable_dspy
        self.timeout = timeout
        self.reasoning_strategy = reasoning_strategy
        self.cache = TTLCache(ttl_seconds=cache_ttl)
        self.tracker = PerformanceTracker()
        self.task_enhancer: Any | None = None

        # Initialize reasoning modules using the agent's tools
        self.react_module = FleetReAct(tools=self.tools) if reasoning_strategy == "react" else None
        self.pot_module = FleetPoT() if reasoning_strategy == "program_of_thought" else None

    @property
    def tools(self) -> Any:
        """Expose tools from the internal chat agent.

        Returns:
            List of tools assigned to this agent, or empty list if none.
        """
        return getattr(self, "_tools", [])

    def _get_agent_role_description(self) -> str:
        """Get agent role description for DSPy enhancement.

        Extracts role description from agent configuration, preferring
        description over instructions, truncated to 200 characters.

        Returns:
            Truncated role description string.
        """
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
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None,
        thread: AgentThread | None = None,
    ) -> str:
        """Extracts and formats the conversational history into a single string.

        The last message is treated as the primary prompt, and previous messages
        provide context.
        """
        history: list[str | ChatMessage] = []
        if thread:
            thread_messages = getattr(thread, "messages", None)
            if thread_messages:
                history.extend(list(cast(list[str | ChatMessage], thread_messages)))

        if isinstance(messages, list):
            # If messages are provided, they are the source of truth.
            history = list(cast(list[str | ChatMessage], messages))
        elif messages and (not history or history[-1] != messages):
            # If there's a single new message, add it to the history if it's not already there.
            history.append(messages)

        if not history:
            return ""

        # Format the history into a string
        formatted_history = []
        for msg in history:
            if isinstance(msg, ChatMessage):
                role_name = "User" if msg.role == Role.USER else "Assistant"
                text = getattr(msg, "text", "") or ""
                if text:  # Only include messages with content
                    formatted_history.append(f"{role_name}: {text}")
            else:
                formatted_history.append(str(msg))

        return "\n\n".join(formatted_history)

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
        prompt = self._normalize_input_to_text(messages, thread=thread)
        agent_kwargs = dict(kwargs)
        logger.info(f"Agent {self.name} running with strategy: {self.reasoning_strategy}")

        # Check if DSPy is enabled
        if self.enable_dspy:
            # Check cache
            cached_result = self.cache.get(prompt)
            if cached_result:
                logger.info(f"Cache hit for agent {self.name}")
                return AgentRunResponse(
                    messages=[ChatMessage(role=Role.ASSISTANT, text=cached_result)],
                    additional_properties={"cached": True, "strategy": self.reasoning_strategy},
                )

            try:
                response_text = ""
                if self.reasoning_strategy == "react" and self.react_module:
                    # Use ReAct strategy
                    result = self.react_module(question=prompt)
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
                        messages=[ChatMessage(role=Role.ASSISTANT, text=response_text)],
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
        """Run the agent as a stream.

        For DSPy strategies that do not support native streaming (ReAct, PoT),
        this method runs the agent to get the full response and then yields it
        as a single update. For other cases, it delegates to the parent's
        streaming implementation.
        """
        # DSPy modules (ReAct, PoT) are blocking and do not support streaming.
        if self.enable_dspy and self.reasoning_strategy in ("react", "program_of_thought"):
            logger.warning(
                f"Agent {self.name} with reasoning strategy '{self.reasoning_strategy}' "
                "does not support true streaming. The full response will be sent at once."
            )
            # Execute the non-streaming run method to get the complete response.
            response = await self.run(messages=messages, thread=thread, **kwargs)

            # Determine the role for the update.
            response_role = Role.ASSISTANT
            if response.messages:
                response_role = response.messages[0].role

            # Yield a single update containing the full response.
            yield AgentRunResponseUpdate(
                text=response.text,
                messages=response.messages,
                additional_properties=response.additional_properties,
                role=response_role,
            )
            return

        # For streaming-compatible strategies, delegate to the parent implementation.
        async for update in super().run_stream(messages=messages, thread=thread, **kwargs):
            yield update

    async def _handle_pot_failure(
        self,
        messages: Any,
        thread: AgentThread | None,
        agent_kwargs: dict[str, Any],
        error: Exception,
    ) -> AgentRunResponse:
        """
        Invoke the base ChatAgent as a fallback and attach a Program of Thought (PoT) failure note to the response.

        Parameters:
            messages (Any): Original input messages passed to the fallback run.
            thread (AgentThread | None): Optional thread context to pass to the fallback run.
            agent_kwargs (dict[str, Any]): Additional keyword arguments forwarded to the base agent's run method.
            error (Exception): The PoT failure that triggered the fallback; used to build the user-facing note.

        Returns:
            AgentRunResponse: The fallback response with the PoT note prepended to the first message text (or to the response text if no messages), and with `additional_properties` extended to include `strategy` and `pot_error`.
        """

        note = self._build_pot_error_note(error)
        logger.warning("Program of Thought failed for %s: %s", self.name, note)

        fallback_response = await super().run(messages=messages, thread=thread, **agent_kwargs)
        # Prepend note to the first message text
        # ChatMessage.text is read-only, so create a new ChatMessage instead of modifying
        if fallback_response.messages:
            first_msg = fallback_response.messages[0]
            original_text = getattr(first_msg, "text", "")
            updated_text = self._apply_note_to_text(original_text, note)

            # Create a new ChatMessage with the updated text while preserving all other fields.
            # Prefer Pydantic model cloning APIs if available.
            update_patch: dict[str, Any] = {"text": updated_text}
            model_fields = getattr(type(first_msg), "model_fields", None)
            v1_fields = getattr(type(first_msg), "__fields__", None)
            if (isinstance(model_fields, dict) and "content" in model_fields) or (
                isinstance(v1_fields, dict) and "content" in v1_fields
            ):
                update_patch["content"] = updated_text

            updated_msg: ChatMessage
            model_copy = getattr(first_msg, "model_copy", None)
            if callable(model_copy):
                updated_msg = cast(ChatMessage, model_copy(update=update_patch))
            else:
                v1_copy = getattr(first_msg, "copy", None)
                if callable(v1_copy):
                    updated_msg = cast(ChatMessage, v1_copy(update=update_patch))
                elif dataclasses.is_dataclass(first_msg):
                    # Only pass fields that exist on the dataclass.
                    patch = {k: v for k, v in update_patch.items() if hasattr(first_msg, k)}
                    updated_msg = cast(ChatMessage, dataclasses.replace(first_msg, **patch))
                else:
                    # Last-resort fallback: manually reconstruct commonly used fields.
                    # (This may drop unknown fields on non-pydantic, non-dataclass message types.)
                    updated_msg = ChatMessage(
                        role=first_msg.role,
                        text=updated_text,
                        metadata=getattr(first_msg, "metadata", None),
                        additional_properties=getattr(first_msg, "additional_properties", None),
                    )
            # Replace the first message with the updated one
            # Note: We reassign messages assuming it's mutable. If AgentRunResponse.messages
            # becomes immutable, construct a new AgentRunResponse instead.
            fallback_response.messages = [updated_msg, *fallback_response.messages[1:]]
        else:
            fallback_response_text = getattr(fallback_response, "text", "")
            updated_text = self._apply_note_to_text(fallback_response_text, note)
            # Create a new message if there are no messages
            fallback_response.messages = [ChatMessage(role=Role.ASSISTANT, text=updated_text)]

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
        """Create a user-facing note describing why PoT fell back.

        Extracts the last error from the PoT module if available,
        otherwise uses the exception message.

        Args:
            error: The exception that caused the fallback.

        Returns:
            Formatted error note string prefixed with 'Program of Thought fallback:'.
        """

        fallback_reason = None
        if self.pot_module:
            fallback_reason = getattr(self.pot_module, "last_error", None)
        base = fallback_reason or str(error)
        return f"Program of Thought fallback: {base}"

    @staticmethod
    def _apply_note_to_text(text: str, note: str) -> str:
        """Prepend note to existing text while preserving whitespace.

        Avoids duplicating notes if already present at the start of text.

        Args:
            text: The original text content.
            note: The note to prepend.

        Returns:
            Combined text with note prepended, or just note if text is empty.
        """

        if not text:
            return note
        if text.startswith(note):
            return text
        return f"{note}\n\n{text}"

    def _create_timeout_response(self, timeout: int) -> ChatMessage:
        """Create a timeout response message.

        Generates a standardized ChatMessage indicating the task
        exceeded its time limit.

        Args:
            timeout: The timeout duration in seconds.

        Returns:
            ChatMessage with role=ASSISTANT and timeout metadata.
        """
        return ChatMessage(
            role=Role.ASSISTANT,
            text=f"Task execution timed out after {timeout} seconds.",
            metadata={"status": "timeout", "timeout": timeout},
        )
