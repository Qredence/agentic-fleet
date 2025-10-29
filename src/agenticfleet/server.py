"""Minimal FastAPI server exposing placeholder endpoints for the frontend."""

from __future__ import annotations

import asyncio
import builtins
import json
import logging
import threading
import time
from collections.abc import AsyncIterator
from json import JSONDecodeError
from typing import Any
from uuid import uuid4

from agent_framework.exceptions import ServiceInitializationError, ServiceResponseException
from agent_framework.openai import OpenAIResponsesClient
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agenticfleet import __version__

PLACEHOLDER_DETAIL = {
    "detail": (
        "This endpoint is not implemented in the minimal AgenticFleet distribution. "
        "Restore the full backend to enable interactive features."
    )
}


class InMemoryConversationStore:
    """Simple in-memory conversation storage compatible with frontend expectations."""

    def __init__(self) -> None:
        self._conversations: dict[str, dict[str, Any]] = {}
        self._items: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._next_id = 1

    @staticmethod
    def _clone_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            **item,
            "content": [block.copy() for block in item.get("content", [])],
        }

    def _generate_id(self) -> str:
        conversation_id = f"conv-{self._next_id:06d}"
        self._next_id += 1
        return conversation_id

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(metadata, dict):
            return {}

        sanitized: dict[str, str] = {}
        for key, value in metadata.items():
            if not isinstance(key, str):
                key = str(key)
            if value is None:
                sanitized[key] = ""
            elif isinstance(value, str):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def _clone(record: dict[str, Any]) -> dict[str, Any]:
        return {**record, "metadata": {**record.get("metadata", {})}}

    def create(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        sanitized_metadata = self._sanitize_metadata(metadata)
        conversation_id = self._generate_id()
        timestamp = self._now()
        record = {
            "id": conversation_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "metadata": sanitized_metadata,
        }

        with self._lock:
            self._conversations[conversation_id] = record
            self._items[conversation_id] = []

        return self._clone(record)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        sanitized_content: list[dict[str, Any]] = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    sanitized_content.append(block.copy())
                else:
                    sanitized_content.append({"type": "text", "text": str(block)})

        item = {
            "id": f"item-{uuid4().hex[:12]}",
            "role": role,
            "content": sanitized_content,
            "created_at": self._now(),
        }

        with self._lock:
            conversation = self._conversations.get(conversation_id)
            if conversation is None:
                raise KeyError(conversation_id)
            conversation["updated_at"] = item["created_at"]
            self._items.setdefault(conversation_id, []).append(item)

        return self._clone_item(item)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            records = [self._clone(record) for record in self._conversations.values()]

        return sorted(records, key=lambda record: record["updated_at"], reverse=True)

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._conversations.get(conversation_id)
            if record is None:
                return None
            return self._clone(record)

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            conversation_removed = self._conversations.pop(conversation_id, None)
            self._items.pop(conversation_id, None)
        return conversation_removed is not None

    def list_items(self, conversation_id: str) -> builtins.list[dict[str, Any]] | None:
        with self._lock:
            if conversation_id not in self._conversations:
                return None
            items = self._items.get(conversation_id, [])
            return [self._clone_item(item) for item in items]


LOGGER = logging.getLogger(__name__)

DEFAULT_RESPONSES_MODEL = "gpt-5-mini"
ASSISTANT_INSTRUCTION = (
    "You are the AgenticFleet assistant. Provide concise, accurate updates about the "
    "multi-agent orchestration system, highlighting how the manager coordinates the "
    "researcher, coder, and reviewer agents with dynamic spawning and human-in-the-loop approvals."
)
FALLBACK_SUMMARY = (
    "AgenticFleet is a multi-agent orchestration framework that unites a planning manager with "
    "specialist researcher, coder, and reviewer agents. It supports dynamic agent spawning, "
    "human-in-the-loop approvals, checkpointing, and detailed observability so teams can tackle "
    "complex tasks reliably."
)


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


async def _build_assistant_reply(user_text: str | None) -> tuple[str, str, dict[str, int | None]]:
    prompt = (user_text or "Provide a concise overview of AgenticFleet for a new user.").strip()
    request_payload = (
        f"{ASSISTANT_INSTRUCTION}\n\n"
        "Summarise the following request with actionable highlights about AgenticFleet's "
        "architecture, dynamic agent spawning, and human-in-the-loop safeguards."
        f"\n\nRequest:\n{prompt}"
    )

    usage: dict[str, int | None] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    try:
        client = OpenAIResponsesClient(model_id=DEFAULT_RESPONSES_MODEL)
        response = await client.get_response(request_payload)
        text = (response.text or "").strip()
        if not text and response.messages:
            text = "\n".join(msg.text for msg in response.messages if getattr(msg, "text", ""))
        if not text:
            text = FALLBACK_SUMMARY

        if response.usage_details:
            usage = {
                "input_tokens": response.usage_details.input_token_count,
                "output_tokens": response.usage_details.output_token_count,
                "total_tokens": response.usage_details.total_token_count,
            }

        return text, response.model_id or DEFAULT_RESPONSES_MODEL, usage
    except (ServiceInitializationError, ServiceResponseException) as exc:
        LOGGER.exception(
            "OpenAI Responses client failed (%s); falling back to static summary",
            exc,
            exc_info=True,
        )
        fallback = FALLBACK_SUMMARY
        if user_text:
            fallback = (
                f"{fallback}\n\nI wasn't able to reach the model for this specific request, but here's a "
                "refresher on AgenticFleet. Your original prompt was: "
                f"{user_text.strip()}"
            )
        return fallback, DEFAULT_RESPONSES_MODEL, usage
    except Exception as exc:  # pragma: no cover - guard for unexpected client errors
        LOGGER.exception("Unexpected error while generating assistant reply", exc_info=True)
        fallback = FALLBACK_SUMMARY
        if user_text:
            fallback = (
                f"{fallback}\n\nWe encountered an unexpected issue while processing your request: {exc}."
                f"\nOriginal prompt: {user_text.strip()}"
            )
        return fallback, DEFAULT_RESPONSES_MODEL, usage


def _format_sse_event(event: dict[str, Any]) -> bytes:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n".encode()


def _not_implemented() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=PLACEHOLDER_DETAIL)


