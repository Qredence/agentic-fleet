"""Fast-path workflow for simple queries.

This module provides a lightweight workflow implementation that bypasses
the full multi-agent orchestration for simple queries that don't require
complex reasoning or multiple agent coordination.
"""

import logging
import os
from collections.abc import AsyncGenerator

from agent_framework.openai import OpenAIResponsesClient

from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent

logger = logging.getLogger(__name__)

__all__ = ["FastPathWorkflow", "create_fast_path_workflow"]


class FastPathWorkflow(RunsWorkflow):
    """Fast-path workflow for simple queries.

    This workflow bypasses the full Magentic orchestration and provides
    direct responses using a single LLM call for improved latency on
    simple queries.
    """

    def __init__(
        self,
        client: OpenAIResponsesClient | None = None,
        model: str | None = None,
    ):
        """Initialize fast-path workflow.

        Args:
            client: OpenAI Responses client (created from env if not provided)
            model: Model name (defaults to FAST_PATH_MODEL or gpt-5-mini)
        """
        self.model = model or os.getenv("FAST_PATH_MODEL", "gpt-5-mini")
        self.client = client or self._create_client()

    def _create_client(self) -> OpenAIResponsesClient:
        """Create OpenAI Responses client from environment variables.

        Returns:
            Configured OpenAIResponsesClient

        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        return OpenAIResponsesClient(
            model_id=self.model,
            api_key=api_key,
            base_url=base_url,  # Optional, uses default OpenAI endpoint if not provided
        )

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        """Run fast-path workflow with direct Responses API call.

        Args:
            message: Input message to process

        Yields:
            WorkflowEvent instances (message.delta and message.done)
        """
        try:
            sanitized_message = message[:100].replace('\n', '').replace('\r', '')
            logger.info(f"[FAST-PATH] Processing message with {self.model}: {sanitized_message}")

            # Use the Responses API streaming
            from agent_framework import ChatMessage, ChatOptions, TextContent

            messages = [ChatMessage(role="user", contents=[TextContent(text=message)])]
            chat_options = ChatOptions(
                model_id=self.model,
            )

            # Stream responses
            accumulated_content = ""
            async for update in self.client.get_streaming_response(
                messages=messages, chat_options=chat_options
            ):
                for content in update.contents:
                    if isinstance(content, TextContent) and content.text:
                        delta = content.text
                        accumulated_content += delta

                        # Emit delta event compatible with existing consumers
                        yield {
                            "type": "message.delta",
                            "data": {
                                "delta": delta,
                                "agent_id": "fast-path",
                                "accumulated": accumulated_content,
                            },
                        }

            # Emit completion event
            yield {
                "type": "message.done",
                "data": {
                    "content": accumulated_content,
                    "agent_id": "fast-path",
                    "metadata": {
                        "fast_path": True,
                        "model": self.model,
                    },
                },
            }

            logger.info(f"[FAST-PATH] Completed response ({len(accumulated_content)} chars)")

        except Exception as e:
            logger.error(f"[FAST-PATH] Error in fast-path workflow: {e}")
            # Emit error event
            yield {
                "type": "error",
                "data": {
                    "message": f"Fast-path error: {e!s}",
                    "agent_id": "fast-path",
                },
            }
            raise


def create_fast_path_workflow(
    model: str | None = None,
) -> FastPathWorkflow:
    """Create a fast-path workflow instance.

    Args:
        model: Model name (defaults to FAST_PATH_MODEL env var or gpt-5-mini)

    Returns:
        Configured FastPathWorkflow instance

    Example:
        >>> workflow = create_fast_path_workflow()
        >>> async for event in workflow.run("hello"):
        ...     print(event)
    """
    return FastPathWorkflow(
        model=model,
    )
