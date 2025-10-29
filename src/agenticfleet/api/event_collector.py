"""Event collector for buffering workflow events during execution."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from agenticfleet.api.models.chat_models import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class EventCollector:
    """Collects and buffers events from workflow execution for streaming."""

    def __init__(self, execution_id: str) -> None:
        """Initialize event collector.

        Args:
            execution_id: Unique execution ID
        """
        self.execution_id = execution_id
        self.messages: list[ChatMessage] = []
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._streaming = False
        self._background_tasks: set[asyncio.Task[None]] = set()

    def handle_agent_delta(self, event: Any) -> None:
        """Handle agent delta event (streaming text).

        Args:
            event: MagenticAgentDeltaEvent
        """
        try:
            agent_id = getattr(event, "agent_id", "unknown")
            text = getattr(event, "text", "")

            # Queue streaming event
            task = asyncio.create_task(
                self._event_queue.put(
                    {
                        "type": "delta",
                        "execution_id": self.execution_id,
                        "data": {"agent_id": agent_id, "text": text},
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception as e:
            logger.error(f"Error handling agent delta: {e}")

    def handle_agent_message(self, event: Any) -> None:
        """Handle complete agent message event.

        Args:
            event: MagenticAgentMessageEvent
        """
        try:
            agent_id = getattr(event, "agent_id", "unknown")
            content = getattr(event, "content", "")

            # Create ChatMessage
            message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                agent_id=agent_id,
                agent_type=self._map_agent_type(agent_id),
            )
            self.messages.append(message)

            # Queue complete message event
            task = asyncio.create_task(
                self._event_queue.put(
                    {
                        "type": "message",
                        "execution_id": self.execution_id,
                        "data": message.model_dump(),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception as e:
            logger.error(f"Error handling agent message: {e}")

    def handle_final_result(self, event: Any) -> None:
        """Handle final workflow result event.

        Args:
            event: MagenticFinalResultEvent
        """
        try:
            result = getattr(event, "result", "")

            # Create final message
            message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=result,
                agent_id="orchestrator",
                agent_type="manager",
            )
            self.messages.append(message)

            # Queue completion event
            task = asyncio.create_task(
                self._event_queue.put(
                    {
                        "type": "complete",
                        "execution_id": self.execution_id,
                        "data": {"result": result, "message": message.model_dump()},
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception as e:
            logger.error(f"Error handling final result: {e}")

    def handle_error(self, error: Exception) -> None:
        """Handle workflow error.

        Args:
            error: Exception that occurred
        """
        task = asyncio.create_task(
            self._event_queue.put(
                {
                    "type": "error",
                    "execution_id": self.execution_id,
                    "data": {"error": str(error)},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def get_event(self, timeout: float | None = None) -> dict[str, Any] | None:
        """Get next event from queue.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Event dict or None if timeout
        """
        try:
            return await asyncio.wait_for(self._event_queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def _map_agent_type(self, agent_id: str) -> str:
        """Map agent ID to frontend agent type.

        Args:
            agent_id: Backend agent ID

        Returns:
            Frontend agent type
        """
        agent_id_lower = agent_id.lower()

        if "orchestrator" in agent_id_lower or "manager" in agent_id_lower:
            return "manager"
        elif "planner" in agent_id_lower:
            return "planner"
        elif "executor" in agent_id_lower:
            return "executor"
        elif "coder" in agent_id_lower or "code" in agent_id_lower:
            return "coder"
        elif "verifier" in agent_id_lower or "reviewer" in agent_id_lower:
            return "verifier"
        elif "generator" in agent_id_lower:
            return "generator"
        elif "researcher" in agent_id_lower or "research" in agent_id_lower:
            return "researcher"
        else:
            return "assistant"
