"""Routes for workflow management."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse

from agentic_fleet.api.chat.service import create_workflow  # type: ignore
from agentic_fleet.api.conversations.service import (
    ConversationNotFoundError,
    get_store,
)
from agentic_fleet.api.exceptions import WorkflowNotFoundError
from agentic_fleet.models.requests import WorkflowRunRequest
from agentic_fleet.utils.factory import get_workflow_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows")


@router.get("")  # type: ignore
async def list_workflows() -> dict[str, Any]:
    """Return metadata for all available workflows."""

    factory = await get_workflow_factory()
    workflows = await factory.list_available_workflows_async()
    return {"workflows": workflows}


@router.get("/{workflow_id}")  # type: ignore
async def get_workflow_config(workflow_id: str) -> dict[str, Any]:
    """Return configuration for a specific workflow."""

    factory = await get_workflow_factory()
    try:
        config = await factory.get_workflow_config_async(workflow_id)
    except ValueError as exc:
        logger.warning("Workflow '%s' not found", workflow_id)
        raise HTTPException(status_code=404, detail="Workflow not found") from exc

    payload = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    return jsonable_encoder(payload)  # type: ignore


@router.post("/{workflow_id}/run")  # type: ignore
async def run_workflow(workflow_id: str, request: WorkflowRunRequest) -> EventSourceResponse:
    """Execute a workflow and stream events."""
    logger.info("Received request to run workflow: %s", workflow_id)
    logger.debug("Request details: %s", request)

    try:
        # Legacy route path: adapt to current WorkflowRunRequest (no files/stream fields)
        workflow = await create_workflow(workflow_id=workflow_id)
    except WorkflowNotFoundError as e:
        logger.warning("Workflow '%s' not found.", workflow_id)
        raise HTTPException(status_code=404, detail="Workflow not found") from e
    except Exception as e:
        logger.exception("Error creating workflow '%s': %s", workflow_id, e)
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    # Provide message payload from request; fallback to empty string satisfies protocol
    event_generator = workflow.run(request)
    return EventSourceResponse(event_generator)


@router.get("/{workflow_id}/conversations/{conversation_id}/messages")  # type: ignore
async def get_messages(workflow_id: str, conversation_id: str) -> list[dict[str, Any]]:
    """Retrieve all messages for a given conversation."""
    logger.info(
        "Fetching messages for workflow '%s' and conversation '%s'",
        workflow_id,
        conversation_id,
    )
    store = get_store()
    try:
        conversation = store.get(conversation_id)
    except ConversationNotFoundError as exc:
        logger.warning(
            "Conversation '%s' not found while accessing workflow '%s'",
            conversation_id,
            workflow_id,
        )
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    logger.debug(
        "Retrieved %d messages for workflow '%s' conversation '%s'",
        len(conversation.messages),
        workflow_id,
        conversation_id,
    )
    return [asdict(message) for message in conversation.messages]
