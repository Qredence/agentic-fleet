"""Service layer for workflows API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, NotRequired, Protocol, TypedDict


class WorkflowEvent(TypedDict):
    type: str
    data: NotRequired[dict[str, Any]]


class RunsWorkflow(Protocol):
    def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]: ...


class StubMagenticFleetWorkflow:
    """Stub implementation for MagenticFleetWorkflow.

    This class does not perform any real workflow processing.
    The magic number for truncating the message is configurable via `max_delta_length`.
    API responses are marked to indicate stub behavior.
    """
    def __init__(self, max_delta_length: int = 16):
        self.max_delta_length = max_delta_length

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        # STUB: This implementation only returns the first `max_delta_length` characters of the message.
        # No actual workflow processing is performed.
        yield {
            "type": "message.delta",
            "data": {
                "delta": message[:self.max_delta_length],
                "stub": True,
                "note": "Stub implementation: no real workflow processing performed."
            }
        }
        yield {
            "type": "message.done",
            "data": {
                "stub": True,
                "note": "Stub implementation: no real workflow processing performed."
            }
        }


def create_magentic_fleet_workflow(max_delta_length: int = 16) -> RunsWorkflow:
    """Factory for MagenticFleetWorkflow. Allows configuration of stub max_delta_length."""
    return StubMagenticFleetWorkflow(max_delta_length=max_delta_length)
