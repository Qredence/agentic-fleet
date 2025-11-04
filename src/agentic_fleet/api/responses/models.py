"""OpenAI Responses API compatible models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResponseDelta(BaseModel):
    """Delta content in a streaming response."""

    content: str = Field(default="", description="Delta text content")
    agent_id: str | None = Field(default=None, description="Agent ID that generated this delta")


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


class OrchestratorMessageEvent(BaseModel):
    """Event for orchestrator/manager messages."""

    type: str = Field(default="orchestrator.message", description="Event type")
    message: str = Field(description="Orchestrator message text")
    kind: str | None = Field(default=None, description="Message kind (plan, replan, etc.)")
