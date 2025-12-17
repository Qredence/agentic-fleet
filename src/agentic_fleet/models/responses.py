"""Response models for the AgenticFleet API.

Defines response schemas for various API endpoints.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunResponse(BaseModel):
    """Response model for workflow execution results.

    Attributes:
        result: The execution result as a string.
        status: Execution status (completed, failed, etc.).
        execution_id: Unique identifier for this execution.
        metadata: Additional metadata about the execution.
    """

    result: str = Field(..., description="Execution result")
    status: str = Field(..., description="Execution status")
    execution_id: str = Field(..., description="Unique execution identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "result": "Analysis complete. Key findings: ...",
                    "status": "completed",
                    "execution_id": "wf-abc123-def456",
                    "metadata": {
                        "duration_seconds": 12.5,
                        "agents_used": ["researcher", "analyst"],
                    },
                }
            ]
        },
    )


class AgentInfo(BaseModel):
    """Information about an available agent.

    Attributes:
        name: The agent's name.
        description: Human-readable description of the agent's capabilities.
        type: The agent type (DSPyEnhancedAgent, StandardAgent, etc.).
    """

    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    type: str = Field(..., description="Agent type")

    model_config = ConfigDict(from_attributes=True)
