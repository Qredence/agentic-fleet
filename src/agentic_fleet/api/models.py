"""Pydantic models for the Agentic Fleet API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    """Request model for starting a workflow."""

    task: str = Field(..., description="The task description to execute")
    config: dict[str, Any] | None = Field(
        default=None, description="Optional workflow configuration overrides"
    )


class WorkflowResponse(BaseModel):
    """Response model for a completed workflow."""

    result: str = Field(..., description="The final result of the workflow")
    quality_score: float = Field(..., description="The quality score of the result")
    execution_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary of the execution"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkflowStatus(BaseModel):
    """Status model for a running workflow."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: str = Field(..., description="Current status (running, completed, failed)")
    progress: dict[str, Any] | None = Field(default=None, description="Progress details")
