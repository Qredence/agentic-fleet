"""Base agent combining agent-framework ChatAgent with DSPy optimization.

This module provides a hybrid agent architecture that combines:
- agent-framework's production-ready ChatAgent infrastructure
- DSPy's prompt optimization and task enhancement capabilities
- Performance monitoring and caching
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import dspy
from agent_framework import AgentRunResponse, ChatAgent, ChatMessage, Role

from ..utils.cache import cache_agent_response
from ..utils.logger import setup_logger
from ..utils.telemetry import PerformanceTracker, optional_span

if TYPE_CHECKING:
    from agent_framework.openai import OpenAIResponsesClient

logger = setup_logger(__name__)


class TaskEnhancement(dspy.Signature):
    """Enhance agent task with additional context and clarity.

    This signature helps agents understand tasks better by:
    - Adding relevant context from conversation history
    - Clarifying ambiguous requirements
    - Breaking down complex multi-part tasks
    """

    task = dspy.InputField(desc="Original user task or question")
    agent_role = dspy.InputField(desc="Agent's specialized role and capabilities")
    conversation_context = dspy.InputField(desc="Recent conversation history (optional)")

    enhanced_task = dspy.OutputField(desc="Clarified task with added context")
    key_requirements = dspy.OutputField(desc="List of key requirements to fulfill")
    expected_output_format = dspy.OutputField(desc="Expected format of the response")


class DSPyEnhancedAgent(ChatAgent):
    """
    Enhanced agent combining agent-framework ChatAgent with DSPy optimization.

    Features:
    - DSPy task enhancement for better understanding
    - Response caching for repeated queries
    - Performance tracking and timeout management
    - Automatic context retention

    Usage:
        agent = DSPyEnhancedAgent(
            name="ResearcherAgent",
            chat_client=client,
            tools=TavilyMCPTool(),
            enable_dspy=True,
            cache_ttl=300
        )

        async for event in agent.run_stream_with_dspy(task):
            print(event)
    """

    def __init__(
        self,
        name: str,
        chat_client: OpenAIResponsesClient,
        instructions: str = "",
        description: str = "",
        tools: Any = None,
        enable_dspy: bool = True,
        cache_ttl: int = 300,
        timeout: int = 30,
    ):
        """Initialize DSPy-enhanced agent.

        Args:
            name: Agent name (e.g., "ResearcherAgent")
            chat_client: OpenAI client for LLM calls
            instructions: Agent instructions/system prompt
            description: Agent description
            tools: Tool instance or tuple of tools
            enable_dspy: Whether to enable DSPy task enhancement
            cache_ttl: Cache time-to-live in seconds (0 to disable)
            timeout: Maximum execution time per task in seconds
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
        self.cache_ttl = cache_ttl
        self.performance_tracker = PerformanceTracker()

        # Initialize DSPy task enhancer if enabled
        if self.enable_dspy:
            try:
                self.task_enhancer = dspy.ChainOfThought(TaskEnhancement)
                logger.debug(f"DSPy enhancement enabled for {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize DSPy for {name}: {e}")
                self.enable_dspy = False
                self.task_enhancer = None
        else:
            self.task_enhancer = None

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

    async def execute_with_timeout(
        self, task: str, context: str = "", timeout: int | None = None
    ) -> AgentRunResponse:
        """Execute task with configurable timeout.

        Args:
            task: Task to execute
            context: Optional conversation context
            timeout: Timeout in seconds (uses instance default if None)

        Returns:
            ChatMessage with agent response

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        timeout = timeout or self.timeout
        start_time = time.time()

        try:
            async with asyncio.timeout(timeout):
                # Enhance task with DSPy
                enhanced_task, metadata = self._enhance_task_with_dspy(task, context)

                # Execute with agent-framework
                result = await self.run(enhanced_task)

                if metadata:
                    extras = getattr(result, "additional_properties", None) or {}
                    cached_metadata = extras.get("metadata")
                    if isinstance(cached_metadata, dict):
                        cached_metadata.update(metadata)
                    else:
                        extras["metadata"] = metadata
                    result.additional_properties = extras

                duration = time.time() - start_time
                self.performance_tracker.record_execution(
                    agent_name=self.name,
                    duration=duration,
                    success=True,
                    metadata={"task": task, **metadata},
                )

                return result

        except TimeoutError:
            duration = time.time() - start_time
            self.performance_tracker.record_execution(
                agent_name=self.name,
                duration=duration,
                success=False,
                error="timeout",
                metadata={"task": task, "timeout": timeout},
            )
            logger.warning(f"{self.name} exceeded {timeout}s timeout")
            return self._create_timeout_response(timeout)
        except Exception as exc:
            duration = time.time() - start_time
            self.performance_tracker.record_execution(
                agent_name=self.name,
                duration=duration,
                success=False,
                error=str(exc),
                metadata={"task": task},
            )
            raise

    async def run_stream_with_dspy(
        self,
        task: str,
        context: str = "",
    ) -> AsyncGenerator[Any, None]:
        """Stream agent execution with DSPy enhancement.

        Args:
            task: Task to execute
            context: Optional conversation context

        Yields:
            Agent framework events (MagenticAgentMessageEvent, etc.)
        """
        start_time = time.time()

        try:
            # Enhance task with DSPy
            enhanced_task, metadata = self._enhance_task_with_dspy(task, context)

            # Stream execution with agent-framework
            async for event in self.run_stream(enhanced_task):
                yield event

            # Track performance
            duration = time.time() - start_time
            agent_name = self.name or self.__class__.__name__
            self.performance_tracker.record_execution(
                agent_name=agent_name, duration=duration, success=True, metadata=metadata
            )

        except Exception as e:
            duration = time.time() - start_time
            agent_name = self.name or self.__class__.__name__
            self.performance_tracker.record_execution(
                agent_name=agent_name, duration=duration, success=False, error=str(e)
            )
            logger.error(f"Error in {self.name} execution: {e}")
            raise

    @cache_agent_response(ttl=300)
    async def run_cached(self, task: str, context: str = "") -> AgentRunResponse:
        """Execute task with response caching.

        Args:
            task: Task to execute
            context: Optional conversation context

        Returns:
            ChatMessage (may be from cache)
        """
        return await self.execute_with_timeout(task, context)

    def _create_timeout_response(self, timeout: int) -> AgentRunResponse:
        """Create standard timeout response message.

        Args:
            timeout: Timeout value that was exceeded

        Returns:
            ChatMessage indicating timeout
        """
        message = ChatMessage(
            role=Role.ASSISTANT,
            text=f"⏱️ {self.name} exceeded {timeout}s time limit. Task may be too complex or require different approach.",
        )
        metadata = {
            "status": "timeout",
            "agent": self.name,
            "timeout": timeout,
        }
        return AgentRunResponse(
            messages=[message],
            additional_properties={
                "status": "timeout",
                "agent": self.name,
                "timeout": timeout,
                "metadata": metadata,
            },
        )

    def get_performance_stats(self) -> dict[str, Any]:
        """Get agent performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        return self.performance_tracker.get_stats(agent_name=self.name)
