"""Response aggregator service for converting Magentic events to OpenAI-compatible format."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from agentic_fleet.api.responses.schemas import (
    OrchestratorMessageEvent,
    ResponseCompletedEvent,
    ResponseDelta,
    ResponseDeltaEvent,
    ResponseMessage,
)
from agentic_fleet.models.events import WorkflowEvent
from agentic_fleet.models.requests import WorkflowRunRequest, WorkflowRunResponse

logger = logging.getLogger(__name__)


class ResponseAggregator:
    """Aggregates workflow events into OpenAI-compatible response format."""

    def __init__(
        self,
        workflow_id: str | None = None,
        request: WorkflowRunRequest | None = None,
    ) -> None:
        self._workflow_id = workflow_id
        self._request = request
        self._response_metadata: WorkflowRunResponse | None = None
        self._accumulated_content = ""
        self._agent_id: str | None = None
        self._reasoning_agent_id: str | None = None
        self._accumulated_reasoning = ""
        self._cached = False
        self._metadata_payload: dict[str, Any] = {}
        self._last_completion_metadata: dict[str, Any] | None = None

    def set_request_context(self, workflow_id: str, request: WorkflowRunRequest) -> None:
        """Bind workflow/request context for subsequent aggregation."""

        self._workflow_id = workflow_id
        self._request = request

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
        self._initialize_response_metadata()
        completed_sent = False

        try:
            async for event in events:
                event_type = event.get("type")
                event_data = event.get("data", {})
                openai_type = event.get("openai_type")
                event_metadata = (
                    event_data.get("metadata") if isinstance(event_data, dict) else None
                )

                if event_metadata and isinstance(event_metadata, dict):
                    self._metadata_payload.update(event_metadata)

                correlation_id = event.get("correlation_id")
                if correlation_id and self._response_metadata is not None:
                    self._response_metadata.correlation_id = correlation_id

                if event_type == "message.delta":
                    # Handle delta events
                    delta_value = event_data.get("delta") if isinstance(event_data, dict) else ""
                    delta_text = self._extract_text(delta_value)
                    agent_id = event_data.get("agent_id") if isinstance(event_data, dict) else None
                    if isinstance(event_data, dict) and event_data.get("cached"):
                        self._cached = True

                    if delta_text:
                        self._accumulated_content += delta_text
                        self._agent_id = agent_id

                        # Emit OpenAI-compatible delta event
                        delta_event = ResponseDeltaEvent(
                            type="response.delta",
                            delta=ResponseDelta(
                                content=delta_text,
                                agent_id=agent_id,
                                cached=self._cached or bool(event_data.get("cached")),
                            ),
                        )
                        yield f"data: {delta_event.model_dump_json(exclude_none=True)}\n\n"

                elif event_type == "reasoning.delta":
                    delta_value = event_data.get("delta") if isinstance(event_data, dict) else ""
                    delta_text = self._extract_text(delta_value)

                    if isinstance(event_data, dict) and event_data.get("cached"):
                        self._cached = True

                    if delta_text:
                        self._accumulated_reasoning += delta_text
                        agent_id = (
                            event_data.get("agent_id") if isinstance(event_data, dict) else None
                        )
                        if agent_id:
                            self._reasoning_agent_id = agent_id
                        reasoning_event: dict[str, Any] = {
                            "type": "reasoning.delta",
                            "reasoning": delta_text,
                        }
                        if self._reasoning_agent_id:
                            reasoning_event["agent_id"] = self._reasoning_agent_id
                        if self._cached:
                            reasoning_event["cached"] = True

                        yield f"data: {json.dumps(reasoning_event)}\n\n"
                    continue

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

                    if isinstance(event_data, dict) and event_data.get("cached"):
                        self._cached = True

                    # Check for reasoning content
                    reasoning = (
                        event_data.get("reasoning") if isinstance(event_data, dict) else None
                    )
                    if not reasoning and self._accumulated_reasoning:
                        reasoning = self._accumulated_reasoning

                    agent_id = None
                    if isinstance(event_data, dict):
                        agent_id = event_data.get("agent_id")
                    if agent_id is None:
                        agent_id = self._reasoning_agent_id or self._agent_id

                    # Emit reasoning.completed event if reasoning is present
                    if reasoning:
                        reasoning_event = {
                            "type": "reasoning.completed",
                            "reasoning": str(reasoning),
                        }
                        if agent_id:
                            reasoning_event["agent_id"] = agent_id
                        if self._cached:
                            reasoning_event["cached"] = True
                        yield f"data: {json.dumps(reasoning_event)}\n\n"
                    self._accumulated_reasoning = ""
                    self._reasoning_agent_id = None

                    completed_event = ResponseCompletedEvent(
                        type="response.completed",
                        response=ResponseMessage(
                            role="assistant",
                            content=final_content,
                        ),
                        metadata=self._build_completion_metadata(),
                    )
                    yield f"data: {completed_event.model_dump_json(exclude_none=True)}\n\n"
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
                        if isinstance(event_data, dict) and event_data.get("cached"):
                            self._cached = True
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
                    metadata=self._build_completion_metadata(),
                )
                yield f"data: {completed_event.model_dump_json(exclude_none=True)}\n\n"
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

    def get_response_metadata(self) -> WorkflowRunResponse | None:
        """Return workflow response metadata if available."""

        if self._response_metadata is not None:
            self._response_metadata.cached = self._cached
        return self._response_metadata

    def reset(self) -> None:
        """Reset aggregator state."""
        self._accumulated_content = ""
        self._agent_id = None
        self._reasoning_agent_id = None
        self._accumulated_reasoning = ""
        self._cached = False
        self._metadata_payload = {}
        self._last_completion_metadata = None

    def _initialize_response_metadata(self) -> None:
        if self._workflow_id is None:
            self._response_metadata = None
            return

        conversation_id = self._request.conversation_id if self._request else None
        correlation_id = self._request.correlation_id if self._request else None
        self._response_metadata = WorkflowRunResponse(
            workflow_id=self._workflow_id,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
        )

        if self._request:
            if self._request.metadata:
                self._metadata_payload.update(self._request.metadata)
            if self._request.context:
                self._metadata_payload.setdefault("context", {}).update(self._request.context)

    def _build_completion_metadata(self) -> dict[str, Any] | None:
        metadata: dict[str, Any] = {}

        if self._response_metadata is not None:
            self._response_metadata.cached = self._cached
            metadata["workflow_id"] = self._response_metadata.workflow_id
            if self._response_metadata.conversation_id is not None:
                metadata["conversation_id"] = self._response_metadata.conversation_id
            if self._response_metadata.correlation_id is not None:
                metadata["correlation_id"] = self._response_metadata.correlation_id
            metadata["cached"] = self._cached
            metadata["started_at"] = self._response_metadata.started_at.isoformat()
        elif self._cached:
            metadata["cached"] = True

        if self._metadata_payload:
            metadata.setdefault("details", {}).update(self._metadata_payload)

        self._last_completion_metadata = metadata or None
        return self._last_completion_metadata

    def get_completion_metadata(self) -> dict[str, Any] | None:
        """Return metadata emitted with completion events."""

        return self._last_completion_metadata
