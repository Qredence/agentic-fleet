from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from typing import Any, no_type_check

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.chat.service import get_workflow_service
from agentic_fleet.api.conversations.service import ConversationNotFoundError, get_store

logger = logging.getLogger(__name__)
router = APIRouter()


TRUTHY = {"1", "true", "yes", "on"}
REVEAL_REASONING = os.getenv("STREAM_REASONING", "0").strip().lower() in TRUTHY
STREAM_AGENT_DELTAS = os.getenv("STREAM_AGENT_DELTAS", "1").strip().lower() in TRUTHY


async def _stream_chat_response(req: ChatRequest) -> StreamingResponse:
    """Stream chat response as Server-Sent Events (SSE)."""
    start_time = time.time()
    logger.info(
        f"[CHAT] Starting chat request - conversation_id: {req.conversation_id}, message: {req.message[:50]}..."
    )

    store = get_store()
    workflow_service = get_workflow_service()

    try:
        store.get(req.conversation_id)
    except ConversationNotFoundError as exc:
        logger.error(f"[CHAT] Conversation not found: {req.conversation_id}")
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    store.add_message(req.conversation_id, role="user", content=req.message)
    logger.info(f"[CHAT] User message saved. Elapsed: {time.time() - start_time:.2f}s")

    async def generate_stream() -> AsyncGenerator[str, None]:
        # Send initial keep-alive comment to establish connection
        yield ": keep-alive\n\n"
        # Accumulate global content (legacy single assistant message)
        accumulated_content = ""
        # Per-agent buffers for segmented output
        agent_buffers: dict[str, str] = {}
        # Track orchestrator reasoning messages if enabled
        reasoning_events: list[dict[str, Any]] = []
        workflow_start = time.time()
        logger.info("[CHAT] Getting workflow from cache...")
        workflow = await workflow_service.get_workflow()
        workflow_elapsed = time.time() - workflow_start
        logger.info(f"[CHAT] Workflow retrieved. Elapsed: {workflow_elapsed:.3f}s")

        try:
            # Get workflow events stream
            logger.info("[CHAT] Starting workflow.run()...")
            run_start = time.time()
            events = workflow.run(req.message)
            logger.info(f"[CHAT] workflow.run() returned. Elapsed: {time.time() - run_start:.3f}s")

            event_count = 0
            delta_count = 0
            first_token_time: float | None = None
            last_event_time = time.time()

            async for event in events:
                event_count += 1
                event_time = time.time()
                event_type = event.get("type")
                event_data = event.get("data", {})

                # Log all events for debugging
                logger.info(
                    f"[CHAT] Event #{event_count}: type={event_type}, "
                    f"data_keys={list(event_data.keys()) if isinstance(event_data, dict) else 'N/A'}"
                )

                # Performance metrics
                time_since_last_event = event_time - last_event_time
                if event_count == 1:
                    logger.debug(f"[CHAT] Event #{event_count}: type={event_type} (first event)")
                elif time_since_last_event > 0.5:  # Log slow events (>500ms)
                    logger.warning(
                        f"[CHAT] Event #{event_count}: type={event_type}, "
                        f"time_since_last={time_since_last_event:.3f}s"
                    )
                else:
                    logger.debug(
                        f"[CHAT] Event #{event_count}: type={event_type}, elapsed={time_since_last_event:.3f}s"
                    )

                last_event_time = event_time

                if event_type == "message.delta":
                    delta_count += 1
                    data = event.get("data", {})
                    delta = data.get("delta", "") if isinstance(data, dict) else ""
                    agent_id = data.get("agent_id") if isinstance(data, dict) else None

                    # Only send non-empty deltas to avoid cluttering the stream
                    if delta:
                        accumulated_content += str(delta)
                        if agent_id:
                            agent_buffers.setdefault(agent_id, "")
                            agent_buffers[agent_id] += str(delta)

                        # Track time to first token (TTFT)
                        if first_token_time is None:
                            first_token_time = event_time
                            ttft = first_token_time - start_time
                            logger.info(f"[CHAT] Time to first token (TTFT): {ttft:.3f}s")

                        if (
                            delta_count % 10 == 1 or len(delta) > 50
                        ):  # Log every 10th delta or large deltas
                            elapsed = event_time - start_time
                            logger.info(
                                f"[CHAT] Delta #{delta_count}: {len(delta)} chars, "
                                f"total: {len(accumulated_content)} chars, "
                                f"elapsed: {elapsed:.3f}s"
                            )

                        # Send SSE event with proper type and delta
                        # Frontend expects: {type: "response.delta", delta: "..."}
                        payload: dict[str, Any] = {
                            "type": "response.delta",
                            "delta": str(delta),
                        }
                        if agent_id:
                            payload["agent_id"] = agent_id
                        yield f"data: {json.dumps(payload)}\n\n"
                        # Optional per-agent delta event for finer grained UI segmentation
                        if STREAM_AGENT_DELTAS and agent_id:
                            agent_payload = {
                                "type": "agent.delta",
                                "agent_id": agent_id,
                                "delta": str(delta),
                            }
                            yield f"data: {json.dumps(agent_payload)}\n\n"
                    else:
                        logger.debug(f"[CHAT] Skipping empty delta in event #{event_count}")

                elif event_type == "agent.message.complete":
                    # Agent completed its message - send completion signal to frontend
                    agent_id = event_data.get("agent_id") if isinstance(event_data, dict) else None
                    content = event_data.get("content", "") if isinstance(event_data, dict) else ""
                    # If event has empty content but we buffered per-agent deltas, fallback
                    if not content and agent_id and agent_id in agent_buffers:
                        content = agent_buffers[agent_id]
                    logger.info(f"[CHAT] Agent {agent_id} completed message: {len(content)} chars")

                    # Forward the agent completion event to frontend
                    completion_payload: dict[str, Any] = {
                        "type": "agent.message.complete",
                        "agent_id": agent_id,
                        "content": content,
                    }
                    yield f"data: {json.dumps(completion_payload)}\n\n"
                    # Persist segmented agent message to conversation store (prefix with agent id)
                    if agent_id and content:
                        store.add_message(
                            req.conversation_id,
                            role="assistant",
                            content=f"[{agent_id}] {content}",
                        )

                elif event_type == "message.done":
                    # Extract result from message.done event if present
                    result = event_data.get("result", "") if isinstance(event_data, dict) else ""

                    # Debug: Log the result content
                    if result:
                        logger.debug(f"[CHAT] message.done result preview: {result[:200]}...")
                        logger.debug(
                            f"[CHAT] accumulated_content so far: {len(accumulated_content)} chars"
                        )

                    # If result is provided but no deltas were sent, use the result as final content
                    if result and not accumulated_content:
                        accumulated_content = result
                        logger.info(
                            f"[CHAT] Using result from message.done event: {len(result)} chars"
                        )
                        # Send the result as a delta to the frontend so it can display it
                        result_payload: dict[str, Any] = {
                            "type": "response.delta",
                            "delta": result,
                        }
                        yield f"data: {json.dumps(result_payload)}\n\n"
                    elif result and accumulated_content:
                        logger.warning(
                            f"[CHAT] message.done has result ({len(result)} chars) but accumulated_content "
                            f"already has {len(accumulated_content)} chars - using accumulated_content"
                        )

                    workflow_elapsed = time.time() - workflow_start
                    total_time = time.time() - start_time
                    ttft_str = (
                        f"{first_token_time - start_time:.3f}s" if first_token_time else "N/A"
                    )

                    logger.info(
                        f"[CHAT] Workflow complete. "
                        f"Total events: {event_count}, Total deltas: {delta_count}, "
                        f"Final length: {len(accumulated_content)} chars, "
                        f"TTFT: {ttft_str}, "
                        f"Workflow time: {workflow_elapsed:.3f}s, "
                        f"Total time: {total_time:.3f}s"
                    )

                    # Save final message to store
                    store_save_start = time.time()
                    # Persist final aggregated assistant message (legacy combined output)
                    store.add_message(
                        req.conversation_id, role="assistant", content=accumulated_content
                    )
                    store_save_elapsed = time.time() - store_save_start
                    logger.info(
                        f"[CHAT] Message saved to store. Elapsed: {store_save_elapsed:.3f}s"
                    )

                    # Send completion signal with proper event type
                    # Frontend expects: {type: "response.completed"} or [DONE]
                    completion_payload = {"type": "response.completed"}
                    yield f"data: {json.dumps(completion_payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    logger.info(f"[CHAT] Request complete. Total time: {total_time:.3f}s")
                    break
                elif event_type == "orchestrator.message":
                    # Forward orchestrator reasoning if enabled
                    if REVEAL_REASONING:
                        kind = event_data.get("kind") if isinstance(event_data, dict) else None
                        text = event_data.get("message") if isinstance(event_data, dict) else ""
                        reasoning_payload = {
                            "type": "orchestrator.message",
                            "kind": kind,
                            "message": text,
                        }
                        reasoning_events.append(reasoning_payload)
                        yield f"data: {json.dumps(reasoning_payload)}\n\n"
                        # Persist reasoning as system message for later retrieval
                        if text:
                            store.add_message(
                                req.conversation_id,
                                role="system",
                                content=f"[orchestrator:{kind}] {text}",
                            )
                    else:
                        logger.debug(
                            "[CHAT] Orchestrator message suppressed (STREAM_REASONING disabled)"
                        )
                elif event_type in ("progress", "unknown"):
                    logger.debug(f"[CHAT] Skipping informational event: {event_type}")
                else:
                    logger.warning(f"[CHAT] Unhandled event type: {event_type}")

        except Exception as exc:
            logger.error(f"[CHAT] Error in workflow execution: {exc}", exc_info=True)
            # Send a generic error as SSE event with proper type
            error_payload = {"type": "error", "error": "An internal error occurred"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield "data: [DONE]\n\n"
            logger.error(f"[CHAT] Request failed after {time.time() - start_time:.2f}s")

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def chat(req: ChatRequest, request: Request) -> ChatResponse | StreamingResponse:
    """Handle chat request with optional streaming support."""
    # Check if client wants streaming (via Accept header or stream param)
    accept_header = request.headers.get("accept", "")
    wants_streaming = req.stream or "text/event-stream" in accept_header

    # If streaming is requested, return SSE stream
    if wants_streaming:
        return await _stream_chat_response(req)

    # Otherwise, return standard JSON response
    store = get_store()
    workflow_service = get_workflow_service()

    try:
        store.get(req.conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    store.add_message(req.conversation_id, role="user", content=req.message)

    assistant_message = await workflow_service.execute_workflow(req.message)
    store.add_message(req.conversation_id, role="assistant", content=assistant_message)

    conversation = store.get(req.conversation_id)

    response_messages = [
        ChatMessagePayload(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in conversation.messages
    ]

    return ChatResponse(
        conversation_id=conversation.id,
        message=assistant_message,
        messages=response_messages,
    )


# Use response_model=None to allow both ChatResponse and StreamingResponse
router.post("/chat", response_model=None)(chat)


@no_type_check
@router.get("/chat/stream")
async def chat_stream_get(message: str, conversation_id: str = "default") -> StreamingResponse:
    """GET endpoint for SSE streaming (for testing with EventSource).

    Args:
        message: User message
        conversation_id: Conversation ID (defaults to "default")

    Returns:
        StreamingResponse with SSE events
    """
    req = ChatRequest(message=message, conversation_id=conversation_id, stream=True)
    return await _stream_chat_response(req)
