from __future__ import annotations

from fastapi import APIRouter, JSONResponse, Request, status

PLACEHOLDER_DETAIL = {
    "detail": (
        "This endpoint is not implemented in the minimal AgenticFleet distribution. "
        "Restore the full backend to enable interactive features."
    )
}

router = APIRouter(tags=["placeholders"])


def _not_implemented() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=PLACEHOLDER_DETAIL)


@router.api_route("/api/chat", methods=["POST"])
async def chat_placeholder(_: Request) -> JSONResponse:
    return _not_implemented()


@router.api_route("/api/chat/stream", methods=["GET"])
async def chat_stream_placeholder(_: Request) -> JSONResponse:
    return _not_implemented()


@router.api_route("/api/approval/{request_id}", methods=["POST"])
async def approval_placeholder(request_id: str, _: Request) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()


@router.api_route("/api/conversations", methods=["GET", "POST"])
async def conversations_placeholder(_: Request) -> JSONResponse:
    return _not_implemented()


@router.api_route("/api/conversations/{conversation_id}", methods=["GET", "DELETE"])
async def conversation_item_placeholder(conversation_id: str, _: Request) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()


@router.api_route("/api/checkpoints", methods=["GET"])
async def checkpoints_placeholder(_: Request) -> JSONResponse:
    return _not_implemented()


@router.api_route("/api/checkpoints/{checkpoint_id}/resume", methods=["POST"])
async def checkpoint_resume_placeholder(checkpoint_id: str, _: Request) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()


@router.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def fallback_placeholder(path: str, _: Request) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()


@router.api_route("/v1/entities", methods=["GET"])
async def entities_placeholder() -> JSONResponse:
    return _not_implemented()


@router.api_route("/v1/entities/{entity_id}/info", methods=["GET"])
async def entity_info_placeholder(entity_id: str) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()


@router.api_route("/v1/workflow/dynamic", methods=["POST"])
async def workflow_dynamic_placeholder(_: Request) -> JSONResponse:
    return _not_implemented()


@router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def v1_fallback_placeholder(path: str, _: Request) -> JSONResponse:  # noqa: ARG001
    return _not_implemented()
