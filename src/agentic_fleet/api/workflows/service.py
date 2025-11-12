"""Workflow service shims for Magentic Fleet.

Provides:
- create_workflow(workflow_id): async creation via WorkflowFactory
- StubMagenticFleetWorkflow: simple stub that emits one delta then done
- create_magentic_fleet_workflow(): legacy sync factory returning the stub

Kept minimal to satisfy legacy tests and current chat service imports.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent
from agentic_fleet.models.requests import WorkflowRunRequest
from agentic_fleet.utils.factory import get_workflow_factory

logger = logging.getLogger(__name__)


async def create_workflow(workflow_id: str = "magentic_fleet") -> RunsWorkflow:
    """Create a workflow instance using the YAML-driven WorkflowFactory (async).

    This is the canonical async entrypoint used by the chat service.

    Args:
        workflow_id: The workflow identifier to build (default: "magentic_fleet")

    Returns:
        RunsWorkflow instance built from the YAML configuration
    """
    factory = await get_workflow_factory()
    return await factory.create_from_yaml_async(workflow_id)


class StubMagenticFleetWorkflow(RunsWorkflow):
    """Legacy-compatible stub workflow.

    Emits:
    - message.delta with the provided message
    - message.done to signal completion

    Used by tests that import the legacy synchronous factory alias.
    """

    async def run(self, request: WorkflowRunRequest | str) -> AsyncGenerator[WorkflowEvent, None]:
        """Run the stub workflow and yield delta then done.

        Accepts either a raw ``str`` or a ``WorkflowRunRequest`` for backward
        compatibility with the updated ``RunsWorkflow`` protocol.
        """
        message = request.message if isinstance(request, WorkflowRunRequest) else request
        # Emit a delta containing the full message (tests expect "Test message" to be returned)
        yield {
            "type": "message.delta",
            "data": {
                "delta": message,
            },
        }
        # Emit completion
        yield {
            "type": "message.done",
            "data": {},
        }


def create_magentic_fleet_workflow(*args: Any, **kwargs: Any) -> RunsWorkflow:
    """Backward-compatible synchronous workflow factory alias.

    Returns a stub workflow for legacy test compatibility.
    New code should use async create_workflow() instead.

    Returns:
        RunsWorkflow (stub) instance.
    """
    return StubMagenticFleetWorkflow()


# Convenience re-exports for tests importing types from this module
__all__ = [
    "StubMagenticFleetWorkflow",
    "WorkflowEvent",
    "create_magentic_fleet_workflow",
    "create_workflow",
]
