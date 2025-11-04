"""Service layer for chat API."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException

from agentic_fleet.api.workflows.service import (
    create_magentic_fleet_workflow as _deprecated_workflow_alias,
)
from agentic_fleet.api.workflows.service import create_workflow
from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing workflow execution and event processing."""

    def __init__(self) -> None:
        """Initialize WorkflowService with InMemory workflow cache."""
        self._workflow_cache: dict[str, RunsWorkflow] = {}

    async def get_workflow(self, workflow_id: str = "magentic_fleet") -> RunsWorkflow:
        """Get or create a workflow instance.

        Uses InMemory caching to avoid rebuilding workflows on every request.

        Args:
            workflow_id: Workflow identifier (default: "magentic_fleet")

        Returns:
            Workflow instance implementing RunsWorkflow protocol
        """
        # Check cache first
        if workflow_id in self._workflow_cache:
            logger.debug(f"[WORKFLOW] Cache hit for workflow_id: {workflow_id}")
            return self._workflow_cache[workflow_id]

        # Cache miss - create workflow
        logger.info(f"[WORKFLOW] Cache miss - creating workflow: {workflow_id}")
        workflow = await create_workflow(workflow_id=workflow_id)
        self._workflow_cache[workflow_id] = workflow
        logger.info(f"[WORKFLOW] Workflow cached successfully: {workflow_id}")
        return workflow

    def invalidate_cache(self, workflow_id: str | None = None) -> None:
        """Invalidate workflow cache.

        Args:
            workflow_id: Specific workflow to invalidate. If None, clears all caches.
        """
        if workflow_id is None:
            logger.info("[WORKFLOW] Clearing all workflow caches")
            self._workflow_cache.clear()
        elif workflow_id in self._workflow_cache:
            logger.info(f"[WORKFLOW] Invalidating cache for workflow_id: {workflow_id}")
            del self._workflow_cache[workflow_id]
        else:
            logger.debug(f"[WORKFLOW] Workflow_id not in cache: {workflow_id}")

    async def execute_workflow(self, message: str) -> str:
        """Execute a workflow and return the final result.

        Args:
            message: The input message to process

        Returns:
            The final workflow result as a string

        Raises:
            HTTPException: If workflow execution fails
        """
        workflow = await self.get_workflow()
        try:
            events = workflow.run(message)
            return await self.process_workflow_events(events)
        except Exception as exc:
            logger.error("Workflow execution failed", exc_info=True)
            raise HTTPException(
                status_code=500, detail="An error occurred while processing your request"
            ) from exc

    async def process_workflow_events(self, events: AsyncGenerator[WorkflowEvent, None]) -> str:
        """Process workflow events and aggregate the result.

        Args:
            events: Async generator of workflow events

        Returns:
            Aggregated result from processing all events
        """
        parts: list[str] = []
        async for event in events:
            event_type = event.get("type")
            if event_type == "message.delta":
                data = event.get("data", {})
                delta = data.get("delta", "") if isinstance(data, dict) else ""
                parts.append(str(delta))
            elif event_type == "message.done":
                break
        return "".join(parts)


_workflow_service = WorkflowService()


def get_workflow_service() -> WorkflowService:
    """Return the singleton workflow service."""
    return _workflow_service


# Backward compatibility: some tests monkey-patch this symbol on chat.service.
# This now returns the synchronous stub immediately to match legacy behavior.
def create_magentic_fleet_workflow(
    *args: Any, **kwargs: Any
) -> RunsWorkflow:  # pragma: no cover - shim
    """Backward-compatible synchronous workflow factory alias.

    Args:
        *args: Positional arguments forwarded to legacy factory
        **kwargs: Keyword arguments forwarded to legacy factory

    Returns:
        Stub workflow implementing RunsWorkflow protocol.
    """
    return _deprecated_workflow_alias(*args, **kwargs)
