from __future__ import annotations

from fastapi import APIRouter, Depends, JSONResponse, status

from agenticfleet.api.dependencies import get_backend
from agenticfleet.api.state import BackendState

router = APIRouter(prefix="/v2/workflows", tags=["workflows"])


@router.get("")
async def list_workflows(state: BackendState = Depends(get_backend)) -> JSONResponse:
    workflows = state.workflow_factory.list_available_workflows()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"workflows": workflows})


@router.get("/{workflow_id}")
async def get_workflow_config(
    workflow_id: str,
    state: BackendState = Depends(get_backend),
) -> JSONResponse:
    try:
        config = state.workflow_factory.get_workflow_config(workflow_id)
        return JSONResponse(status_code=status.HTTP_200_OK, content=config.model_dump())
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )


@router.post("/{workflow_id}/create")
async def create_workflow_instance(
    workflow_id: str,
    state: BackendState = Depends(get_backend),
) -> JSONResponse:
    try:
        config = state.workflow_factory.get_workflow_config(workflow_id)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "workflow_id": workflow_id,
                "name": config.name,
                "status": "configuration_loaded",
                "message": "Workflow instance creation not yet implemented",
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )
