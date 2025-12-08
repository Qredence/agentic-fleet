"""AgenticFleet API models.

Re-exports all model classes for backward compatibility.
"""

# Base models and enums
from .base import EventCategory, MessageRole, StreamEventType, UIHint, WorkflowStatus

# Conversation models
from .conversations import Conversation, Message

# DSPy models
from .dspy import CacheInfo, CompileRequest, CompileResponse, ReasonerSummary, SignatureInfo

# Event models
from .events import StreamEvent

# Request models
from .requests import ChatRequest, CreateConversationRequest, RunRequest

# Response models
from .responses import AgentInfo, RunResponse

# Workflow models
from .workflows import WorkflowSession

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
