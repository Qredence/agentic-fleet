"""Shared type definitions for AgenticFleet."""

from enum import Enum
from typing import Any, TypedDict


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
