"""Tests for DSPy typed Pydantic models.

These tests verify that the Pydantic models correctly validate and coerce
output data from DSPy predictions, ensuring robust structured outputs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic_fleet.dspy_modules.typed_models import (
    CapabilityMatchOutput,
    HandoffDecisionOutput,
    ProgressEvaluationOutput,
    QualityAssessmentOutput,
    RoutingDecisionOutput,
    TaskAnalysisOutput,
    ToolPlanOutput,
    WorkflowStrategyOutput,
)


class TestRoutingDecisionOutput:
    """Tests for RoutingDecisionOutput model."""

    def test_valid_routing_decision(self):
        """Verify valid routing decision passes validation."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer", "Researcher"],
            execution_mode="sequential",
            subtasks=["Research", "Write"],
            tool_requirements=["TavilySearchTool"],
            reasoning="Task requires research then writing",
        )

        assert decision.assigned_to == ["Writer", "Researcher"]
        assert decision.execution_mode == "sequential"
        assert len(decision.subtasks) == 2
        assert decision.tool_requirements == ["TavilySearchTool"]

    def test_mode_normalization_lowercase(self):
        """Verify execution_mode is normalized to lowercase."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer"],
            execution_mode="DELEGATED",  # type: ignore[arg-type]
            reasoning="Simple task",
        )

        assert decision.execution_mode == "delegated"

    def test_mode_normalization_mixed_case(self):
        """Verify mixed case execution_mode is normalized."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer", "Analyst"],
            execution_mode="Parallel",  # type: ignore[arg-type]
            reasoning="Independent tasks",
        )

        assert decision.execution_mode == "parallel"

    def test_invalid_mode_rejected(self):
        """Verify invalid execution_mode raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RoutingDecisionOutput(
                assigned_to=["Writer"],
                execution_mode="invalid_mode",  # type: ignore[arg-type]
                reasoning="Bad mode",
            )

        assert "execution_mode" in str(exc_info.value)

    def test_comma_separated_agents_coerced(self):
        """Verify comma-separated agent string is coerced to list."""
        decision = RoutingDecisionOutput(
            assigned_to="Writer, Researcher, Analyst",  # type: ignore[arg-type]
            execution_mode="parallel",
            reasoning="Multi-agent task",
        )

        assert decision.assigned_to == ["Writer", "Researcher", "Analyst"]

    def test_comma_separated_tools_coerced(self):
        """
        Ensure `tool_requirements` is stored as a list, accepting comma-separated tool strings.

        Asserts that the specified tools appear in `tool_requirements`.
        """
        decision = RoutingDecisionOutput(
            assigned_to=["Researcher"],
            execution_mode="delegated",
            tool_requirements=["TavilySearchTool", "CodeInterpreter"],
            reasoning="Research with code",
        )

        assert "TavilySearchTool" in decision.tool_requirements
        assert "CodeInterpreter" in decision.tool_requirements

    def test_empty_lists_default(self):
        """Verify empty lists as defaults."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer"],
            execution_mode="delegated",
            reasoning="Simple task",
        )

        assert decision.subtasks == []
        assert decision.tool_requirements == []
        assert decision.tool_plan == []

    def test_optional_fields(self):
        """Verify optional fields can be set."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer"],
            execution_mode="delegated",
            reasoning="With optional fields",
            handoff_strategy="Sequential handoff",
            workflow_gates="Quality check after each step",
            tool_goals="Web search for current info",
            latency_budget="low",
        )

        assert decision.handoff_strategy == "Sequential handoff"
        assert decision.workflow_gates == "Quality check after each step"


class TestTaskAnalysisOutput:
    """Tests for TaskAnalysisOutput model."""

    def test_valid_task_analysis(self):
        """Verify valid task analysis passes validation."""
        analysis = TaskAnalysisOutput(
            complexity="high",
            required_capabilities=["research", "coding"],
            estimated_steps=5,
            preferred_tools=["TavilySearchTool"],
            needs_web_search=True,
            search_query="Latest AI trends 2025",
            urgency="medium",
            reasoning="Complex research task",
        )

        assert analysis.complexity == "high"
        assert analysis.estimated_steps == 5
        assert analysis.needs_web_search is True

    def test_complexity_normalization(self):
        """Verify complexity is validated (must be lowercase)."""
        # The field validator only allows lowercase values
        analysis = TaskAnalysisOutput(
            complexity="high",
            required_capabilities=[],
            estimated_steps=3,
            needs_web_search=False,
            reasoning="Normalized complexity",
        )

        assert analysis.complexity == "high"

    def test_invalid_complexity_rejected(self):
        """Verify invalid complexity raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TaskAnalysisOutput(
                complexity="very_high",  # type: ignore[arg-type]
                required_capabilities=[],
                estimated_steps=1,
                needs_web_search=False,
                reasoning="Invalid complexity",
            )

        assert "complexity" in str(exc_info.value)

    def test_estimated_steps_minimum(self):
        """Verify estimated_steps minimum is enforced."""
        with pytest.raises(ValidationError):
            TaskAnalysisOutput(
                complexity="low",
                required_capabilities=[],
                estimated_steps=0,
                needs_web_search=False,
                reasoning="Zero steps invalid",
            )

    def test_string_capabilities_coerced(self):
        """Verify string capabilities are coerced to list."""
        analysis = TaskAnalysisOutput(
            complexity="medium",
            required_capabilities="research, coding, writing",  # type: ignore[arg-type]
            estimated_steps=3,
            needs_web_search=False,
            reasoning="Coerced capabilities",
        )

        assert analysis.required_capabilities == ["research", "coding", "writing"]


