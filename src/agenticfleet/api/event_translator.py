"""Translator for converting Magentic events to SSE format."""

from __future__ import annotations

import logging
from typing import Any

from agent_framework import (
    MagenticAgentDeltaEvent,
    MagenticAgentMessageEvent,
    MagenticFinalResultEvent,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)

from agenticfleet.api.models import SSEEvent, SSEEventType

logger = logging.getLogger(__name__)


class EventTranslator:
    """Translates Microsoft Agent Framework events to SSE format.

    This class provides a clean separation between the internal Magentic event
    types and the SSE events sent to clients. It handles event type mapping,
    data extraction, and SSE formatting.
    """

    def translate_to_sse(
        self,
        event: Any,
        workflow_id: str | None = None,
    ) -> SSEEvent | None:
        """Translate a Magentic event to SSE format.

        Args:
            event: Magentic event object to translate
            workflow_id: Optional workflow ID for context

        Returns:
            SSEEvent instance, or None if event type is not supported

        """
        # Orchestrator/Manager messages
        if isinstance(event, MagenticOrchestratorMessageEvent):
            return self._translate_orchestrator_message(event, workflow_id)

        # Agent delta (streaming output)
        elif isinstance(event, MagenticAgentDeltaEvent):
            return self._translate_agent_delta(event, workflow_id)

        # Agent message (complete output)
        elif isinstance(event, MagenticAgentMessageEvent):
            return self._translate_agent_message(event, workflow_id)

        # Final result
        elif isinstance(event, MagenticFinalResultEvent):
            return self._translate_final_result(event, workflow_id)

        # Workflow output
        elif isinstance(event, WorkflowOutputEvent):
            return self._translate_workflow_output(event, workflow_id)

        else:
            logger.warning(f"Unknown event type: {type(event).__name__}")
            return None

    def _translate_orchestrator_message(
        self,
        event: MagenticOrchestratorMessageEvent,
        workflow_id: str | None,
    ) -> SSEEvent:
        """Translate orchestrator message event to SSE."""
        message_text = getattr(event.message, "text", "")

        data: dict[str, Any] = {
            "kind": event.kind,
            "message": message_text,
            "timestamp": None,  # Will be filled by server
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        return SSEEvent(
            event=SSEEventType.ORCHESTRATOR_MESSAGE,
            data=data,
        )

    def _translate_agent_delta(
        self,
        event: MagenticAgentDeltaEvent,
        workflow_id: str | None,
    ) -> SSEEvent:
        """Translate agent delta event (streaming) to SSE."""
        data: dict[str, Any] = {
            "agent_id": event.agent_id,
            "text": event.text or "",
            "timestamp": None,
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        return SSEEvent(
            event=SSEEventType.AGENT_DELTA,
            data=data,
        )

    def _translate_agent_message(
        self,
        event: MagenticAgentMessageEvent,
        workflow_id: str | None,
    ) -> SSEEvent:
        """Translate agent message event (complete) to SSE."""
        message_text = getattr(event.message, "text", "") if event.message else ""

        data: dict[str, Any] = {
            "agent_id": event.agent_id,
            "message": message_text,
            "timestamp": None,
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        return SSEEvent(
            event=SSEEventType.AGENT_MESSAGE,
            data=data,
        )

    def _translate_final_result(
        self,
        event: MagenticFinalResultEvent,
        workflow_id: str | None,
    ) -> SSEEvent:
        """Translate final result event to SSE."""
        result_text = getattr(event.message, "text", "") if event.message else ""

        data: dict[str, Any] = {
            "result": result_text,
            "timestamp": None,
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        return SSEEvent(
            event=SSEEventType.FINAL_RESULT,
            data=data,
        )

    def _translate_workflow_output(
        self,
        event: WorkflowOutputEvent,
        workflow_id: str | None,
    ) -> SSEEvent:
        """Translate workflow output event to SSE.

        Workflow outputs are currently logged but not streamed to clients.
        This could be enhanced to support structured data streaming.
        """
        data: dict[str, Any] = {
            "output": event.data,
            "timestamp": None,
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        # Using agent_message type for now, could create dedicated workflow.output type
        return SSEEvent(
            event=SSEEventType.AGENT_MESSAGE,
            data=data,
        )

    def create_error_event(
        self,
        error: str | Exception,
        workflow_id: str | None = None,
    ) -> SSEEvent:
        """Create an error SSE event.

        Args:
            error: Error message or exception
            workflow_id: Optional workflow ID for context

        Returns:
            SSEEvent for the error

        """
        error_msg = str(error)
        data: dict[str, Any] = {
            "error": error_msg,
            "timestamp": None,
        }

        if workflow_id:
            data["workflow_id"] = workflow_id

        return SSEEvent(
            event=SSEEventType.ERROR,
            data=data,
        )

    def create_workflow_started_event(
        self,
        workflow_id: str,
        workflow_name: str,
    ) -> SSEEvent:
        """Create a workflow started SSE event.

        Args:
            workflow_id: ID of the workflow
            workflow_name: Name of the workflow

        Returns:
            SSEEvent for workflow start

        """
        return SSEEvent.workflow_started(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
        )

    def create_workflow_completed_event(
        self,
        workflow_id: str,
        result: Any,
    ) -> SSEEvent:
        """Create a workflow completed SSE event.

        Args:
            workflow_id: ID of the workflow
            result: Final result from the workflow

        Returns:
            SSEEvent for workflow completion

        """
        return SSEEvent.workflow_completed(
            workflow_id=workflow_id,
            result=result,
        )
