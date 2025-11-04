"""Event bridge for converting Microsoft Agent Framework events to API format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agentic_fleet.models.events import WorkflowEvent

if TYPE_CHECKING:
    from agent_framework import (
        MagenticAgentDeltaEvent,
        MagenticAgentMessageEvent,
        MagenticFinalResultEvent,
        MagenticOrchestratorMessageEvent,
        WorkflowOutputEvent,
    )
else:
    try:
        from agent_framework import (
            MagenticAgentDeltaEvent,
            MagenticAgentMessageEvent,
            MagenticFinalResultEvent,
            MagenticOrchestratorMessageEvent,
            WorkflowOutputEvent,
        )
    except ImportError:
        # Event types not available - will handle gracefully
        MagenticAgentDeltaEvent = None  # type: ignore[assignment,misc]
        MagenticAgentMessageEvent = None  # type: ignore[assignment,misc]
        MagenticFinalResultEvent = None  # type: ignore[assignment,misc]
        MagenticOrchestratorMessageEvent = None  # type: ignore[assignment,misc]
        WorkflowOutputEvent = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


def _json_safe_value(value: Any) -> Any:
    """Best-effort conversion of arbitrary values into JSON-safe structures."""

    if value is None or isinstance(value, str | int | float | bool):
        return value

    if hasattr(value, "model_dump") and callable(value.model_dump):  # Pydantic models
        return _json_safe_value(value.model_dump())

    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}

    if isinstance(value, list | tuple | set):
        return [_json_safe_value(item) for item in value]

    if hasattr(value, "__dict__"):
        return _json_safe_value(
            {
                key: getattr(value, key)
                for key in dir(value)
                if not key.startswith("_") and not callable(getattr(value, key))
            }
        )

    return str(value)


class WorkflowEventBridge:
    """Bridge for converting agent framework events to WorkflowEvent format."""

    @staticmethod
    def convert_event(event: Any, openai_format: bool = False) -> WorkflowEvent:
        """Convert agent framework event to WorkflowEvent format.

        Args:
            event: Event from agent framework
            openai_format: If True, emit OpenAI-compatible event types
                (response.delta, response.completed) alongside existing types

        Returns:
            WorkflowEvent dictionary
        """
        # Check if event types are available
        if (
            MagenticAgentDeltaEvent is None
            or MagenticAgentMessageEvent is None
            or MagenticFinalResultEvent is None
            or MagenticOrchestratorMessageEvent is None
        ):
            logger.warning("Agent framework event types not available")
            return {
                "type": "unknown",
                "data": {"raw": str(event)},
            }

        # Handle different event types
        if isinstance(event, MagenticAgentDeltaEvent):
            # Convert agent deltas to message.delta so they appear as streaming assistant messages
            # Each agent's output will be accumulated separately by the frontend
            delta_event: WorkflowEvent = {
                "type": "message.delta",
                "data": {
                    "delta": event.text or "",
                    "agent_id": event.agent_id,
                },
            }
            # Add OpenAI-compatible type if requested
            if openai_format:
                delta_event["openai_type"] = "response.delta"
            logger.debug(
                f"Converted MagenticAgentDeltaEvent to message.delta: "
                f"agent={event.agent_id}, delta_length={len(event.text or '')}"
            )
            return delta_event

        elif isinstance(event, MagenticAgentMessageEvent):
            # Signal agent message completion - frontend should finalize this agent's message
            # This marks the end of one agent's work and allows the frontend to create a separate message
            text = event.message.text if event.message else ""
            complete_event: WorkflowEvent = {
                "type": "agent.message.complete",
                "data": {
                    "agent_id": event.agent_id,
                    "content": text,
                },
            }
            # Add OpenAI-compatible type if requested
            if openai_format:
                complete_event["openai_type"] = "agent.message.complete"
            logger.debug(
                f"Converted MagenticAgentMessageEvent to agent.message.complete: "
                f"agent={event.agent_id}, text_length={len(text)}"
            )
            return complete_event

        elif isinstance(event, MagenticOrchestratorMessageEvent):
            text = event.message.text if event.message else ""
            kind = getattr(event, "kind", "unknown")
            orchestrator_event: WorkflowEvent = {
                "type": "orchestrator.message",
                "data": {
                    "message": text,
                    "kind": kind,
                },
            }
            # Add OpenAI-compatible type if requested
            if openai_format:
                orchestrator_event["openai_type"] = "orchestrator.message"
            logger.debug(
                f"Converted MagenticOrchestratorMessageEvent to orchestrator.message: kind={kind}"
            )
            return orchestrator_event

        elif isinstance(event, MagenticFinalResultEvent):
            text = event.message.text if event.message else ""
            final_event: WorkflowEvent = {
                "type": "message.done",
                "data": {
                    "result": text,
                },
            }
            # Add OpenAI-compatible type if requested
            if openai_format:
                final_event["openai_type"] = "response.completed"
            logger.debug(
                f"Converted MagenticFinalResultEvent to message.done: text_length={len(text)}"
            )
            return final_event

        elif WorkflowOutputEvent is not None and isinstance(event, WorkflowOutputEvent):
            # Handle workflow output event (final result from workflow)
            # Extract text from ChatMessage if present, otherwise convert to string
            if event.data is not None:
                # Check if data has a 'text' attribute (ChatMessage)
                if hasattr(event.data, "text"):
                    output = event.data.text
                # Check if data is iterable and has content items with text
                elif hasattr(event.data, "__iter__") and not isinstance(event.data, str):
                    try:
                        # Try to extract text from content items
                        texts = []
                        for item in event.data:
                            if hasattr(item, "text"):
                                texts.append(item.text)
                            elif hasattr(item, "__str__"):
                                texts.append(str(item))
                        output = "".join(texts) if texts else str(event.data)
                    except (TypeError, AttributeError):
                        output = str(event.data)
                else:
                    output = str(event.data)
            else:
                output = ""

            output_event: WorkflowEvent = {
                "type": "message.done",
                "data": {
                    "result": output,
                },
            }
            # Add OpenAI-compatible type if requested
            if openai_format:
                output_event["openai_type"] = "response.completed"
            logger.debug(
                f"Converted WorkflowOutputEvent to message.done: output_length={len(output)}"
            )
            return output_event

        else:
            # Check for additional Response API compatible events
            response_event_type = getattr(event, "type", None)
            if isinstance(response_event_type, str) and response_event_type.startswith("response."):
                payload = _json_safe_value(event)
                if isinstance(payload, dict):
                    payload.pop("type", None)
                response_event: WorkflowEvent = {
                    "type": response_event_type,
                    "data": payload if isinstance(payload, dict) else {"value": payload},
                }
                if openai_format:
                    response_event["openai_type"] = response_event_type
                logger.debug("Converted OpenAI response event: type=%s", response_event_type)
                return response_event

            # Check for ExecutorInvokedEvent and ExecutorCompletedEvent
            event_type_name = type(event).__name__

            if event_type_name in ("ExecutorInvokedEvent", "ExecutorCompletedEvent"):
                executor_id = getattr(event, "executor_id", "unknown")
                logger.debug(
                    f"Converting {event_type_name} to progress event: executor_id={executor_id}"
                )
                return {
                    "type": "progress",
                    "data": {
                        "stage": (
                            "executor" if "Invoked" in event_type_name else "executor.complete"
                        ),
                        "executor_id": executor_id,
                        "event_type": event_type_name,
                    },
                }

            if event_type_name == "WorkflowStartedEvent":
                return {
                    "type": "workflow.started",
                    "data": {
                        "timestamp": _json_safe_value(getattr(event, "timestamp", None)),
                    },
                }

            if event_type_name == "WorkflowStatusEvent":
                state = getattr(event, "state", None)
                details = {
                    "state": str(state) if state is not None else None,
                    "progress": _json_safe_value(getattr(event, "data", None)),
                }
                # Remove None values for cleanliness
                details = {k: v for k, v in details.items() if v is not None}
                return {
                    "type": "workflow.status",
                    "data": details,
                }

            # Unknown event type - log for debugging
            logger.warning(f"Unknown event type: {event_type_name}, event={str(event)[:200]}")
            return {
                "type": "unknown",
                "data": {
                    "raw": str(event),
                    "event_type": event_type_name,
                },
            }
