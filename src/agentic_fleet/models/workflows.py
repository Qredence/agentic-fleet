"""Workflow models for the AgenticFleet API.

Defines workflow session and execution schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .base import WorkflowStatus


class WorkflowSession(BaseModel):
    """Workflow session metadata for tracking active workflows.

    Attributes:
        workflow_id: Unique identifier for the workflow.
        task: The task being executed.
        status: Current workflow status.
        created_at: When the workflow was created.
        started_at: When execution started.
        completed_at: When execution completed.
    """

    workflow_id: str = Field(..., description="Unique workflow identifier")
    task: str = Field(..., description="Task being executed")
    status: WorkflowStatus = Field(default=WorkflowStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    reasoning_effort: str | None = Field(default=None, description="Reasoning effort setting")

    model_config = ConfigDict(from_attributes=True)