class TestQualityAssessmentOutput:
    """Tests for QualityAssessmentOutput model."""

    def test_valid_quality_assessment(self):
        """Verify valid quality assessment passes validation."""
        assessment = QualityAssessmentOutput(
            score=8.5,
            missing_elements="None",
            required_improvements="Add citations",
            reasoning="Good quality with minor improvements",
        )

        assert assessment.score == 8.5
        assert assessment.missing_elements == "None"

    def test_score_clamped_to_minimum(self):
        """Verify score is clamped to minimum."""
        assessment = QualityAssessmentOutput(
            score=-5.0,
            missing_elements="",
            required_improvements="",
            reasoning="Clamped score",
        )
        # Score is clamped to 0.0
        assert assessment.score == 0.0

    def test_score_clamped_to_maximum(self):
        """Verify score is clamped to maximum."""
        assessment = QualityAssessmentOutput(
            score=15.0,
            missing_elements="",
            required_improvements="",
            reasoning="Clamped score",
        )
        # Score is clamped to 10.0
        assert assessment.score == 10.0

    def test_string_score_coerced(self):
        """Verify string score is coerced to float."""
        assessment = QualityAssessmentOutput(
            score="7.5",  # type: ignore[arg-type]
            missing_elements="",
            required_improvements="",
            reasoning="Coerced score",
        )

        assert assessment.score == 7.5
        assert isinstance(assessment.score, float)


class TestProgressEvaluationOutput:
    """Tests for ProgressEvaluationOutput model."""

    def test_valid_progress_evaluation(self):
        """Verify valid progress evaluation passes validation."""
        evaluation = ProgressEvaluationOutput(
            action="complete",
            feedback="Task fully addressed",
            reasoning="All requirements met",
        )

        assert evaluation.action == "complete"
        assert evaluation.feedback == "Task fully addressed"

    def test_action_normalization(self):
        """Verify action is normalized to lowercase."""
        evaluation = ProgressEvaluationOutput(
            action="REFINE",  # type: ignore[arg-type]
            feedback="Needs more detail",
            reasoning="Incomplete",
        )

        assert evaluation.action == "refine"

    def test_invalid_action_rejected(self):
        """Verify invalid action raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProgressEvaluationOutput(
                action="restart",  # type: ignore[arg-type]
                feedback="Invalid",
                reasoning="Bad action",
            )

        assert "action" in str(exc_info.value)


class TestToolPlanOutput:
    """Tests for ToolPlanOutput model."""

    def test_valid_tool_plan(self):
        """Verify valid tool plan passes validation."""
        plan = ToolPlanOutput(
            tool_plan=["TavilySearchTool", "CodeInterpreter"],
            reasoning="Need search then code execution",
        )

        assert len(plan.tool_plan) == 2

    def test_string_tool_plan_coerced(self):
        """Verify string tool plan is coerced to list."""
        plan = ToolPlanOutput(
            tool_plan="TavilySearchTool, CodeInterpreter",  # type: ignore[arg-type]
            reasoning="Coerced plan",
        )

        assert plan.tool_plan == ["TavilySearchTool", "CodeInterpreter"]

    def test_empty_tool_plan_allowed(self):
        """Verify empty tool plan is allowed."""
        plan = ToolPlanOutput(
            tool_plan=[],
            reasoning="No tools needed",
        )

        assert plan.tool_plan == []


class TestWorkflowStrategyOutput:
    """Tests for WorkflowStrategyOutput model."""

    def test_valid_workflow_strategy(self):
        """Verify valid workflow strategy passes validation."""
        strategy = WorkflowStrategyOutput(
            workflow_mode="handoff",
            reasoning="Task requires multiple handoffs",
        )

        assert strategy.workflow_mode == "handoff"

    def test_workflow_mode_normalization(self):
        """Verify workflow_mode is normalized to lowercase."""
        strategy = WorkflowStrategyOutput(
            workflow_mode="standard",
            reasoning="Normalized mode",
        )

        assert strategy.workflow_mode == "standard"

    def test_invalid_workflow_mode_rejected(self):
        """Verify invalid workflow_mode raises ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowStrategyOutput(
                workflow_mode="async",  # type: ignore[arg-type]
                reasoning="Invalid mode",
            )


