"""Message processing module for AgenticFleet.

This module provides functionality for processing and streaming messages in the chat interface.
"""

from typing import Any, Dict, List, Optional, Union

import chainlit as cl
from autogen_agentchat.messages import TextMessage

# Task status constants
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

async def stream_text(text: str, delay: float = 0.03) -> None:
    """Stream text with a delay between characters."""
    await cl.Message(content=text, stream=True).send()

async def process_response(
    response: Union[TextMessage, List[Any], Dict[str, Any]],
    collected_responses: List[str]
) -> None:
    """Process agent responses with step visualization and error handling."""
    try:
        if isinstance(response, TextMessage):
            await cl.Message(content=response.content, author=response.source).send()
            collected_responses.append(response.content)
        elif isinstance(response, (list, tuple)):
            for item in response:
                await process_response(item, collected_responses)
        elif isinstance(response, dict):
            if "content" in response:
                await cl.Message(content=response["content"]).send()
                collected_responses.append(response["content"])
            else:
                await cl.Message(content=str(response)).send()
                collected_responses.append(str(response))
        else:
            await cl.Message(content=str(response)).send()
            collected_responses.append(str(response))
    except Exception as e:
        error_msg = f"⚠️ Error processing response: {str(e)}"
        await cl.Message(content=error_msg).send() 