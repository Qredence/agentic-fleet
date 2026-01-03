"""Pydantic models and DSPy signatures for the cognitive layer."""

from __future__ import annotations

from typing import Literal

import dspy
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentic_fleet.dspy_modules.validation import (
    validate_non_empty_str,
    validate_routing_pattern,
    validate_string_list,
    validate_team_name,
)


class TaskContext(BaseModel):
    """Context passed into planner/worker modules."""

    model_config = ConfigDict(extra="forbid")

    team_id: str
    constraints: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    mounted_skills: list[str] = Field(default_factory=list, description="Active mounted skills")
    available_skills: list[str] = Field(default_factory=list, description="All available skills")

    @field_validator("team_id")
    @classmethod
    def _team_id(cls, value: str) -> str:
        return validate_team_name(value)

    @field_validator("constraints")
    @classmethod
    def _constraints(cls, value: list[str]) -> list[str]:
        return validate_string_list(value, "constraints")

    @field_validator("tools")
    @classmethod
    def _tools(cls, value: list[str]) -> list[str]:
        return validate_string_list(value, "tools")

    @field_validator("mounted_skills", "available_skills")
    @classmethod
    def _skill_lists(cls, value: list[str]) -> list[str]:
        if value is None:
            return []
        return validate_string_list(value, "skills")


class ExecutionResult(BaseModel):
    """Normalized output from a worker step."""

    model_config = ConfigDict(extra="forbid")

    status: str
    content: str
    artifacts: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        return validate_non_empty_str(value, "status")

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        return validate_non_empty_str(value, "content")

    @field_validator("artifacts")
    @classmethod
    def _artifacts(cls, value: list[str]) -> list[str]:
        return validate_string_list(value, "artifacts")


class RoutingDecision(BaseModel):
    """Router output describing where to send a task."""

    model_config = ConfigDict(extra="forbid")

    pattern: Literal[
        "direct",
        "simple",
        "complex",
        "direct_answer",
        "simple_tool",
        "complex_council",
    ]
    target_team: str
    reasoning: str
    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills recommended for task execution"
    )

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str) -> str:
        return validate_routing_pattern(value)

    @field_validator("target_team")
    @classmethod
    def _target_team(cls, value: str) -> str:
        return validate_team_name(value)

    @field_validator("reasoning")
    @classmethod
    def _reasoning(cls, value: str) -> str:
        return validate_non_empty_str(value, "reasoning")

    @field_validator("required_skills")
    @classmethod
    def _required_skills(cls, value: list[str]) -> list[str]:
        if value is None:
            return []
        return validate_string_list(value, "required_skills")


class RouterSignature(dspy.Signature):
    """Route a task to the right team and execution pattern."""

    task: str = dspy.InputField(desc="Task to route")
    decision: RoutingDecision = dspy.OutputField(desc="Routing decision")


class PlannerSignature(dspy.Signature):
    """Plan a task into actionable steps with skill selection."""

    task: str = dspy.InputField(desc="Task to plan")
    context: TaskContext = dspy.InputField(desc="Execution context with mounted/available skills")
    available_skills: str = dspy.InputField(
        desc="Comma-separated list of available skills to consider"
    )
    plan: str = dspy.OutputField(desc="Structured plan incorporating relevant skills")
    required_skills: str = dspy.OutputField(
        desc="Comma-separated list of skills needed for this plan"
    )
    reasoning: str = dspy.OutputField(desc="Planner rationale for skill selection")


class WorkerSignature(dspy.Signature):
    """Execute a single step with mounted skills."""

    step: str = dspy.InputField(desc="Step to execute")
    context: TaskContext = dspy.InputField(desc="Execution context with mounted skills")
    mounted_skills: str = dspy.InputField(
        desc="Comma-separated list of currently mounted skills"
    )
    action: str = dspy.OutputField(desc="Action taken")
    result: ExecutionResult = dspy.OutputField(desc="Execution result")


class JudgeSignature(dspy.Signature):
    """Review the execution output for approval."""

    original_task: str = dspy.InputField(desc="Original task")
    result: ExecutionResult = dspy.InputField(desc="Result to evaluate")
    is_approved: bool = dspy.OutputField(desc="Approval decision")
    critique: str = dspy.OutputField(desc="Judgment feedback")
