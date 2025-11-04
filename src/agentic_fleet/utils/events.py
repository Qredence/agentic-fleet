"""Event handling utilities."""

from __future__ import annotations

import logging

from agentic_fleet.models.events import WorkflowEvent

logger = logging.getLogger(__name__)


class EventHandler:
    """Utility for handling workflow events."""

    @staticmethod
    def log_event(event: WorkflowEvent) -> None:
        """Log a workflow event.

        Args:
            event: Workflow event to log
        """
        event_type = event.get("type", "unknown")
        logger.debug(f"Workflow event: type={event_type}")

    @staticmethod
    def is_completion_event(event: WorkflowEvent) -> bool:
        """Check if event indicates workflow completion.

        Args:
            event: Workflow event to check

        Returns:
            True if event indicates completion
        """
        return event.get("type") == "message.done"

    @staticmethod
    def is_error_event(event: WorkflowEvent) -> bool:
        """Check if event indicates an error.

        Args:
            event: Workflow event to check

        Returns:
            True if event indicates an error
        """
        return event.get("type") == "error"

    @staticmethod
    def extract_delta(event: WorkflowEvent) -> str:
        """Extract delta text from event.

        Args:
            event: Workflow event

        Returns:
            Delta text or empty string
        """
        if event.get("type") == "message.delta":
            data = event.get("data", {})
            if isinstance(data, dict):
                delta = data.get("delta", "")
                return str(delta) if delta else ""
        return ""
