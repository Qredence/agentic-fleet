"""Pydantic models for DSPy TypedPredictors.

This module defines structured output models that enforce JSON schema compliance
for DSPy predictions, reducing parsing errors and improving reliability.

These models are used with dspy.TypedPredictor to:
- Enforce JSON schema compliance
- Auto-retry on malformed outputs
- Provide clear validation errors
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RoutingDecisionOutput(BaseModel):
    """Structured output for task routing decisions."""

    assigned_to: list[str] = Field(
        description="List of agent names assigned to the task",
        min_length=1,
    )
    execution_mode: Literal["delegated", "sequential", "parallel"] = Field(
        description="Execution mode: delegated (single agent), sequential (ordered), or parallel (concurrent)",
    )
    subtasks: list[str] = Field(
        default_factory=list,
        description="Task breakdown into subtasks (if applicable)",
    )
    tool_requirements: list[str] = Field(
        default_factory=list,
        description="List of required tool names",
    )
    tool_plan: list[str] = Field(
        default_factory=list,
        description="Ordered list of tools to use",
    )
    tool_goals: str = Field(
        default="",
        description="Specific goals for tool usage",
    )
    latency_budget: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Estimated time/latency budget",
    )
    handoff_strategy: str = Field(
        default="",
        description="Strategy for agent handoffs",
    )
    workflow_gates: str = Field(
        default="",
        description="Quality gates and checkpoints",
    )
    reasoning: str = Field(
        description="Reasoning for the routing decision",
    )

    @field_validator("assigned_to", mode="before")
    @classmethod
    def ensure_list(cls, v: str | list[str]) -> list[str]:
        """
        Normalize a comma-separated string into a list of trimmed, non-empty items.

        Parameters:
            v (str | list[str]): A comma-separated string of items or an already-parsed list of strings.

        Returns:
            list[str]: A list of trimmed, non-empty strings. If `v` is already a list, it is returned unchanged.
        """
        if isinstance(v, str):
            return [agent.strip() for agent in v.split(",") if agent.strip()]
        return v

    @field_validator("execution_mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        """
        Normalize various textual representations of an execution mode to canonical values.

        Converts common synonyms (e.g., "delegate" or "single" -> "delegated";
        "sequence" or "serial" -> "sequential"; "concurrent" -> "parallel") and
        trims/lowers the input string. If the value is not a recognized synonym,
        the input (lowercased and stripped) is returned unchanged.

        Parameters:
            v (str): Candidate execution mode string.

        Returns:
            str: Canonicalized execution mode string.
        """
        if isinstance(v, str):
            v = v.strip().lower()
            # Handle common variations
            mode_mapping = {
                "delegate": "delegated",
                "single": "delegated",
                "sequence": "sequential",
                "serial": "sequential",
                "concurrent": "parallel",
            }
            return mode_mapping.get(v, v)
        return v


class TaskAnalysisOutput(BaseModel):
    """Structured output for task analysis."""

    complexity: Literal["low", "medium", "high"] = Field(
        description="Estimated task complexity",
    )
    required_capabilities: list[str] = Field(
        description="List of required capabilities (e.g., research, coding)",
    )
    estimated_steps: int = Field(
        ge=1,
        le=50,
        description="Estimated number of steps to complete the task",
    )
    preferred_tools: list[str] = Field(
        default_factory=list,
        description="Ordered list of tools to prioritize if needed",
    )
    needs_web_search: bool = Field(
        description="Whether the task requires fresh or online information",
    )
    search_query: str = Field(
        default="",
        description="Suggested search query (empty if web search not needed)",
    )
    urgency: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Time sensitivity / freshness requirement",
    )
    reasoning: str = Field(
        description="Reasoning behind the analysis",
    )

    @field_validator("required_capabilities", mode="before")
    @classmethod
    def ensure_capabilities_list(cls, v: str | list[str]) -> list[str]:
        """
        Normalize capability input to a list of capability names.

        Accepts a comma-separated string or a list of strings. When given a string, splits on commas, strips surrounding whitespace from each item, and discards empty items.

        Parameters:
            v (str | list[str]): Capability input to normalize.

        Returns:
            list[str]: List of capability names with whitespace removed; returns the original list unchanged if `v` is already a list.
        """
        if isinstance(v, str):
            return [cap.strip() for cap in v.split(",") if cap.strip()]
        return v


class QualityAssessmentOutput(BaseModel):
    """Structured output for quality assessment."""

    score: float = Field(
        ge=0.0,
        le=10.0,
        description="Quality score between 0.0 and 10.0",
    )
    missing_elements: str = Field(
        description="Description of what is missing from the result",
    )
    required_improvements: str = Field(
        description="Specific improvements needed",
    )
    reasoning: str = Field(
        description="Reasoning for the quality score",
    )

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, v: float | str) -> float:
        """Ensure score is within valid range."""
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                return 5.0  # Default to middle score on parse error
        return max(0.0, min(10.0, float(v)))


class ProgressEvaluationOutput(BaseModel):
    """Structured output for progress evaluation."""

    action: Literal["complete", "refine", "continue"] = Field(
        description="Next action to take",
    )
    feedback: str = Field(
        description="Feedback for the next step",
    )
    reasoning: str = Field(
        description="Reasoning for the decision",
    )

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, v: str) -> str:
        """
        Normalize common progress/action strings to canonical action names.

        Parameters:
            v (str | any): Input action value; common string variations like "done", "finished",
                "improve", "iterate", "proceed", and "next" are mapped to "complete", "refine",
                and "continue" respectively. Non-string inputs are returned unchanged.

        Returns:
            str | any: Canonical action string ("complete", "refine", or "continue") when a
            known variation is provided, otherwise returns the original value.
        """
        if isinstance(v, str):
            v = v.strip().lower()
            # Handle common variations
            action_mapping = {
                "done": "complete",
                "finished": "complete",
                "improve": "refine",
                "iterate": "refine",
                "proceed": "continue",
                "next": "continue",
            }
            return action_mapping.get(v, v)
        return v


class ToolPlanOutput(BaseModel):
    """Structured output for tool planning."""

    tool_plan: list[str] = Field(
        description="Ordered list of tool names to use",
    )
    reasoning: str = Field(
        description="Reasoning for the tool plan",
    )

    @field_validator("tool_plan", mode="before")
    @classmethod
    def ensure_tool_list(cls, v: str | list[str]) -> list[str]:
        """
        Normalize a tool-plan value into a list of tool names.

        Converts a comma-separated string into a list by trimming whitespace and removing empty entries; if `v` is already a list of strings, returns it unchanged.

        Parameters:
            v (str | list[str]): A comma-separated string of tool names or an existing list of tool names.

        Returns:
            list[str]: A list of trimmed tool names with empty items removed.
        """
        if isinstance(v, str):
            return [tool.strip() for tool in v.split(",") if tool.strip()]
        return v


class WorkflowStrategyOutput(BaseModel):
    """Structured output for workflow strategy selection."""

    workflow_mode: Literal["handoff", "standard", "fast_path"] = Field(
        description="The optimal workflow architecture",
    )
    reasoning: str = Field(
        description="Why this architecture was chosen",
    )

    @field_validator("workflow_mode", mode="before")
    @classmethod
    def normalize_workflow_mode(cls, v: str) -> str:
        """
        Normalize workflow_mode variations to canonical values.

        Converts common alternative spellings or synonyms to the canonical workflow modes expected by the model.

        Parameters:
            v (str): Input workflow mode string to normalize.

        Returns:
            str: Canonical workflow mode (for example, "handoff", "standard", or "fast_path"), or the original value if no normalization rule applies.
        """
        if isinstance(v, str):
            v = v.strip().lower()
            # Handle common variations
            mode_mapping = {
                "hand_off": "handoff",
                "hand-off": "handoff",
                "normal": "standard",
                "default": "standard",
                "fast": "fast_path",
                "quick": "fast_path",
                "simple": "fast_path",
            }
            return mode_mapping.get(v, v)
        return v


class GroupChatSpeakerOutput(BaseModel):
    """Structured output for group chat speaker selection."""

    next_speaker: str = Field(
        description="The name of the next speaker, or 'TERMINATE' to end",
    )
    reasoning: str = Field(
        description="Reasoning for the selection",
    )


class SimpleResponseOutput(BaseModel):
    """Structured output for simple/direct responses."""

    answer: str = Field(
        description="Concise and accurate answer to the task/question",
    )


class HandoffDecisionOutput(BaseModel):
    """Structured output for handoff decisions."""

    should_handoff: bool = Field(
        description="Whether handoff is recommended",
    )
    next_agent: str = Field(
        default="",
        description="Which agent to hand off to (empty if no handoff)",
    )
    handoff_context: str = Field(
        default="",
        description="Key information the next agent needs to know",
    )
    handoff_reason: str = Field(
        default="",
        description="Why this handoff is necessary or beneficial",
    )

    @field_validator("should_handoff", mode="before")
    @classmethod
    def normalize_bool(cls, v: str | bool) -> bool:
        """
        Convert a string or boolean-like value to a canonical boolean.

        Recognizes the case-insensitive string values "yes", "true", "1", and "y" as True; any other string yields False. If a boolean is provided, its boolean value is returned.

        Parameters:
            v (str | bool): Input value to normalize; may be a boolean or a string representation.

        Returns:
            bool: `True` if the input represents a truthy value, `False` otherwise.
        """
        if isinstance(v, str):
            return v.strip().lower() in ("yes", "true", "1", "y")
        return bool(v)


class CapabilityMatchOutput(BaseModel):
    """Structured output for capability matching."""

    best_match: str = Field(
        description="Agent with the best capability match",
    )
    capability_gaps: str = Field(
        default="",
        description="Required capabilities that are not available",
    )
    fallback_agents: list[str] = Field(
        default_factory=list,
        description="Alternative agents if primary is unavailable",
    )
    confidence: float = Field(
        ge=0.0,
        le=10.0,
        description="Confidence score 0-10 in the capability match",
    )

    @field_validator("fallback_agents", mode="before")
    @classmethod
    def ensure_fallback_list(cls, v: str | list[str]) -> list[str]:
        """
        Normalize a fallback-agents value into a list of agent names.

        Converts a comma-separated string into a list of trimmed, non-empty agent names; returns a list input unchanged.

        Parameters:
            v (str | list[str]): A comma-separated string of agent names or an already-parsed list.

        Returns:
            list[str]: List of agent names with surrounding whitespace removed and empty entries omitted.
        """
        if isinstance(v, str):
            return [agent.strip() for agent in v.split(",") if agent.strip()]
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: float | str) -> float:
        """
        Normalize and clamp a confidence value to the range 0.0-10.0.

        Parameters:
            v (float | str): Confidence value as a float or numeric string. If a string cannot be parsed as a float, a default value is used.

        Returns:
            float: Confidence value converted to a float and clamped to the interval [0.0, 10.0]. If parsing a non-numeric string, returns 5.0.
        """
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                return 5.0
        return max(0.0, min(10.0, float(v)))


__all__ = [
    "CapabilityMatchOutput",
    "GroupChatSpeakerOutput",
    "HandoffDecisionOutput",
    "ProgressEvaluationOutput",
    "QualityAssessmentOutput",
    "RoutingDecisionOutput",
    "SimpleResponseOutput",
    "TaskAnalysisOutput",
    "ToolPlanOutput",
    "WorkflowStrategyOutput",
]
