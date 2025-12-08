"""Pydantic schemas for the AgenticFleet API.

DEPRECATED: This module is maintained for backward compatibility only.
All models have been reorganized into the models/ directory.

New code should import directly from agentic_fleet.app.models instead.
"""

# Re-export all models from the new models/ directory for backward compatibility
from agentic_fleet.app.models import (
    AgentInfo,
    CacheInfo,
    ChatRequest,
    CompileRequest,
    CompileResponse,
    Conversation,
    CreateConversationRequest,
    EventCategory,
    Message,
    MessageRole,
    ReasonerSummary,
    RunRequest,
    RunResponse,
    SignatureInfo,
    StreamEvent,
    StreamEventType,
    UIHint,
    WorkflowSession,
    WorkflowStatus,
)

__all__ = [
    # Responses
    "AgentInfo",
    # DSPy
    "CacheInfo",
    # Requests
    "ChatRequest",
    "CompileRequest",
    "CompileResponse",
    # Conversations
    "Conversation",
    "CreateConversationRequest",
    # Base
    "EventCategory",
    "Message",
    "MessageRole",
    "ReasonerSummary",
    "RunRequest",
    "RunResponse",
    "SignatureInfo",
    # Events
    "StreamEvent",
    "StreamEventType",
    "UIHint",
    # Workflows
    "WorkflowSession",
    "WorkflowStatus",
]
