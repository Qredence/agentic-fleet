"""AgenticFleet API models.

Re-exports all model classes for backward compatibility.
"""

# Base models and enums
from .base import EventCategory, MessageRole, StreamEventType, UIHint, WorkflowStatus

# Conversation models
from .conversations import Conversation, Message

# DSPy models
from .dspy import (
    CacheInfo,
    CompileRequest,
    CompileResponse,
    OptimizationJobStatus,
    ReasonerSummary,
    SelfImproveRequest,
    SelfImproveResponse,
    SignatureInfo,
)

# Event models
from .events import StreamEvent

# Request models
from .requests import ChatRequest, CreateConversationRequest, RunRequest, WorkflowResumeRequest

# Response models
from .responses import AgentInfo, RunResponse

# Workflow models
from .workflows import WorkflowSession

__all__ = [
    "AgentInfo",
    "CacheInfo",
    "ChatRequest",
    "CompileRequest",
    "CompileResponse",
    "Conversation",
    "CreateConversationRequest",
    "EventCategory",
    "Message",
    "MessageRole",
    "OptimizationJobStatus",
    "ReasonerSummary",
    "RunRequest",
    "RunResponse",
    "SelfImproveRequest",
    "SelfImproveResponse",
    "SignatureInfo",
    "StreamEvent",
    "StreamEventType",
    "UIHint",
    "WorkflowResumeRequest",
    "WorkflowSession",
    "WorkflowStatus",
]
