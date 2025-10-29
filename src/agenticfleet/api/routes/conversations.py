from __future__ import annotations

import logging
from json import JSONDecodeError

from fastapi import APIRouter, Depends, JSONResponse, Request, Response, status

from agenticfleet.api.dependencies import get_backend
from agenticfleet.api.state import BackendState

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])
LOGGER = logging.getLogger(__name__)


@router.api_route("", methods=["GET", "POST"])
async def conversations_v1(
    request: Request,
    state: BackendState = Depends(get_backend),
) -> JSONResponse:
    if request.method == "GET":
        return JSONResponse(status_code=status.HTTP_200_OK, content={"data": state.conversation_store.list()})

    try:
        payload = await request.json()
    except (JSONDecodeError, ValueError):
        LOGGER.warning("Invalid JSON payload while creating conversation", exc_info=True)
        payload = {}

    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    record = state.conversation_store.create(metadata=metadata if isinstance(metadata, dict) else None)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=record)


@router.api_route("/{conversation_id}", methods=["GET", "DELETE"])
async def conversations_v1_item(
    conversation_id: str,
    request: Request,
    state: BackendState = Depends(get_backend),
) -> Response:
    if request.method == "GET":
        record = state.conversation_store.get(conversation_id)
        if record is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Conversation not found"},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content=record)

    deleted = state.conversation_store.delete(conversation_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Conversation not found"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/items")
async def conversations_v1_items(
    conversation_id: str,
    state: BackendState = Depends(get_backend),
) -> JSONResponse:
    items = state.conversation_store.list_items(conversation_id)
    if items is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Conversation not found"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"data": items})
