"""
Bridge Converter Module.

This module handles the translation between Microsoft Agent Framework's runtime objects
(ThreadMessage, CloudEvents) and DSPy's optimization objects (Example).
It serves as the "Bridge" layer ensuring the optimizer can learn from runtime history
without coupling the two systems at runtime.
"""

from typing import Any

import dspy
from agent_framework._types import ChatMessage, Role

# Try to import Azure AI Agents types, but fail gracefully if not available
try:
    from azure.ai.agents.models import ThreadMessage
except ImportError:
    ThreadMessage = object  # type: ignore


class BridgeConverter:
    """Converts Microsoft Agent Framework objects to DSPy objects."""

    @staticmethod
    def message_to_dict(message: ChatMessage | ThreadMessage | Any) -> dict[str, Any]:
        """Convert a message object to a standardized dictionary."""
        if isinstance(message, ChatMessage):
            return {
                "role": message.role.value if hasattr(message.role, "value") else str(message.role),
                "content": message.text,
            }

        # Handle Azure ThreadMessage
        if hasattr(message, "role") and hasattr(message, "content"):
            # Content in ThreadMessage is usually a list of ContentItem
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

        # Fallback for dict or unknown
        if isinstance(message, dict):
            return message

        return {"role": "unknown", "content": str(message)}

    @classmethod
    def thread_to_example(
        cls,
        messages: list[ChatMessage | ThreadMessage | Any],
        task_override: str | None = None,
        labels: dict[str, Any] | None = None,
    ) -> dspy.Example:
        """
        Flatten a conversation thread into a DSPy training example.

        Args:
            messages: List of conversation messages
            task_override: Optional explicit task description. If None, uses the last user message.
            labels: Optional dictionary of labels (e.g., {"assigned_to": ["Coder"]})

        Returns:
            dspy.Example: A training example suitable for DSPy optimization.
        """
        history = [cls.message_to_dict(m) for m in messages]

        # Extract task from last user message if not provided
        task = task_override
        context_messages = history[:-1] if history else []

        if not task and history:
            # Find last user message
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] in ("user", "human"):
                    task = history[i]["content"]
                    context_messages = history[:i]
                    break

        if not task:
            task = "Unknown task"

        # Format context string
        context_str = "\n".join([f"{m['role']}: {m['content']}" for m in context_messages])

        # Create base inputs
        inputs = {
            "task": task,
            "context": context_str,
            "current_context": context_str,  # Alias for some signatures
        }

        # Add labels if provided (for training)
        if labels:
            return dspy.Example(**inputs, **labels).with_inputs(
                "task", "context", "current_context"
            )

        # Return input-only example (for inference/prediction)
        return dspy.Example(**inputs).with_inputs("task", "context", "current_context")

    @staticmethod
    def example_to_messages(example: dspy.Example) -> list[ChatMessage]:
        """Convert a DSPy example back to a list of ChatMessages (for replay/debug)."""
        messages = []

        # Parse context string back to messages if possible
        # This is a heuristic since context is flattened
        if hasattr(example, "context") and example.context:
            lines = example.context.split("\n")
            for line in lines:
                if ": " in line:
                    role, content = line.split(": ", 1)
                    # Map role strings to Role enum if needed
                    role_enum = Role.USER if role.lower() in ("user", "human") else Role.ASSISTANT
                    messages.append(ChatMessage(role=role_enum, text=content))

        # Add task as user message
        if hasattr(example, "task") and example.task:
            messages.append(ChatMessage(role=Role.USER, text=example.task))

        return messages