def create_app() -> FastAPI:
    app = FastAPI(title="AgenticFleet Minimal API", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": "AgenticFleet Minimal API", "version": __version__, "status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health")
    async def api_health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/info")
    async def api_info() -> dict[str, str]:
        return {"name": "AgenticFleet", "version": __version__, "mode": "minimal"}

    # Legacy API surface used by the trimmed frontend ---------------------

    conversation_store = InMemoryConversationStore()

    # Legacy API surface used by the trimmed frontend ---------------------

    @app.api_route("/api/chat", methods=["POST"])
    async def chat_placeholder(_: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/chat/stream", methods=["GET"])
    async def chat_stream_placeholder(_: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/approval/{request_id}", methods=["POST"])
    async def approval_placeholder(request_id: str, _: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/conversations", methods=["GET", "POST"])
    async def conversations_placeholder(_: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/conversations/{conversation_id}", methods=["GET", "DELETE"])
    async def conversation_item_placeholder(conversation_id: str, _: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/checkpoints", methods=["GET"])
    async def checkpoints_placeholder(_: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/checkpoints/{checkpoint_id}/resume", methods=["POST"])
    async def checkpoint_resume_placeholder(checkpoint_id: str, _: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def fallback_placeholder(path: str, _: Request) -> JSONResponse:
        return _not_implemented()

    # v1 API surface (Human Approval + Conversations + Entities) ----------

    @app.api_route("/v1/entities", methods=["GET"])
    async def entities_placeholder() -> JSONResponse:
        return _not_implemented()

    @app.api_route("/v1/entities/{entity_id}/info", methods=["GET"])
    async def entity_info_placeholder(entity_id: str) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/v1/conversations", methods=["GET", "POST"])
    async def conversations_v1(request: Request) -> JSONResponse:
        if request.method == "GET":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"data": conversation_store.list()},
            )

        try:
            payload = await request.json()
        except (JSONDecodeError, ValueError):
            payload = {}

        metadata = payload.get("metadata") if isinstance(payload, dict) else None
        record = conversation_store.create(
            metadata=metadata if isinstance(metadata, dict) else None
        )
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=record)

    @app.api_route("/v1/conversations/{conversation_id}", methods=["GET", "DELETE"])
    async def conversations_v1_item(conversation_id: str, request: Request) -> Response:
        if request.method == "GET":
            record = conversation_store.get(conversation_id)
            if record is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": "Conversation not found"},
                )
            return JSONResponse(status_code=status.HTTP_200_OK, content=record)

        deleted = conversation_store.delete(conversation_id)
        if not deleted:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Conversation not found"},
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.api_route(
        "/v1/conversations/{conversation_id}/items",
        methods=["GET"],
    )
    async def conversations_v1_items(conversation_id: str) -> JSONResponse:
        items = conversation_store.list_items(conversation_id)
        if items is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Conversation not found"},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"data": items})

    @app.post("/v1/responses")
    async def responses_v1(request: Request) -> StreamingResponse:
        try:
            payload = await request.json()
        except (JSONDecodeError, ValueError):
            return StreamingResponse(
                iter((b'data: {"type": "error", "message": "Invalid JSON payload"}\n\n',)),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="text/event-stream",
            )

        requested_model = payload.get("model")
        if not isinstance(requested_model, str) or not requested_model:
            requested_model = "dynamic_orchestration"

        conversation_id = _extract_conversation_id(payload) or ""
        if conversation_id and conversation_store.get(conversation_id) is None:
            conversation_id = ""

        if not conversation_id:
            record = conversation_store.create(metadata={"auto_created": "true"})
            conversation_id = record["id"]

        user_text = _extract_user_text(payload.get("input"))
        if user_text:
            conversation_store.add_message(
                conversation_id,
                "user",
                [{"type": "input_text", "text": user_text}],
            )

        async def event_stream() -> AsyncIterator[bytes]:
            message_id = f"msg-{uuid4().hex[:12]}"
            sequence_number = 1

            workflow_event = {
                "type": "workflow.event",
                "actor": "Orchestrator",
                "text": (
                    "Plan:\n"
                    "- Understand the latest request\n"
                    f"- Query {DEFAULT_RESPONSES_MODEL} for an AgenticFleet-focused answer\n"
                    "- Stream the summary back to the conversation"
                ),
                "role": "manager",
                "message_id": message_id,
                "sequence_number": sequence_number,
            }
            yield _format_sse_event(workflow_event)

            await asyncio.sleep(0)

            assistant_text, resolved_model, usage = await _build_assistant_reply(user_text)
            assistant_text = assistant_text.strip()
            if not assistant_text:
                assistant_text = FALLBACK_SUMMARY

            sequence_number += 1
            delta_event = {
                "type": "response.output_text.delta",
                "delta": assistant_text,
                "item_id": message_id,
                "output_index": 0,
                "sequence_number": sequence_number,
                "actor": "Assistant",
                "role": "assistant",
            }
            yield _format_sse_event(delta_event)

            conversation_store.add_message(
                conversation_id,
                "assistant",
                [{"type": "output_text", "text": assistant_text}],
            )

            await asyncio.sleep(0)

            sequence_number += 1
            completion_event = {
                "type": "response.completed",
                "sequence_number": sequence_number,
                "response": {
                    "id": message_id,
                    "model": resolved_model or requested_model,
                    "usage": usage,
                    "conversation_id": conversation_id,
                },
            }
            yield _format_sse_event(completion_event)

            yield b"data: [DONE]\n\n"

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)

    @app.api_route("/v1/approvals", methods=["GET"])
    async def approvals_placeholder() -> JSONResponse:
        return _not_implemented()

    @app.api_route("/v1/approvals/{request_id}", methods=["POST"])
    async def approvals_item_placeholder(request_id: str, _: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/v1/workflow/dynamic", methods=["POST"])
    async def workflow_dynamic_placeholder(_: Request) -> JSONResponse:
        return _not_implemented()

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def v1_fallback_placeholder(path: str, _: Request) -> JSONResponse:
        return _not_implemented()

    return app


app = create_app()
