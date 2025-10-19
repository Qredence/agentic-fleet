"""FastAPI backend for HaxUI with workflow_as_agent reflection endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from agent_framework import AgentRunUpdateEvent
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from agenticfleet.haxui.conversations import ConversationStore
from agenticfleet.haxui.models import (
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationSummary,
    DiscoveryResponse,
    HealthResponse,
)
from agenticfleet.haxui.runtime import FleetRuntime, build_entity_catalog

logger = logging.getLogger(__name__)


class ReflectionRequest(BaseModel):
    """Request model for /v1/workflow/reflection endpoint."""

    query: str = Field(..., description="User query to process with reflection pattern")
    worker_model: str = Field(
        default="gpt-4.1-nano", description="Model ID for Worker (response generation)"
    )
    reviewer_model: str = Field(
        default="gpt-4.1", description="Model ID for Reviewer (quality evaluation)"
    )
    conversation_id: str | None = Field(
        default=None, description="Existing conversation to continue (optional)"
    )


class SSEEvent(BaseModel):
    """Server-Sent Event structure."""

    type: str
    data: dict[str, Any] | None = None
    delta: str | None = None
    item_id: str | None = None
    output_index: int | None = None
    sequence_number: int = 0
    conversation_id: str | None = None
    message_id: str | None = None
    usage: dict[str, int] | None = None
    error: dict[str, str] | None = None


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="AgenticFleet HaxUI API",
        description="Backend API for HaxUI with Magentic Fleet and Workflow as Agent support",
        version="0.5.3",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize stores and runtime
    conversation_store = ConversationStore()
    runtime = FleetRuntime()

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize runtime on startup."""
        await runtime.ensure_initialised()
        logger.info("HaxUI API started")

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(version="0.5.3", agents_dir=None)

    @app.get("/v1/entities", response_model=DiscoveryResponse)
    async def list_entities() -> DiscoveryResponse:
        """List available agents and workflows."""
        agents, workflows = build_entity_catalog()
        entities = agents + workflows
        return DiscoveryResponse(entities=entities)

    @app.post("/v1/conversations", response_model=ConversationSummary, status_code=201)
    async def create_conversation(
        metadata: dict[str, str] | None = None,
    ) -> ConversationSummary:
        """Create a new conversation."""
        return await conversation_store.create(metadata=metadata)

    @app.get("/v1/conversations", response_model=ConversationListResponse)
    async def list_conversations() -> ConversationListResponse:
        """List all conversations."""
        return await conversation_store.list()

    @app.get("/v1/conversations/{conversation_id}", response_model=ConversationSummary)
    async def get_conversation(conversation_id: str) -> ConversationSummary:
        """Get a specific conversation."""
        try:
            return await conversation_store.get(conversation_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Conversation not found")

    @app.delete("/v1/conversations/{conversation_id}", status_code=204)
    async def delete_conversation(conversation_id: str) -> None:
        """Delete a conversation."""
        await conversation_store.delete(conversation_id)

    @app.get(
        "/v1/conversations/{conversation_id}/items",
        response_model=ConversationItemsResponse,
    )
    async def list_conversation_items(conversation_id: str) -> ConversationItemsResponse:
        """List items in a conversation."""
        try:
            return await conversation_store.list_items(conversation_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Conversation not found")

    @app.post("/v1/workflow/reflection")
    async def reflection_workflow(request: ReflectionRequest) -> StreamingResponse:
        """
        Execute the reflection workflow with Worker ↔ Reviewer quality assurance.

        This endpoint streams Server-Sent Events (SSE) as the workflow progresses:
        - Worker generates initial response
        - Reviewer evaluates quality (Relevance, Accuracy, Clarity, Completeness)
        - If not approved, Worker regenerates with feedback
        - Iteration continues until approval

        Args:
            request: Reflection request with query and optional model overrides

        Returns:
            StreamingResponse with SSE events

        Raises:
            HTTPException: 400 if query is missing or invalid
            HTTPException: 404 if conversation_id doesn't exist
        """
        # Validate request
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Missing or invalid 'query' field.")

        # Get or create conversation
        conversation_id = request.conversation_id
        if conversation_id:
            try:
                await conversation_store.get(conversation_id)
            except KeyError:
                raise HTTPException(status_code=404, detail="Conversation not found.")
        else:
            conv = await conversation_store.create()
            conversation_id = conv.id

        # Add user message to conversation
        user_content = [{"type": "text", "text": request.query}]
        await conversation_store.add_message(conversation_id, role="user", content=user_content)

        async def generate_sse_stream() -> AsyncIterator[str]:
            """Generate SSE stream from workflow events."""
            sequence_number = 0
            accumulated_text = ""
            message_id = f"msg_{conversation_id}_reflection"

            try:
                # Create workflow agent with specified models
                agent = runtime.get_workflow_as_agent(
                    worker_model=request.worker_model,
                    reviewer_model=request.reviewer_model,
                )

                # Run agent in streaming mode
                async for event in agent.run_stream(request.query):
                    sequence_number += 1

                    # Handle AgentRunUpdateEvent
                    if isinstance(event, AgentRunUpdateEvent):
                        # Extract text from event
                        text_content = ""
                        if hasattr(event.data, "text") and event.data.text:
                            text_content = event.data.text
                        elif hasattr(event.data, "contents"):
                            for content in event.data.contents:
                                if hasattr(content, "text"):
                                    text_content += content.text

                        # Stream as delta if we have text
                        if text_content:
                            accumulated_text += text_content
                            sse_event = SSEEvent(
                                type="response.output_text.delta",
                                delta=text_content,
                                item_id=message_id,
                                output_index=0,
                                sequence_number=sequence_number,
                            )
                            yield f"data: {sse_event.model_dump_json()}\n\n"

                # Send completion event
                sequence_number += 1
                completion_event = SSEEvent(
                    type="response.done",
                    conversation_id=conversation_id,
                    message_id=message_id,
                    sequence_number=sequence_number,
                    usage={
                        "input_tokens": len(request.query.split()),
                        "output_tokens": len(accumulated_text.split()),
                        "total_tokens": len(request.query.split()) + len(accumulated_text.split()),
                    },
                )
                yield f"data: {completion_event.model_dump_json()}\n\n"

                # Add assistant message to conversation
                assistant_content = [{"type": "text", "text": accumulated_text}]
                await conversation_store.add_message(
                    conversation_id, role="assistant", content=assistant_content
                )

                # Send final done marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in reflection workflow: {e}", exc_info=True)
                sequence_number += 1
                error_event = SSEEvent(
                    type="error",
                    error={"type": "workflow_error", "message": str(e)},
                    sequence_number=sequence_number,
                )
                yield f"data: {error_event.model_dump_json()}\n\n"

        return StreamingResponse(
            generate_sse_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