class TestHandoffDecisionOutput:
    """Tests for HandoffDecisionOutput model."""

    def test_valid_handoff_decision(self):
        """Verify valid handoff decision passes validation."""
        decision = HandoffDecisionOutput(
            should_handoff=True,
            next_agent="Analyst",
            handoff_context="Analysis complete, ready for review",
            handoff_reason="Research phase complete",
        )

        assert decision.should_handoff is True
        assert decision.next_agent == "Analyst"

    def test_no_handoff_decision(self):
        """Verify no-handoff decision passes validation."""
        decision = HandoffDecisionOutput(
            should_handoff=False,
            next_agent="",
            handoff_context="",
            handoff_reason="",
        )

        assert decision.should_handoff is False


class TestCapabilityMatchOutput:
    """Tests for CapabilityMatchOutput model."""

    def test_valid_capability_match(self):
        """Verify valid capability match passes validation."""
        match = CapabilityMatchOutput(
            best_match="Researcher",
            confidence=9.5,
            capability_gaps="coding",
            fallback_agents=["Writer", "Analyst"],
        )

        assert match.best_match == "Researcher"
        assert match.confidence == 9.5

    def test_confidence_clamped(self):
        """Verify confidence is clamped to range."""
        match = CapabilityMatchOutput(
            best_match="Writer",
            confidence=15.0,
        )
        # Confidence is clamped to 10.0
        assert match.confidence == 10.0

    def test_string_fallback_agents_coerced(self):
        """Verify string fallback_agents are coerced to list."""
        match = CapabilityMatchOutput(
            best_match="Writer",
            confidence=8.0,
            fallback_agents="Researcher, Analyst",  # type: ignore[arg-type]
        )

        assert match.fallback_agents == ["Researcher", "Analyst"]


class TestModelSerialization:
    """Tests for model serialization/deserialization."""

    def test_routing_decision_to_dict(self):
        """Verify RoutingDecisionOutput converts to dict correctly."""
        decision = RoutingDecisionOutput(
            assigned_to=["Writer"],
            execution_mode="delegated",
            reasoning="Simple task",
        )

        data = decision.model_dump()

        assert isinstance(data, dict)
        assert data["assigned_to"] == ["Writer"]
        assert data["execution_mode"] == "delegated"

    def test_routing_decision_from_dict(self):
        """Verify RoutingDecisionOutput can be created from dict."""
        data = {
            "assigned_to": ["Researcher", "Writer"],
            "execution_mode": "sequential",
            "subtasks": ["Research", "Write"],
            "tool_requirements": [],
            "reasoning": "Two-phase task",
        }

        decision = RoutingDecisionOutput(**data)

        assert decision.assigned_to == ["Researcher", "Writer"]
        assert decision.execution_mode == "sequential"

    def test_quality_assessment_json_round_trip(self):
        """Verify QualityAssessmentOutput survives JSON round trip."""
        original = QualityAssessmentOutput(
            score=9.0,
            missing_elements="None",
            required_improvements="Minor formatting",
            reasoning="Excellent response",
        )

        json_str = original.model_dump_json()
        restored = QualityAssessmentOutput.model_validate_json(json_str)

        assert restored.score == original.score
        assert restored.reasoning == original.reasoning
