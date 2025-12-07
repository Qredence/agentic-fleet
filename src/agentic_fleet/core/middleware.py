"""Middleware utilities for bridging runtime history to DSPy examples."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, cast

import dspy
from agent_framework._types import ChatMessage, Role

from agentic_fleet.utils.history_manager import HistoryManager
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.utils.types import MessageLike

logger = setup_logger(__name__)

# Try to import Azure AI Agents types, but fail gracefully if not available
try:  # pragma: no cover - optional dependency
    from azure.ai.agents.models import ThreadMessage
except ImportError:  # pragma: no cover - optional dependency
    ThreadMessage = None  # type: ignore[misc,assignment]

# Type alias for message types - union of known message types
type _MessageType = ChatMessage | MessageLike | dict[str, Any]


class ChatMiddleware:
    """Base class for chat middlewares."""

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Called when a chat task starts."""

    async def on_event(self, event: Any) -> None:
        """Called when an event occurs during execution."""

    async def on_end(self, result: Any) -> None:
        """Called when a chat task completes successfully."""

    async def on_error(self, error: Exception) -> None:
        """Called when a chat task fails."""


class BridgeConverter:
    """Converts Microsoft Agent Framework objects to DSPy objects."""

    @staticmethod
    def message_to_dict(message: _MessageType) -> dict[str, Any]:
        """
        Normalize a variety of message-like inputs into a dictionary with keys "role" and "content".

        Returns:
            dict[str, Any]: A mapping with "role" set to the message role as a string and "content" set to the message text content. If the input is a dict it is returned as-is; unknown types produce {"role": "unknown", "content": str(message)}.
        """
        # Handle dict first (before hasattr checks)
        if isinstance(message, dict):
            return cast(dict[str, Any], message)

        if isinstance(message, ChatMessage):
            return {
                "role": message.role.value if hasattr(message.role, "value") else str(message.role),
                "content": message.text,
            }

        # Handle MessageLike (Azure ThreadMessage and similar)
        if hasattr(message, "role") and hasattr(message, "content"):
            content_str: str = ""
            if isinstance(message.content, list):
                for item in message.content:
                    if hasattr(item, "text") and hasattr(item.text, "value"):
                        content_str += str(item.text.value)
                    elif hasattr(item, "text"):
                        content_str += str(item.text)
            else:
                content_str = str(message.content)

            return {
                "role": str(message.role),
                "content": content_str,
            }

        return {"role": "unknown", "content": str(message)}

    @classmethod
    def thread_to_example(
        cls,
        messages: list[_MessageType],
        task_override: str | None = None,
        labels: dict[str, Any] | None = None,
    ) -> dspy.Example:
        """
        Create a DSPy Example from a conversation thread.

        Determines the example task (uses task_override when provided; otherwise the most recent message with role "user" or "human"; defaults to "Unknown task" if none found), builds a context string from preceding messages as "role: content" lines, and returns a dspy.Example with inputs "task", "context", and "current_context".

        Parameters:
            messages (list[_MessageType]): Sequence of messages to convert; each message will be normalized to a dict with "role" and "content".
            task_override (str | None): If set, use this value as the example task instead of inferring from messages.
            labels (dict[str, Any] | None): Optional label fields to include on the returned example.

        Returns:
            dspy.Example: An example containing the constructed inputs ("task", "context", "current_context"); if `labels` is provided, those label fields are included on the example.
        """
        history = [cls.message_to_dict(m) for m in messages]

        task = task_override
        context_messages = history[:-1] if history else []

        if not task and history:
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] in ("user", "human"):
                    task = history[i]["content"]
                    context_messages = history[:i]
                    break

        if not task:
            task = "Unknown task"

        context_str = "\n".join([f"{m['role']}: {m['content']}" for m in context_messages])

        inputs = {
            "task": task,
            "context": context_str,
            "current_context": context_str,
        }

        if labels:
            return dspy.Example(**inputs, **labels).with_inputs(
                "task", "context", "current_context"
            )

        return dspy.Example(**inputs).with_inputs("task", "context", "current_context")

    @staticmethod
    def example_to_messages(example: dspy.Example) -> list[ChatMessage]:
        """Convert a DSPy example back to a list of ChatMessages (for replay/debug)."""
        messages = []

        if hasattr(example, "context") and example.context:
            lines = example.context.split("\n")
            for line in lines:
                if ": " in line:
                    role, content = line.split(": ", 1)
                    role_enum = Role.USER if role.lower() in ("user", "human") else Role.ASSISTANT
                    messages.append(ChatMessage(role=role_enum, text=content))

        if hasattr(example, "task") and example.task:
            messages.append(ChatMessage(role=Role.USER, text=example.task))

        return messages


class BridgeMiddleware(ChatMiddleware):
    """Middleware that captures workflow execution for offline learning."""

    def __init__(
        self,
        history_manager: HistoryManager,
        dspy_examples_path: str | None = ".var/logs/dspy_examples.jsonl",
    ):
        self.history_manager = history_manager
        self.dspy_examples_path = dspy_examples_path
        self.execution_data: dict[str, Any] = {}

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Initialize execution data when workflow starts."""
        self.execution_data = {
            "workflowId": context.get("workflowId"),
            "task": task,
            "start_time": datetime.now().isoformat(),
            "mode": context.get("mode", "standard"),
            "metadata": context.get("metadata", {}),
        }

    async def on_event(self, event: Any) -> None:  # noqa: ARG002
        """Handle intermediate workflow events (currently a no-op)."""
        return None

    async def on_end(self, result: Any) -> None:
        """Persist execution data and DSPy example when workflow completes."""
        self.execution_data["end_time"] = datetime.now().isoformat()

        if isinstance(result, dict):
            self.execution_data.update(result)
        else:
            self.execution_data["result"] = str(result)

        try:
            await self.history_manager.save_execution_async(self.execution_data)
            await self._save_dspy_example()
        except Exception as exc:
            logger.error("Failed to save execution history in middleware: %s", exc)

    async def on_error(self, error: Exception) -> None:
        """Record error details and persist execution data on workflow failure."""
        self.execution_data["end_time"] = datetime.now().isoformat()
        self.execution_data["error"] = str(error)
        self.execution_data["status"] = "failed"

        try:
            await self.history_manager.save_execution_async(self.execution_data)
        except Exception as exc:
            logger.error("Failed to save error history in middleware: %s", exc)

    async def _save_dspy_example(self) -> None:
        if not self.dspy_examples_path:
            return

        task = self.execution_data.get("task")
        output = self.execution_data.get("result")

        if not task or not output:
            logger.warning(
                "Skipping DSPy example: missing task (%s) or output (%s) for workflowId %s.",
                task,
                output,
                self.execution_data.get("workflowId"),
            )
            return

        try:
            example = BridgeConverter.thread_to_example(
                messages=[
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": output},
                ],
                task_override=task,
            )

            example_dict = dict(example.items())
            line = json.dumps(example_dict) + "\n"
            path = self.dspy_examples_path
            dir_path = os.path.dirname(path)

            def write_file() -> None:
                os.makedirs(dir_path, exist_ok=True)
                with open(path, "a", encoding="utf-8") as file:
                    file.write(line)

            await asyncio.to_thread(write_file)
        except Exception as exc:
            logger.error("Failed to save DSPy example: %s", exc)
