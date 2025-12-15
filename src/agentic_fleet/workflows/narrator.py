"""
Event Narrator module for AgenticFleet.

This module uses DSPy to verify and translate raw workflow events
into user-friendly narratives.
"""

from typing import Any, TypedDict

import dspy

from ..dspy_modules.signatures import WorkflowNarration
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkflowEvent(TypedDict, total=False):
    """Structure of a workflow event."""

    timestamp: str
    """Event timestamp."""

    type: str
    """Event type identifier."""

    data: dict[str, Any]
    """Event data payload."""


class EventNarrator(dspy.Module):
    """Translates workflow events into a cohesive narrative."""

    def __init__(self) -> None:
        super().__init__()
        self.generate_narrative = dspy.Predict(WorkflowNarration)

    def forward(self, events: list[WorkflowEvent]) -> dspy.Prediction:
        """
        Generate a narrative for the given list of events.

        Args:
            events: List of WorkflowEvent dictionaries containing workflow details.

        Returns:
            dspy.Prediction with a 'narrative' field.
        """
        # Format events into a structured log string for better LLM consumption
        events_log = []
        for i, event in enumerate(events, 1):
            timestamp = event.get("timestamp", "unknown time")
            event_type = event.get("type", "unknown type")
            details = str(event.get("data", {}))
            events_log.append(f"[{i}] {timestamp} - {event_type}: {details}")

        events_str = "\n".join(events_log)

        logger.debug(f"Narrating {len(events)} events...")
        return self.generate_narrative(events_log=events_str)
