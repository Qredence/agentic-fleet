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
