"""OpenAI-compatible Responses API routes."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agentic_fleet.api.entities.routes import get_entity_discovery
from agentic_fleet.api.exceptions import EntityNotFoundError, ValidationError
from agentic_fleet.api.responses.schemas import ResponseCompleteResponse, ResponseRequest
from agentic_fleet.api.responses.service import ResponseAggregator
from agentic_fleet.models.requests import WorkflowRunRequest
from agentic_fleet.utils.logging import sanitize_for_log
from agentic_fleet.utils.message_classifier import should_use_fast_path
from agentic_fleet.workflow.fast_path import create_fast_path_workflow

# Backward compatibility: tests may use legacy alias "agentic_fleet" instead of "magentic_fleet".
# Provide a normalization helper so streaming requests resolve correctly instead of 404.
_ENTITY_ID_ALIASES = {
    "agentic_fleet": "magentic_fleet",
    "agentic-fleet": "magentic_fleet",
}


def _normalize_entity_id(entity_id: str) -> str:
    """Return canonical workflow ID for legacy aliases."""
    return _ENTITY_ID_ALIASES.get(entity_id, entity_id)


router = APIRouter()


def _build_run_request(input_data: str | dict[str, Any]) -> WorkflowRunRequest:
    """Create a WorkflowRunRequest from the provided input payload."""

    if isinstance(input_data, dict):
        raw_message = input_data.get("input")
        if raw_message is None:
            raw_message = input_data.get("message")

        message = str(raw_message) if raw_message is not None else ""

        metadata = input_data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        context = input_data.get("context")
        if not isinstance(context, dict):
            context = {}

        use_cache_raw = input_data.get("use_cache")
        use_cache = bool(use_cache_raw) if use_cache_raw is not None else True

        conversation_id = input_data.get("conversation_id")
        if conversation_id is not None:
            conversation_id = str(conversation_id)

        correlation_id = input_data.get("correlation_id")
        if correlation_id is not None:
            correlation_id = str(correlation_id)

        return WorkflowRunRequest(
            message=message,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata=metadata,
            context=context,
            use_cache=use_cache,
        )

    return WorkflowRunRequest(message=str(input_data))


async def _stream_response(entity_id: str, input_data: str | dict[str, Any]) -> StreamingResponse:
    """Stream response as Server-Sent Events (SSE).

    Args:
        entity_id: Entity/workflow ID
        input_data: Input message or structured input

    Returns:
        StreamingResponse with SSE events
    """
    run_request = _build_run_request(input_data)
    message = run_request.message

    if not message:
        raise ValidationError("Input message is required")

    # Normalize legacy entity IDs before workflow resolution
    normalized_id = _normalize_entity_id(entity_id)
    if normalized_id != entity_id:
        logging.debug(f"[RESPONSES] Normalized entity_id '{entity_id}' -> '{normalized_id}'")
    entity_id = normalized_id

    discovery = get_entity_discovery()
    try:
        await discovery.get_entity_info_async(entity_id)
    except ValueError as exc:
        raise EntityNotFoundError(entity_id) from exc

    # Check if message should use fast-path once entity existence is confirmed
    use_fast_path = should_use_fast_path(message)
    if use_fast_path:
        logging.info(
            f"[RESPONSES] Using fast-path for simple query: {sanitize_for_log(message)[:100]}"
        )
        workflow = create_fast_path_workflow()
    else:
        workflow = await discovery.get_workflow_instance_async(entity_id)

    # Create aggregator
    aggregator = ResponseAggregator(workflow_id=entity_id, request=run_request)

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream from workflow events."""
        try:
            # Run workflow and get events
            # Unified run signature supports WorkflowRunRequest | str
            events = workflow.run(message) if use_fast_path else workflow.run(run_request)

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
                "error": {
                    "message": "An internal error has occurred.",
                    "type": "execution_error",
                },
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
    # Normalize legacy entity IDs before workflow resolution
    normalized_id = _normalize_entity_id(entity_id)
    if normalized_id != entity_id:
        logging.debug(f"[RESPONSES] Normalized entity_id '{entity_id}' -> '{normalized_id}'")
    entity_id = normalized_id

    run_request = _build_run_request(input_data)
    message = run_request.message

    if not message:
        raise ValidationError("Input message is required")

    discovery = get_entity_discovery()
    try:
        await discovery.get_entity_info_async(entity_id)
    except ValueError as exc:
        raise EntityNotFoundError(entity_id) from exc

    use_fast_path = should_use_fast_path(message)
    if use_fast_path:
        logging.info(
            f"[RESPONSES] Using fast-path for complete response: {sanitize_for_log(message)[:100]}"
        )
        workflow = create_fast_path_workflow()
    else:
        workflow = await discovery.get_workflow_instance_async(entity_id)

    # Create aggregator
    aggregator = ResponseAggregator(workflow_id=entity_id, request=run_request)

    # Consume the workflow stream through the aggregator to reuse identical logic
    events = workflow.run(message) if use_fast_path else workflow.run(run_request)
    async for _ in aggregator.convert_stream(events):
        # Drain the stream - we only care about the aggregated final content
        pass

    final_content = aggregator.get_final_response()
    response_metadata = aggregator.get_response_metadata()
    completion_metadata = aggregator.get_completion_metadata() or {}

    return ResponseCompleteResponse(
        id=f"resp_{int(time.time())}",
        model=entity_id,
        response=final_content,
        created=int(time.time()),
        cached=response_metadata.cached if response_metadata else False,
        conversation_id=response_metadata.conversation_id if response_metadata else None,
        correlation_id=response_metadata.correlation_id if response_metadata else None,
        metadata=completion_metadata or None,
    )


@router.post("/responses", response_model=None)  # type: ignore
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
