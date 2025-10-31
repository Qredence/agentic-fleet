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
    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        # Emit a simple start event and done; real integration to be added later
        yield {"type": "message.delta", "data": {"delta": message[:16]}}
        yield {"type": "message.done", "data": {}}


def create_magentic_fleet_workflow() -> RunsWorkflow:
    return StubMagenticFleetWorkflow()
