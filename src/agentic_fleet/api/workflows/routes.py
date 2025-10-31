from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.workflow_factory import WorkflowFactory

router = APIRouter()


def list_workflows() -> dict[str, list[dict[str, object]]]:
    """Return all workflows available in the YAML configuration."""

    factory = WorkflowFactory()
    return {"workflows": factory.list_available_workflows()}


def get_workflow(workflow_id: str) -> dict[str, object]:
    """Return detailed configuration for a specific workflow."""

    factory = WorkflowFactory()
    try:
        config = factory.get_workflow_config(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return asdict(config)


router.get("/workflows")(list_workflows)
router.get("/workflows/{workflow_id}")(get_workflow)
