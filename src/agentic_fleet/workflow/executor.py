"""Workflow execution engine."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from agentic_fleet.api.workflows.service import RunsWorkflow, WorkflowEvent

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Engine for executing workflows."""

    def __init__(self, workflow: RunsWorkflow) -> None:
        """Initialize executor.

        Args:
            workflow: Workflow instance to execute
        """
        self.workflow = workflow

    async def execute(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        """Execute workflow with a message.

        Args:
            message: Input message

        Yields:
            Workflow events as they occur
        """
        async for event in self.workflow.run(message):
            yield event
