from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from agenticfleet.api.dependencies import get_backend
from agenticfleet.api.services.workflow_executor import format_sse_event
from agenticfleet.api.state import BackendState

router = APIRouter(tags=["legacy"])
LOGGER = logging.getLogger(__name__)


def _extract_conversation_id(payload: dict[str, Any]) -> str | None:
    conversation = payload.get("conversation")
    if isinstance(conversation, str) and conversation:
        return conversation
    if isinstance(conversation, dict):
        identifier = conversation.get("id")
        if isinstance(identifier, str) and identifier:
            return identifier
    return None


def _extract_user_text(input_payload: Any) -> str | None:
    if isinstance(input_payload, str):
        return input_payload

    if not isinstance(input_payload, list):
        return None

    collected: list[str] = []
    for item in input_payload:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contents = item.get("content")
        if not isinstance(contents, list):
            continue
        for block in contents:
            if isinstance(block, dict) and block.get("type") == "input_text":
                text = block.get("text")
                if isinstance(text, str):
                    collected.append(text)
    if not collected:
        return None
    return "\n\n".join(collected)


@router.post("/v1/responses")
async def responses_v1_legacy(
    request: Request,
    state: BackendState = Depends(get_backend),
) -> StreamingResponse:
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    conversation_store = state.conversation_store
    conversation_id = _extract_conversation_id(payload) or conversation_store.create()["id"]
    user_text = _extract_user_text(payload.get("input", payload))

    conversation_store.add_message(
        conversation_id,
        "user",
        content=[{"type": "input_text", "text": user_text or ""}],
    )

    async def event_stream() -> AsyncGenerator[bytes, None]:
        yield format_sse_event({"type": "workflow.event", "data": {"workflow": "legacy"}})
        await asyncio.sleep(0)

        combined = (
            "AgenticFleet — overview: manager + agents\n\n"
            "It supports dynamic spawning, checkpointing, and HITL approvals."
        )
        try:
            conversation_store.add_message(
                conversation_id,
                "assistant",
                content=[{"type": "output_text", "text": combined}],
            )
        except Exception:  # pragma: no cover - best effort history persistence
            LOGGER.exception("Failed to append assistant message to conversation history")

        yield format_sse_event({"type": "response.output_text.delta", "text": combined})
        await asyncio.sleep(0)

        completed = {
            "type": "response.completed",
            "response": {"conversation_id": conversation_id},
        }
        yield format_sse_event(completed)
        await asyncio.sleep(0)

        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
