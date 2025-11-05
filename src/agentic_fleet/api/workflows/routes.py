"""
Workflow API routes with SSE streaming support for Magentic workflows.
"""

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import asdict
from typing import no_type_check

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agentic_fleet.api.workflows.magentic_service import get_workflow_service
from agentic_fleet.utils.factory import WorkflowFactory

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow."""

    task: str = Field(..., description="Task description for the workflow")
    config: dict[str, int] | None = Field(None, description="Optional configuration overrides")


class CreateWorkflowResponse(BaseModel):
    """Response for workflow creation."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    task: str = Field(..., description="Task description")
    status: str = Field(..., description="Workflow status")


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""

    workflow_id: str
    task: str
    status: str
    round_count: int
    phase: str
    stall_count: int
    reset_count: int
    max_rounds: int
    observations_count: int


# YAML-based workflow routes (legacy)
async def list_workflows() -> dict[str, list[dict[str, object]]]:
    """Return all workflows available in the YAML configuration."""
    factory = WorkflowFactory()
    return {"workflows": await factory.list_available_workflows_async()}


async def get_workflow(workflow_id: str) -> dict[str, object]:
    """Return detailed configuration for a specific workflow."""
    factory = WorkflowFactory()
    try:
        config = await factory.get_workflow_config_async(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return asdict(config)


# Magentic workflow routes (active workflow management)
@no_type_check
@router.post("/workflows/instances", response_model=CreateWorkflowResponse, status_code=201)
async def create_workflow(request: CreateWorkflowRequest) -> CreateWorkflowResponse:
    """
    Create a new Magentic workflow.

    Returns a workflow ID that can be used to execute and monitor the workflow.
    """
    service = get_workflow_service()

    try:
        workflow_id = await service.create_workflow(task=request.task, config=request.config)

        return CreateWorkflowResponse(workflow_id=workflow_id, task=request.task, status="created")
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {e!s}") from None


@no_type_check
@router.get("/workflows/instances/{workflow_id}/stream")
async def stream_workflow(workflow_id: str) -> StreamingResponse:
    """
    Execute workflow with SSE streaming.

    Returns Server-Sent Events (SSE) stream of workflow execution events.
    Events include workflow progress, agent actions, and completion status.

    Event format:
    ```
    data: {"type": "plan_created", "data": {"plan": "..."}}

    data: {"type": "agent_start", "data": {"agent": "researcher", ...}}

    data: {"type": "workflow_complete", "data": {...}}
    ```
    """
    service = get_workflow_service()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from workflow execution."""
        try:
            async for event in service.execute_workflow(workflow_id):
                # Format as SSE
                # SSE format: data: {...}\n\n
                event_json = json.dumps(event)
                yield f"data: {event_json}\n\n"

        except Exception as e:
            logger.error(f"Error in workflow stream: {e}", exc_info=True)
            error_event = json.dumps(
                {
                    "type": "error",
                    "data": {"message": "An internal error occurred while streaming the workflow."},
                }
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@no_type_check
@router.get("/workflows/instances/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Get current status of a workflow.

    Returns workflow execution state including round count,
    current phase, and progress information.
    """
    service = get_workflow_service()

    status = await service.get_workflow_status(workflow_id)

    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return WorkflowStatusResponse(**status)


@no_type_check
@router.get("/workflows/instances", response_model=dict[str, list[dict[str, object]]])
async def list_active_workflows() -> dict[str, list[dict[str, object]]]:
    """
    List all active workflow instances.

    Returns list of workflow status objects for all workflows
    currently tracked by the service.
    """
    service = get_workflow_service()
    workflows = await service.list_workflows()
    return {"workflows": workflows}


@no_type_check
@router.delete("/workflows/instances/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str) -> None:
    """
    Delete a workflow instance.

    Removes workflow from active sessions. Does not cancel
    currently executing workflows.
    """
    service = get_workflow_service()

    deleted = await service.delete_workflow(workflow_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return None


@no_type_check
@router.post("/workflows/instances/{workflow_id}/pause", response_model=WorkflowStatusResponse)
async def pause_workflow(workflow_id: str) -> WorkflowStatusResponse:
    """
    Pause workflow instance execution.

    Note: Requires checkpointing to be enabled.
    """
    service = get_workflow_service()

    status = await service.pause_workflow(workflow_id)

    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return WorkflowStatusResponse(**status)


@no_type_check
@router.post("/workflows/instances/{workflow_id}/resume")
async def resume_workflow(workflow_id: str) -> StreamingResponse:
    """
    Resume paused workflow instance with SSE streaming.

    Returns SSE stream continuing from paused state.
    """
    service = get_workflow_service()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from resumed workflow."""
        try:
            async for event in service.resume_workflow(workflow_id):
                event_json = json.dumps(event)
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(f"Error resuming workflow: {e}", exc_info=True)
            error_event = json.dumps(
                {"type": "error", "data": {"message": "Resume error: An internal error occurred."}}
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# YAML workflow configuration routes (primary - backward compatibility)
# These MUST come before the active workflow routes to match correctly
router.get("/workflows", response_model=dict[str, list[dict[str, object]]])(list_workflows)
router.get("/workflows/{workflow_id}", response_model=dict[str, object])(get_workflow)
