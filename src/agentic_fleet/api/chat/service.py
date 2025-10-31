"""Service layer for chat API."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import HTTPException

from agentic_fleet.api.workflows.service import WorkflowEvent, create_magentic_fleet_workflow

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing workflow execution and event processing."""

    def _create_workflow(self):
        """Create a new workflow instance.
        
        Returns:
            A workflow instance that can be used for execution
        """
        return create_magentic_fleet_workflow()

    async def execute_workflow(self, message: str) -> str:
        """Execute a workflow and return the final result.

        Args:
            message: The input message to process

        Returns:
            The final workflow result as a string

        Raises:
            HTTPException: If workflow execution fails
        """
        workflow = self._create_workflow()
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
