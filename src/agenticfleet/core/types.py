"""Shared type definitions for AgenticFleet."""

from dataclasses import dataclass
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


@dataclass
class CodeExecutionResult:
    """Result of code execution."""

    success: bool
    output: str
    error: str
    execution_time: float
    language: str
    exit_code: int
