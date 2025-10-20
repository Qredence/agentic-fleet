from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from typing import Any
from uuid import uuid4

import tiktoken
from agent_framework import AgentRunResponseUpdate, Role
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agenticfleet import __version__
from agenticfleet.core.approval import ApprovalDecision
from agenticfleet.workflows.workflow_as_agent import create_workflow_agent

# Initialize tracing for FastAPI application
try:
    from agenticfleet.observability import setup_tracing

    setup_tracing()
except Exception:
    # Tracing is optional - continue if it fails
    pass

from .conversations import ConversationStore
from .models import (
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationSummary,
    DiscoveryResponse,
    EntityInfo,
    HealthResponse,
)
from .runtime import FleetRuntime, build_entity_catalog


def create_app() -> FastAPI:
    """Create the FastAPI application used by HaxUI."""

    app = FastAPI(
        title="AgenticFleet HaxUI API",
        version=__version__,
        default_response_class=JSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    runtime = FleetRuntime()
    conversation_store = ConversationStore()
    agent_entities, workflow_entities = build_entity_catalog()
    entity_lookup = {entity["id"]: entity for entity in (*agent_entities, *workflow_entities)}

    def get_runtime() -> FleetRuntime:
        return runtime

    def get_conversation_store() -> ConversationStore:
        return conversation_store

    def get_entity(entity_id: str) -> dict[str, Any]:
        entity = entity_lookup.get(entity_id)
        if entity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found.")
        return entity

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        agents_dir = Path(__file__).resolve().parents[2] / "agents"
        return HealthResponse(status="healthy", version=__version__, agents_dir=str(agents_dir))

    @app.get("/v1/entities", response_model=DiscoveryResponse)
    async def list_entities() -> DiscoveryResponse:
        entities: Iterable[dict[str, Any]] = (*agent_entities, *workflow_entities)
        return DiscoveryResponse(entities=[EntityInfo(**entity) for entity in entities])

    @app.get("/v1/entities/{entity_id}/info", response_model=EntityInfo)
    async def get_entity_info(entity_id: str) -> EntityInfo:
        entity = get_entity(entity_id)
        return EntityInfo(**entity)

    @app.post(
        "/v1/conversations",
        response_model=ConversationSummary,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_conversation(
        payload: dict[str, Any] | None = None,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> ConversationSummary:
        metadata = None
        if payload and isinstance(payload.get("metadata"), dict):
            metadata = {k: str(v) for k, v in payload["metadata"].items()}
        return await store.create(metadata)

    @app.get("/v1/conversations", response_model=ConversationListResponse)
    async def list_conversations(
        store: ConversationStore = Depends(get_conversation_store),
    ) -> ConversationListResponse:
        return await store.list()

    @app.get("/v1/conversations/{conversation_id}", response_model=ConversationSummary)
    async def get_conversation(
        conversation_id: str,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> ConversationSummary:
        try:
            return await store.get(conversation_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )

    @app.delete("/v1/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_conversation(
        conversation_id: str,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> Response:
        await store.delete(conversation_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/v1/conversations/{conversation_id}/items", response_model=ConversationItemsResponse)
    async def list_conversation_items(
        conversation_id: str,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> ConversationItemsResponse:
        try:
            return await store.list_items(conversation_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )

    @app.post("/v1/workflow/reflection")
    async def run_reflection_workflow(
        request: Request,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        """
        Dedicated endpoint for workflow_as_agent (Reflection & Retry pattern).

        This endpoint creates a Worker-Reviewer workflow that iteratively
        improves responses through quality feedback loops.

        Request Body:
            {
                "query": "Your question here",
                "worker_model": "gpt-4.1-nano",  // optional
                "reviewer_model": "gpt-4.1",     // optional
                "conversation_id": "conv_123"    // optional
            }

        Returns:
            Server-Sent Events stream with Worker responses and Reviewer feedback
        """
        payload = await request.json()
        query = payload.get("query")
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid 'query' field.",
            )

        worker_model = payload.get("worker_model", "gpt-4.1-nano")
        reviewer_model = payload.get("reviewer_model", "gpt-4.1")
        conversation_id = payload.get("conversation_id")

        # Create or validate conversation
        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(
                metadata={"workflow": "reflection", "auto_created": "true"}
            )
            conversation_id = summary.id

        # Add user message to conversation
        user_content = [{"type": "text", "text": query}]
        await store.add_message(conversation_id, "user", user_content)

        # Create workflow agent
        agent = create_workflow_agent(worker_model=worker_model, reviewer_model=reviewer_model)

        async def stream_workflow() -> AsyncIterator[bytes]:
            """Stream events from the workflow agent."""
            message_id = f"msg_{uuid4().hex[:12]}"
            sequence_number = 0
            accumulated = ""

            try:
                # Stream events from workflow
                async for event in agent.run_stream(query):
                    sequence_number += 1

                    # Unwrap AgentRunUpdateEvent to get the actual data
                    from agent_framework import AgentRunUpdateEvent

                    actual_event = event.data if isinstance(event, AgentRunUpdateEvent) else event

                    text = getattr(actual_event, "text", None)
                    role_value: str | None = None
                    author_name: str | None = getattr(actual_event, "author_name", None)

                    if isinstance(actual_event, AgentRunResponseUpdate):
                        role_obj = actual_event.role
                        if isinstance(role_obj, Role):
                            role_value = role_obj.value
                    else:
                        text = str(actual_event)

                    raw_text = text if text is not None else str(actual_event)

                    if role_value == Role.ASSISTANT.value:
                        accumulated += raw_text
                        yield format_sse(
                            {
                                "type": "response.output_text.delta",
                                "delta": raw_text,
                                "item_id": message_id,
                                "output_index": 0,
                                "sequence_number": sequence_number,
                                "actor": author_name or "assistant",
                                "role": "assistant",
                            }
                        )
                    else:
                        log_text = raw_text.strip()
                        if not log_text:
                            continue
                        yield format_sse(
                            {
                                "type": "workflow.event",
                                "actor": author_name or "workflow",
                                "text": log_text,
                                "role": role_value or "system",
                                "message_id": message_id,
                                "sequence_number": sequence_number,
                            }
                        )
                        continue

                # Save assistant response to conversation
                assistant_content = [{"type": "text", "text": accumulated}]
                await store.add_message(conversation_id, "assistant", assistant_content)

                # Send completion
                sequence_number += 1
                # Calculate token usage
                try:
                    encoding = tiktoken.encoding_for_model(worker_model)
                    input_tokens = len(encoding.encode(query))
                    output_tokens = len(encoding.encode(accumulated))
                    total_tokens = input_tokens + output_tokens
                except (KeyError, Exception):
                    # Fallback if model encoding not found or other encoding errors
                    input_tokens = None
                    output_tokens = None
                    total_tokens = None

                yield format_sse(
                    {
                        "type": "response.done",
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "sequence_number": sequence_number,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": total_tokens,
                        },
                    }
                )
                yield b"data: [DONE]\n\n"
                yield b"data: [DONE]\n\n"

            except Exception as exc:
                # Log full error internally
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Workflow error: {exc}", exc_info=True)

                # Send generic error to client (prevent information exposure)
                sequence_number += 1
                yield format_sse(
                    {
                        "type": "error",
                        "error": {
                            "type": "workflow_error",
                            "message": "An error occurred during workflow execution",
                        },
                        "sequence_number": sequence_number,
                    }
                )
                yield b"data: [DONE]\n\n"

        return StreamingResponse(stream_workflow(), media_type="text/event-stream")

    @app.post("/v1/responses")
    async def create_response(
        request: Request,
        runtime: FleetRuntime = Depends(get_runtime),
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        payload = await request.json()
        model = payload.get("model")
        if not isinstance(model, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing model field."
            )

        input_payload = extract_input_payload(payload)
        user_text = extract_user_text(payload.get("input"))
        approval_response = extract_approval_response(payload.get("input"))

        conversation_ref = payload.get("conversation")
        conversation_id = None
        if isinstance(conversation_ref, dict):
            conversation_id = conversation_ref.get("id")
        elif isinstance(conversation_ref, str):
            conversation_id = conversation_ref

        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(metadata={"auto_created": "true"})
            conversation_id = summary.id

        # Handle approval response if present
        if approval_response:
            request_id = approval_response.get("request_id")
            if request_id is None:
                raise ValueError("Approval response missing request_id")
            approved = approval_response.get("approved", False)
            decision = ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED

            # Set approval response on the runtime's handler
            await runtime.approval_handler.set_approval_response(request_id, decision)

            # Don't add user message for approval responses - they're control messages
            # Just return success event
            async def approval_ack_stream() -> AsyncIterator[bytes]:
                yield format_sse(
                    {
                        "type": "response.function_approval.responded",
                        "request_id": request_id,
                        "approved": approved,
                        "sequence_number": 1,
                    }
                )
                yield b"data: [DONE]\n\n"

            return StreamingResponse(approval_ack_stream(), media_type="text/event-stream")

        # Regular message - add to conversation
        user_content_blocks: list[dict[str, Any]] = []
        if user_text:
            user_content_blocks.append({"type": "text", "text": user_text})
        elif input_payload:
            user_content_blocks.append({"type": "text", "text": json.dumps(input_payload)})

        if user_content_blocks:
            try:
                await store.add_message(conversation_id, "user", user_content_blocks)
            except KeyError:
                # Conversation was deleted between creation and now - recreate.
                summary = await store.create(metadata={"auto_recreated": "true"})
                conversation_id = summary.id
                await store.add_message(conversation_id, "user", user_content_blocks)

        stream = build_sse_stream(
            runtime=runtime,
            entity_id=model,
            user_text=user_text,
            input_payload=input_payload,
            conversation_id=conversation_id,
            store=store,
        )

        return StreamingResponse(stream, media_type="text/event-stream")

    return app


async def build_sse_stream(
    *,
    runtime: FleetRuntime,
    entity_id: str,
    user_text: str | None,
    input_payload: dict | None,
    conversation_id: str,
    store: ConversationStore,
) -> AsyncIterator[bytes]:
    message_id = f"msg_{uuid4().hex[:12]}"
    sequence_number = 0
    accumulated = ""
    assistant_content: list[dict[str, Any]] = []

    # Task for streaming the agent response
    response_task = asyncio.create_task(
        runtime.generate_response(
            entity_id,
            user_text=user_text,
            input_payload=input_payload,
        )
    )

    # Poll for approvals and stream chunks as they arrive
    emitted_approval_ids: set[str] = set()
    last_heartbeat = time.time()
    heartbeat_interval = 15  # Send heartbeat every 15 seconds

    try:
        # Poll loop: check for approvals or task completion
        while not response_task.done():
            # Send periodic heartbeat to keep connection alive
            current_time = time.time()
            if current_time - last_heartbeat >= heartbeat_interval:
                # SSE comment format keeps connection alive
                yield b": heartbeat\n\n"
                last_heartbeat = current_time

            # Check for pending approval requests
            pending = runtime.approval_handler.get_pending_requests()
            for approval_req in pending:
                req_id = approval_req["request_id"]
                if req_id not in emitted_approval_ids:
                    # Emit approval request event
                    sequence_number += 1
                    yield format_sse(
                        {
                            "type": "response.function_approval.requested",
                            "request_id": req_id,
                            "function_call": {
                                "id": req_id,
                                "name": approval_req["operation_type"],
                                "arguments": approval_req["details"],
                            },
                            "item_id": message_id,
                            "output_index": 0,
                            "sequence_number": sequence_number,
                        }
                    )
                    emitted_approval_ids.add(req_id)

            # Wait briefly before checking again
            await asyncio.sleep(0.1)

        # Task is done - get result
        result, usage = await response_task

        # Stream the result in chunks
        if result:
            chunk_size = 160
            for start in range(0, len(result), chunk_size):
                chunk = result[start : start + chunk_size]
                accumulated += chunk
                assistant_content = [{"type": "text", "text": accumulated}]
                sequence_number += 1
                yield format_sse(
                    {
                        "type": "response.output_text.delta",
                        "delta": chunk,
                        "item_id": message_id,
                        "output_index": 0,
                        "sequence_number": sequence_number,
                    }
                )

        # Send completion event
        event = build_completed_event(
            conversation_id=conversation_id,
            entity_id=entity_id,
            assistant_text=accumulated,
            usage=usage,
            sequence_number=sequence_number + 1,
        )
        yield format_sse(event)
        await append_assistant_message(store, conversation_id, accumulated, assistant_content)
        yield b"data: [DONE]\n\n"

    except Exception as exc:  # pragma: no cover - defensive
        # Log full error internally
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Stream error: {exc}", exc_info=True)

        sequence_number += 1
        error_event = {
            "type": "error",
            "message": "An error occurred during response generation",
            "sequence_number": sequence_number,
        }
        yield format_sse(error_event)
        await append_assistant_message(
            store,
            conversation_id,
            accumulated or "[error] An error occurred",
            [{"type": "text", "text": accumulated or "An error occurred"}],
            status="incomplete",
        )
        yield b"data: [DONE]\n\n"


async def append_assistant_message(
    store: ConversationStore,
    conversation_id: str,
    text: str,
    content_blocks: list[dict[str, Any]],
    *,
    status: str = "completed",
) -> None:
    if not content_blocks and text:
        content_blocks = [{"type": "text", "text": text}]
    try:
        await store.add_message(
            conversation_id,
            "assistant",
            content_blocks or [{"type": "text", "text": ""}],
            status=status,
        )
    except KeyError:
        # Conversation discarded after run; ignore.
        return


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name to get appropriate encoding (default: gpt-4)

    Returns:
        Number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough approximation if encoding not found
        return len(text.split())


def build_completed_event(
    *,
    conversation_id: str,
    entity_id: str,
    assistant_text: str,
    usage: dict[str, Any],
    sequence_number: int,
) -> dict[str, Any]:
    response_id = f"resp_{uuid4().hex[:12]}"
    message_id = f"msg_{uuid4().hex[:12]}"
    created_at = int(time.time())
    return {
        "type": "response.completed",
        "sequence_number": sequence_number,
        "response": {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "model": entity_id,
            "conversation_id": conversation_id,
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": assistant_text,
                            "annotations": [],
                        }
                    ],
                    "id": message_id,
                    "status": "completed",
                }
            ],
            "usage": usage,
            "parallel_tool_calls": False,
            "tool_choice": "none",
            "tools": [],
        },
    }


def format_sse(event: dict[str, Any]) -> bytes:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n".encode()


def extract_input_payload(request_payload: dict[str, Any]) -> dict | None:
    extra_body = request_payload.get("extra_body")
    if isinstance(extra_body, dict):
        input_data = extra_body.get("input_data")
        if isinstance(input_data, dict):
            return input_data
    return None


def extract_user_text(input_param: Any) -> str | None:
    if isinstance(input_param, str):
        return input_param
    if not isinstance(input_param, list):
        return None

    collected: list[str] = []
    for item in input_param:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contents = item.get("content")
        if not isinstance(contents, list):
            continue
        for content_item in contents:
            if isinstance(content_item, dict) and content_item.get("type") == "input_text":
                text = content_item.get("text")
                if isinstance(text, str):
                    collected.append(text)
    if not collected:
        return None
    return "\n\n".join(collected)


def extract_approval_response(input_param: Any) -> dict[str, Any] | None:
    """
    Extract function_approval_response from OpenAI-format input.

    Returns dict with 'request_id', 'approved' keys if found, else None.
    """
    if not isinstance(input_param, list):
        return None

    for item in input_param:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contents = item.get("content")
        if not isinstance(contents, list):
            continue
        for content_item in contents:
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "function_approval_response"
            ):
                return {
                    "request_id": content_item.get("request_id"),
                    "approved": content_item.get("approved", False),
                }
    return None


# Instantiate application for ASGI servers.
app = create_app()
