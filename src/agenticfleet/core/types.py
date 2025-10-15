"""Shared type definitions for AgenticFleet."""

from enum import Enum
from typing import Any, TypedDict

from agenticfleet.core.code_types import CodeExecutionResult


class AgentRole(str, Enum):
    """Agent role enumeration."""

    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"


class AgentResponse(TypedDict):
    """Standard agent response structure."""

    content: str
    metadata: dict[str, Any]
    success: bool


# Re-exported for backwards compatibility; prefer importing from
# ``agenticfleet.core.code_types`` for the canonical definition.
__all__ = [
    "AgentRole",
    "AgentResponse",
    "CodeExecutionResult",
]
