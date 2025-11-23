"""API models for agentic-fleet."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Core Models
class WorkflowRunRequest(BaseModel):
    """Request model for running a workflow."""

    workflow_id: str = Field(..., description="ID of the workflow to run", min_length=1)
    inputs: dict[str, Any] | None = Field(default=None, description="Optional workflow inputs")
    verbose: bool = Field(default=False, description="Enable verbose logging")

    model_config = ConfigDict(extra="forbid")


class WorkflowRunResponse(BaseModel):
    """Response model for a workflow run."""

    run_id: str
    status: WorkflowStatus
    output: dict[str, Any] | None = None


class HistoryQuery(BaseModel):
    """Query parameters for history retrieval."""

    all: bool | None = None
    summary: bool | None = None
    executions: bool | None = None
    last_n: int | None = Field(None, ge=1, le=1000)
    routing: bool | None = None
    agents: bool | None = None
    timing: bool | None = None


class HistoryResponse(BaseModel):
    """Response model for history retrieval."""

    runs: list[dict[str, Any]]


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogQuery(BaseModel):
    """Query parameters for log retrieval."""

    run_id: str | None = None
    level: LogLevel | None = None
    agent_id: str | None = None


class LogResponse(BaseModel):
    """Response model for log retrieval."""

    logs: list[dict[str, Any]]


# Optimization/Agent models kept for compatibility if needed, but not strictly required by new schema
# I will keep them if they are used by other parts of the system, but distinct from the requested schema.
class AgentInfo(BaseModel):
    """Information about an agent."""

    name: str
    description: str
    model: str
    capabilities: list[str]
    status: str


class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: list[AgentInfo]


# Self-Improvement Models
class SelfImprovementRequest(BaseModel):
    """Request model for self-improvement."""

    min_quality_score: float = Field(
        8.0,
        ge=0.0,
        le=10.0,
        description="Minimum quality score to consider an execution for learning",
    )
    max_examples: int = Field(20, ge=1, description="Maximum number of new examples to generate")
    lookback: int = Field(100, ge=1, description="Number of recent executions to analyze")
    force_recompile: bool = Field(
        True, description="Whether to force DSPy recompilation after adding examples"
    )


class ImprovementStats(BaseModel):
    """Statistics for self-improvement."""

    total_executions: int
    high_quality_executions: int
    potential_new_examples: int
    average_quality_score: float
    quality_score_distribution: dict[str, int]


class SelfImprovementResponse(BaseModel):
    """Response model for self-improvement."""

    added_examples: int
    status: str
