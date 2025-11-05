"""Response aggregator service for converting Magentic events to OpenAI-compatible format."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from agentic_fleet.api.responses.models import (
    OrchestratorMessageEvent,
    ResponseCompletedEvent,
    ResponseDelta,
    ResponseDeltaEvent,
    ResponseMessage,
)
from agentic_fleet.models.events import WorkflowEvent

logger = logging.getLogger(__name__)


class ResponseAggregator:
    """Aggregates workflow events into OpenAI-compatible response format."""

    def __init__(self) -> None:
        """Initialize ResponseAggregator."""
        self._accumulated_content = ""
        self._agent_id: str | None = None

    @staticmethod
    def _extract_text(value: object) -> str:
        """Best-effort extraction of textual content from arbitrary event payloads."""

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, int | float | bool):
            return str(value)

        if isinstance(value, dict):
            # Prefer common text-bearing keys
            for key in ("content", "text", "message", "result", "value"):
                if key in value:
                    extracted = ResponseAggregator._extract_text(value[key])
                    if extracted:
                        return extracted
            # Fallback: join any remaining string-like values
            parts = [ResponseAggregator._extract_text(item) for item in value.values()]
            return "".join(part for part in parts if part)

        if isinstance(value, list | tuple | set):
            parts = [ResponseAggregator._extract_text(item) for item in value]
            return "".join(part for part in parts if part)

        return str(value)

    async def convert_stream(
        self, events: AsyncGenerator[WorkflowEvent, None]
    ) -> AsyncGenerator[str, None]:
        """Convert workflow events to OpenAI-compatible SSE stream.

        Args:
            events: Async generator of WorkflowEvent objects

        Yields:
            SSE-formatted strings with OpenAI-compatible events
        """
        # Ensure each invocation starts from a clean state so the aggregator can be reused
        self.reset()
        completed_sent = False

        try:
            async for event in events:
                event_type = event.get("type")
                event_data = event.get("data", {})
                openai_type = event.get("openai_type")

                if event_type == "message.delta":
                    # Handle delta events
                    delta_value = event_data.get("delta") if isinstance(event_data, dict) else ""
                    delta_text = self._extract_text(delta_value)
                    agent_id = event_data.get("agent_id") if isinstance(event_data, dict) else None

                    if delta_text:
                        self._accumulated_content += delta_text
                        self._agent_id = agent_id

                        # Emit OpenAI-compatible delta event
                        delta_event = ResponseDeltaEvent(
                            type="response.delta",
                            delta=ResponseDelta(content=delta_text, agent_id=agent_id),
                        )
                        yield f"data: {delta_event.model_dump_json()}\n\n"

                elif event_type == "orchestrator.message":
                    # Handle orchestrator messages
                    message_text = (
                        event_data.get("message", "") if isinstance(event_data, dict) else ""
                    )
                    kind = event_data.get("kind") if isinstance(event_data, dict) else None

                    if message_text:
                        orchestrator_event = OrchestratorMessageEvent(
                            type="orchestrator.message",
                            message=str(message_text),
                            kind=kind,
                        )
                        yield f"data: {orchestrator_event.model_dump_json()}\n\n"

                elif event_type == "message.done":
                    # Handle completion
                    result_value = event_data.get("result") if isinstance(event_data, dict) else ""
                    result_text = self._extract_text(result_value)
                    final_content = result_text if result_text else self._accumulated_content
                    self._accumulated_content = final_content

                    completed_event = ResponseCompletedEvent(
                        type="response.completed",
                        response=ResponseMessage(
                            role="assistant",
                            content=final_content,
                        ),
                    )
                    yield f"data: {completed_event.model_dump_json()}\n\n"
                    yield "data: [DONE]\n\n"
                    completed_sent = True
                    break

                elif event_type == "error":
                    # Handle errors
                    error_msg = (
                        event_data.get("error", "Unknown error")
                        if isinstance(event_data, dict)
                        else "Unknown error"
                    )
                    error_event = {
                        "type": "error",
                        "error": {"message": str(error_msg), "type": "execution_error"},
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    yield "data: [DONE]\n\n"
                    break

                elif openai_type and openai_type != "response.delta":
                    # Forward additional OpenAI-compatible events (e.g. code interpreter)
                    if isinstance(event_data, dict):
                        payload = {"type": openai_type, **event_data}
                    else:
                        payload = {"type": openai_type, "data": event_data}
                    yield f"data: {json.dumps(payload)}\n\n"

                    if openai_type == "response.completed":
                        final_text = ""
                        if isinstance(event_data, dict):
                            final_text = (
                                self._extract_text(event_data.get("result"))
                                or self._extract_text(event_data.get("response"))
                                or self._extract_text(event_data)
                            )
                        else:
                            final_text = self._extract_text(event_data)
                        if final_text:
                            self._accumulated_content = final_text
                        completed_sent = True
                        yield "data: [DONE]\n\n"
                        break
                    continue

            # If we didn't get a done event, emit a completion event regardless so
            # upstream clients (tests/UI) always see at least one structured event
            # followed by [DONE]. This maintains parity with chat streaming where
            # response.completed is always sent even for empty outputs.
            if not completed_sent:
                completed_event = ResponseCompletedEvent(
                    type="response.completed",
                    response=ResponseMessage(
                        role="assistant",
                        content=self._accumulated_content,
                    ),
                )
                yield f"data: {completed_event.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error(f"Error in response aggregation: {exc}", exc_info=True)
            error_event = {
                "type": "error",
                "error": {"message": str(exc), "type": "execution_error"},
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    def get_final_response(self) -> str:
        """Get accumulated response content.

        Returns:
            Final accumulated content
        """
        return self._accumulated_content

    def reset(self) -> None:
        """Reset aggregator state."""
        self._accumulated_content = ""
        self._agent_id = None
