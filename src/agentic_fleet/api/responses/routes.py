"""OpenAI-compatible Responses API routes."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, no_type_check

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from agentic_fleet.api.entities.routes import get_entity_discovery
from agentic_fleet.api.responses.schemas import ResponseCompleteResponse, ResponseRequest
from agentic_fleet.api.responses.service import ResponseAggregator
from agentic_fleet.utils.logging import sanitize_for_log

router = APIRouter()


async def _stream_response(entity_id: str, input_data: str | dict[str, Any]) -> StreamingResponse:
    """Stream response as Server-Sent Events (SSE).

    Args:
        entity_id: Entity/workflow ID
        input_data: Input message or structured input

    Returns:
        StreamingResponse with SSE events
    """
    discovery = get_entity_discovery()

    # Get workflow instance
    try:
        workflow = await discovery.get_workflow_instance_async(entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found") from exc

    # Convert input to string if needed
    # Extract message from structured input or cast to string
    message = input_data.get("input", "") if isinstance(input_data, dict) else str(input_data)

    if not message:
        raise HTTPException(status_code=400, detail="Input message is required")

    # Create aggregator
    aggregator = ResponseAggregator()

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream from workflow events."""
        try:
            # Run workflow and get events
            events = workflow.run(message)

            # Convert events to OpenAI-compatible SSE format
            async for sse_line in aggregator.convert_stream(events):
                yield sse_line
        except Exception:
            # Log the actual error message and stack trace on the server
            logging.exception(
                "Error in response stream for entity '%s'", sanitize_for_log(entity_id)
            )
            # Send generic error message to client as SSE event
            error_event = {
                "type": "error",
                "error": {"message": "An internal error has occurred.", "type": "execution_error"},
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def _get_complete_response(
    entity_id: str, input_data: str | dict[str, Any]
) -> ResponseCompleteResponse:
    """Get complete response without streaming.

    Args:
        entity_id: Entity/workflow ID
        input_data: Input message or structured input

    Returns:
        ResponseCompleteResponse with complete response
    """
    discovery = get_entity_discovery()

    # Get workflow instance
    try:
        workflow = await discovery.get_workflow_instance_async(entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found") from exc

    # Convert input to string if needed
    message = input_data.get("input", "") if isinstance(input_data, dict) else str(input_data)

    if not message:
        raise HTTPException(status_code=400, detail="Input message is required")

    # Create aggregator
    aggregator = ResponseAggregator()

    # Consume the workflow stream through the aggregator to reuse identical logic
    events = workflow.run(message)
    async for _ in aggregator.convert_stream(events):
        # Drain the stream - we only care about the aggregated final content
        pass

    final_content = aggregator.get_final_response()

    return ResponseCompleteResponse(
        id=f"resp_{int(time.time())}",
        model=entity_id,
        response=final_content,
        created=int(time.time()),
    )


@no_type_check
@router.post("/responses", response_model=None)
async def create_response(
    req: ResponseRequest, request: Request
) -> StreamingResponse | ResponseCompleteResponse:
    """Create a response using OpenAI-compatible Responses API.

    Args:
        req: Response request with model (entity_id), input, and stream flag
        request: FastAPI request object

    Returns:
        StreamingResponse if streaming, ResponseCompleteResponse otherwise

    Raises:
        HTTPException: If entity not found or input invalid
    """
    # Check if client wants streaming (via Accept header or stream param)
    accept_header = request.headers.get("accept", "")
    wants_streaming = req.stream or "text/event-stream" in accept_header

    if wants_streaming:
        return await _stream_response(req.model, req.input)
    else:
        return await _get_complete_response(req.model, req.input)
