"""
Magentic Workflow Service with SSE streaming support.

Provides service layer for creating, executing, and managing
Magentic workflows with real-time event streaming.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from agentic_fleet.core.magentic_framework import MagenticContext
from agentic_fleet.models.events import WorkflowEvent
from agentic_fleet.utils.logging_sanitize import sanitize_log_value
from agentic_fleet.workflow.magentic_builder import MagenticFleet, create_default_fleet

logger = logging.getLogger(__name__)


class MagenticWorkflowService:
    """
    Service layer for Magentic workflow execution.

    Manages workflow lifecycle:
    - Creation and configuration
    - Execution with event streaming
    - Status monitoring
    - Session management

    Suitable for SSE streaming to frontend clients.
    """

    def __init__(self) -> None:
        """Initialize workflow service."""
        self.active_workflows: dict[str, dict[str, Any]] = {}
        self.fleet: MagenticFleet | None = None
        logger.info("MagenticWorkflowService initialized")

    @staticmethod
    def _sanitize_for_logging(value: str) -> str:
        """
        Sanitize user-controlled input for safe logging.

        Removes carriage return and newline characters to prevent log injection attacks.

        Args:
            value: The string to sanitize

        Returns:
            Sanitized string with \r and \n characters removed
        """
        return value.replace("\r", "").replace("\n", "")

    def _ensure_fleet(self) -> None:
        """Lazy-load fleet on first use."""
        if self.fleet is None:
            try:
                self.fleet = create_default_fleet()
                logger.info("Magentic fleet created successfully")
            except Exception as e:
                logger.error(f"Failed to create Magentic fleet: {e}", exc_info=True)
                raise

    async def create_workflow(self, task: str, config: dict[str, Any] | None = None) -> str:
        """
        Create new workflow instance.

        Args:
            task: The task description
            config: Optional configuration overrides

        Returns:
            Workflow ID for tracking and execution
        """
        workflow_id = str(uuid4())

        # Create context with optional config overrides
        context = MagenticContext(
            task=task,
            max_rounds=config.get("max_rounds", 30) if config else 30,
            max_stalls=config.get("max_stalls", 3) if config else 3,
            max_resets=config.get("max_resets", 2) if config else 2,
        )

        self.active_workflows[workflow_id] = {
            "task": task,
            "context": context,
            "status": "created",
            "created_at": None,  # Could add timestamp
            "updated_at": None,
        }

        logger.info(
            "Created workflow %s for task: %s",
            sanitize_log_value(workflow_id),
            sanitize_log_value(task[:100]),
        )
        return workflow_id

    async def execute_workflow(self, workflow_id: str) -> AsyncIterator[WorkflowEvent]:
        """
        Execute workflow with event streaming.

        Yields events suitable for SSE consumption by frontend.
        Events include workflow progress, agent actions, and completion.

        Args:
            workflow_id: The workflow ID to execute

        Yields:
            WorkflowEvent objects for SSE streaming
        """
        if workflow_id not in self.active_workflows:
            safe_workflow_id = self._sanitize_for_logging(workflow_id)
            yield WorkflowEvent(
                type="error", data={"message": f"Workflow {safe_workflow_id} not found"}
            )
            return

        workflow = self.active_workflows[workflow_id]
        workflow["status"] = "running"

        try:
            # Ensure fleet is initialized
            self._ensure_fleet()

            if self.fleet is None:
                raise RuntimeError("Fleet not initialized")

            # Stream workflow execution
            async for event in self.fleet.run_with_streaming(
                task=workflow["task"], context=workflow["context"]
            ):
                # Add workflow_id to event data
                event_data = event.get("data")
                if isinstance(event_data, dict):
                    event_data["workflow_id"] = workflow_id

                yield event

                # Update workflow status based on events
                event_type = event.get("type")
                if event_type == "workflow_complete":
                    workflow["status"] = "completed"
                elif event_type in ("error", "workflow_failed", "workflow_timeout"):
                    workflow["status"] = "failed"

        except Exception as e:
            logger.error(
                "Error executing workflow %s: %s",
                sanitize_log_value(workflow_id),
                e,
                exc_info=True,
            )
            workflow["status"] = "failed"
            yield WorkflowEvent(
                type="error",
                data={"workflow_id": workflow_id, "message": f"Workflow execution error: {e!s}"},
            )

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """
        Get current workflow status.

        Args:
            workflow_id: The workflow ID to query

        Returns:
            Status dictionary with workflow details
        """
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found", "workflow_id": workflow_id}

        workflow = self.active_workflows[workflow_id]
        context = workflow["context"]

        return {
            "workflow_id": workflow_id,
            "task": workflow["task"],
            "status": workflow["status"],
            "round_count": context.round_count,
            "phase": context.current_phase.value,
            "stall_count": context.stall_count,
            "reset_count": context.reset_count,
            "max_rounds": context.max_rounds,
            "observations_count": len(context.observations),
        }

    async def list_workflows(self) -> list[dict[str, Any]]:
        """
        List all active workflows.

        Returns:
            List of workflow status dictionaries
        """
        return [
            await self.get_workflow_status(workflow_id) for workflow_id in self.active_workflows
        ]

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete workflow from active sessions.

        Args:
            workflow_id: The workflow ID to delete

        Returns:
            True if deleted, False if not found
        """
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
            logger.info("Deleted workflow %s", sanitize_log_value(workflow_id))
            return True
        return False

    async def pause_workflow(self, workflow_id: str) -> dict[str, Any]:
        """
        Pause workflow execution.

        Note: Actual pause implementation would require
        checkpointing and state persistence.

        Args:
            workflow_id: The workflow ID to pause

        Returns:
            Status dictionary
        """
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}

        workflow = self.active_workflows[workflow_id]
        workflow["status"] = "paused"

        logger.info("Paused workflow %s", sanitize_log_value(workflow_id))
        return await self.get_workflow_status(workflow_id)

    async def resume_workflow(self, workflow_id: str) -> AsyncIterator[WorkflowEvent]:
        """
        Resume paused workflow.

        Args:
            workflow_id: The workflow ID to resume

        Yields:
            WorkflowEvent objects continuing from paused state
        """
        if workflow_id not in self.active_workflows:
            yield WorkflowEvent(type="error", data={"message": "Workflow not found"})
            return

        workflow = self.active_workflows[workflow_id]

        if workflow["status"] != "paused":
            yield WorkflowEvent(
                type="error", data={"message": f"Workflow is {workflow['status']}, not paused"}
            )
            return

        logger.info("Resuming workflow %s", sanitize_log_value(workflow_id))

        # Resume by continuing execution with existing context
        async for event in self.execute_workflow(workflow_id):
            yield event


# Singleton instance for API routes
_service_instance: MagenticWorkflowService | None = None


def get_workflow_service() -> MagenticWorkflowService:
    """
    Get singleton workflow service instance.

    Returns:
        MagenticWorkflowService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = MagenticWorkflowService()
    return _service_instance
