"""
Response handler for AgenticFleet.

This module provides functionality for processing agent responses.
"""

from typing import Any

from autogen_agentchat.messages import TextMessage

# Constants
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"


async def process_response(
    response: TextMessage | list[Any] | dict[str, Any] | str
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Process agent responses and return structured data for rendering and any plan update.

    Args:
        response: The response from an agent, which can be a TextMessage, list, dict, or string.

    Returns:
        A tuple containing:
        - Optional[Dict[str, Any]]: Structured data for rendering (e.g., {'type': 'text', 'content': '...', 'author': '...'}), or None.
        - Optional[str]: Extracted plan text, or None.
    """
    processed_data: dict[str, Any] | None = None
    plan_update: str | None = None

    # Handle TextMessage objects
    if isinstance(response, TextMessage):
        content = response.content
        author = getattr(response, "sender", "Assistant")
        processed_data = {
            "type": "text",
            "content": content,
            "author": author,
        }

    # Handle dictionaries
    elif isinstance(response, dict):
        # Check if it's a structured message
        if "content" in response:
            processed_data = {
                "type": "text",
                "content": response["content"],
                "author": response.get("author", "Assistant"),
            }
        # Check if it's a plan update
        elif "plan" in response:
            plan_update = response["plan"]
        # Otherwise, just convert to string
        else:
            processed_data = {
                "type": "text",
                "content": str(response),
                "author": "Assistant",
            }

    # Handle lists
    elif isinstance(response, list):
        # Combine list items into a single string
        combined_content = "\n".join([str(item) for item in response])
        processed_data = {
            "type": "text",
            "content": combined_content,
            "author": "Assistant",
        }

    # Handle strings
    elif isinstance(response, str):
        processed_data = {
            "type": "text",
            "content": response,
            "author": "Assistant",
        }

    return processed_data, plan_update
