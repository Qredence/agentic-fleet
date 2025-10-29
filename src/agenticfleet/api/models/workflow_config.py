"""Pydantic models for workflow configuration validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReasoningConfig(BaseModel):
    """Configuration for OpenAI reasoning parameters."""

    effort: str = Field(
        default="medium",
        description="Reasoning effort level: 'low', 'medium', or 'high'",
    )
    verbosity: str = Field(
        default="verbose",
        description="Reasoning verbosity: 'verbose' or 'concise'",
    )


class AgentConfig(BaseModel):
    """Configuration for a single agent in a workflow."""

    model: str = Field(
        description="OpenAI model ID (e.g., 'gpt-5-mini', 'gpt-5')",
    )
    instructions: str = Field(
        description="System prompt/instructions for the agent",
    )
    description: str = Field(
        description="Brief description of agent's role",
    )
    reasoning: ReasoningConfig = Field(
        default_factory=ReasoningConfig,
        description="Reasoning configuration",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum tokens for response",
    )
    store: bool = Field(
        default=True,
        description="Whether to store conversation history",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of tool names to enable for this agent",
    )


class ManagerConfig(BaseModel):
    """Configuration for the workflow manager/orchestrator."""

    model: str = Field(
        description="OpenAI model ID for the manager",
    )
    instructions: str = Field(
        description="System prompt/instructions for the manager",
    )
    reasoning: ReasoningConfig = Field(
        default_factory=ReasoningConfig,
        description="Reasoning configuration",
    )
    temperature: float = Field(
        default=0.6,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int = Field(
        default=8192,
        gt=0,
        description="Maximum tokens for response",
    )
    store: bool = Field(
        default=True,
        description="Whether to store conversation history",
    )
    max_round_count: int = Field(
        default=12,
        gt=0,
        description="Maximum number of agent interaction rounds",
    )
    max_stall_count: int = Field(
        default=3,
        gt=0,
        description="Maximum consecutive rounds without progress before replanning",
    )
    max_reset_count: int = Field(
        default=1,
        ge=0,
        description="Maximum number of full workflow resets allowed",
    )


class WorkflowConfig(BaseModel):
    """Configuration for a complete workflow."""

    name: str = Field(
        description="Human-readable workflow name",
    )
    description: str = Field(
        description="Brief description of workflow purpose and agents",
    )
    factory: str = Field(
        description="Factory function name to create this workflow",
    )
    agents: dict[str, AgentConfig] = Field(
        description="Agent configurations keyed by agent name",
    )
    manager: ManagerConfig = Field(
        description="Manager/orchestrator configuration",
    )


class WorkflowsConfig(BaseModel):
    """Root configuration containing all workflow definitions."""

    workflows: dict[str, WorkflowConfig] = Field(
        description="Workflow definitions keyed by workflow ID",
    )

    def get_workflow(self, workflow_id: str) -> WorkflowConfig | None:
        """Get a workflow configuration by ID."""
        return self.workflows.get(workflow_id)

    def list_workflow_ids(self) -> list[str]:
        """List all available workflow IDs."""
        return list(self.workflows.keys())

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all workflows with their metadata."""
        return [
            {
                "id": workflow_id,
                "name": config.name,
                "description": config.description,
                "factory": config.factory,
                "agent_count": len(config.agents),
            }
            for workflow_id, config in self.workflows.items()
        ]
