from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Core Models
class WorkflowRequest(BaseModel):
    task: str = Field(..., description="The task description to execute")
    config: dict[str, Any] | None = Field(
        default=None, description="Optional workflow configuration overrides"
    )


class WorkflowResponse(BaseModel):
    workflow_id: str = Field(..., description="Unique ID of the workflow run")
    status: str = Field(..., description="Status of the workflow")
    result: str = Field(..., description="The final result text")
    quality_score: float = Field(..., description="Quality score (0-10)")
    execution_time_seconds: float = Field(..., description="Total execution time")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class OptimizationRequest(BaseModel):
    iterations: int = Field(default=3, description="Number of optimization iterations")
    task: str = Field(
        default="Write a blog post about AI", description="Task to use for optimization benchmark"
    )
    compile_dspy: bool = Field(default=True, description="Whether to compile DSPy modules")


class OptimizationResult(BaseModel):
    optimization_id: str
    status: str
    compiled_avg_time: float | None
    uncompiled_avg_time: float | None
    improvement_percentage: float | None
    details: dict[str, Any]


class AgentInfo(BaseModel):
    name: str
    description: str
    model: str
    capabilities: list[str]
    status: str


class AgentListResponse(BaseModel):
    agents: list[AgentInfo]


class HistoryQuery(BaseModel):
    limit: int = Field(default=20, description="Number of entries to return")
    min_quality: float = Field(default=0.0, description="Minimum quality score filter")


class HistoryEntry(BaseModel):
    workflow_id: str
    task: str
    result: str
    quality_score: float
    total_time_seconds: float
    timestamp: str
    model_config = ConfigDict(extra="ignore")


class HistoryResponse(BaseModel):
    history: list[HistoryEntry]
    total: int


class SelfImprovementRequest(BaseModel):
    min_quality: float = Field(default=8.0, description="Minimum quality score to learn from")
    max_examples: int = Field(default=20, description="Maximum new examples to add")


class SelfImprovementResponse(BaseModel):
    added_count: int
    status: str
    details: dict[str, Any]
