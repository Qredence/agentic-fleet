"""OpenAI Responses API request and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResponseRequest(BaseModel):
    """Request schema for OpenAI-compatible Responses API."""

    model: str = Field(description="Entity ID (workflow ID) to use")
    input: str | dict[str, Any] = Field(description="Input message or structured input")
    stream: bool = Field(default=True, description="Whether to stream the response")


class ResponseDeltaResponse(BaseModel):
    """Delta response in streaming mode."""

    delta: str = Field(description="Delta text content")


class ResponseCompleteResponse(BaseModel):
    """Complete response in non-streaming mode."""

    id: str = Field(description="Response ID")
    model: str = Field(description="Model/entity ID used")
    response: str = Field(description="Complete response text")
    created: int = Field(description="Unix timestamp")
    cached: bool = Field(default=False, description="Whether the response was served from cache")
    conversation_id: str | None = Field(
        default=None, description="Conversation identifier associated with the response"
    )
    correlation_id: str | None = Field(
        default=None, description="Tracing correlation identifier for the response"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata captured during response execution"
    )


# --- Streaming event models (merged from models.py) --- #


class ResponseDelta(BaseModel):
    """Delta content in a streaming response."""

    content: str = Field(default="", description="Delta text content")
    agent_id: str | None = Field(default=None, description="Agent ID that generated this delta")
    cached: bool | None = Field(default=None, description="Whether the delta came from cache")


class ResponseDeltaEvent(BaseModel):
    """Event emitted during streaming response following OpenAI Responses API format."""

    type: str = Field(default="response.delta", description="Event type")
    delta: ResponseDelta = Field(description="Delta content")


class ResponseMessage(BaseModel):
    """Complete response message."""

    role: str = Field(default="assistant", description="Message role")
    content: str = Field(description="Message content")


class ResponseCompletedEvent(BaseModel):
    """Event emitted when response is completed following OpenAI Responses API format."""

    type: str = Field(default="response.completed", description="Event type")
    response: ResponseMessage = Field(description="Completed response")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata about the completed response"
    )


class OrchestratorMessageEvent(BaseModel):
    """Event for orchestrator/manager messages."""

    type: str = Field(default="orchestrator.message", description="Event type")
    message: str = Field(description="Orchestrator message text")
    kind: str | None = Field(default=None, description="Message kind (plan, replan, etc.)")
