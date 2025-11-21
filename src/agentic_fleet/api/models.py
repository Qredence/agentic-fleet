from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# Core Models
class WorkflowRunRequest(BaseModel):
    workflow_id: str = Field(..., description="ID of the workflow to run")
    inputs: dict[str, Any] | None = Field(default=None, description="Optional workflow inputs")
    verbose: bool = Field(default=False, description="Enable verbose logging")


class WorkflowRunResponse(BaseModel):
    run_id: str
    status: str
    output: dict[str, Any] | None = None


class HistoryQuery(BaseModel):
    all: bool | None = None
    summary: bool | None = None
    executions: bool | None = None
    last_n: int | None = None
    routing: bool | None = None
    agents: bool | None = None
    timing: bool | None = None


class HistoryResponse(BaseModel):
    runs: list[dict[str, Any]]


class LogQuery(BaseModel):
    run_id: str | None = None
    level: str | None = None
    agent_id: str | None = None


class LogResponse(BaseModel):
    logs: list[dict[str, Any]]


# Optimization/Agent models kept for compatibility if needed, but not strictly required by new schema
# I will keep them if they are used by other parts of the system, but distinct from the requested schema.
class AgentInfo(BaseModel):
    name: str
    description: str
    model: str
    capabilities: list[str]
    status: str


class AgentListResponse(BaseModel):
    agents: list[AgentInfo]
