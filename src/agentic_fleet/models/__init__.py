"""Data models and Pydantic schemas."""

from __future__ import annotations

from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.entities.schemas import (
    EntityDetailResponse,
    EntityListResponse,
    EntityReloadResponse,
    InputSchema,
)
from agentic_fleet.api.models.workflow_config import WorkflowConfig
from agentic_fleet.api.responses.schemas import (
    ResponseCompleteResponse,
    ResponseDeltaResponse,
    ResponseRequest,
)
from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent

# Backward compatibility aliases
EntityInfo = EntityDetailResponse
DiscoveryResponse = EntityListResponse

__all__ = [
    "ChatMessagePayload",
    "ChatRequest",
    "ChatResponse",
    "DiscoveryResponse",  # Backward compatibility alias
    "EntityDetailResponse",
    "EntityInfo",  # Backward compatibility alias
    "EntityListResponse",
    "EntityReloadResponse",
    "InputSchema",
    "ResponseCompleteResponse",
    "ResponseDeltaResponse",
    "ResponseRequest",
    "RunsWorkflow",
    "WorkflowConfig",
    "WorkflowEvent",
]
