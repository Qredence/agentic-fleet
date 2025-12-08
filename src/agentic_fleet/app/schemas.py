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
    # Base
    "EventCategory",
    "MessageRole",
    "StreamEventType",
    "UIHint",
    "WorkflowStatus",
    # Conversations
    "Conversation",
    "Message",
    # DSPy
    "CacheInfo",
    "CompileRequest",
    "CompileResponse",
    "ReasonerSummary",
    "SignatureInfo",
    # Events
    "StreamEvent",
    # Requests
    "ChatRequest",
    "CreateConversationRequest",
    "RunRequest",
    # Responses
    "AgentInfo",
    "RunResponse",
    # Workflows
    "WorkflowSession",
]
