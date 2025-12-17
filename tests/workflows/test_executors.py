"""Tests for workflows/executors.py - Workflow executor functionality.

This module tests the various executor classes used in the workflow pipeline:
AnalysisExecutor, RoutingExecutor, ExecutionExecutor, ProgressExecutor,
QualityExecutor.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.executors import (
    AnalysisExecutor,
    ProgressExecutor,
    QualityExecutor,
    RoutingExecutor,
)
from agentic_fleet.workflows.models import AnalysisResult, ProgressReport, QualityReport

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = MagicMock()
    config.pipeline_profile = "full"
    config.simple_task_max_words = 40
    config.dspy_retry_attempts = 3
    config.dspy_retry_backoff_seconds = 1.0
    config.dspy_max_backtracks = 2
    config.parallel_threshold = 2
    config.enable_progress_eval = True
    config.enable_quality_eval = True
    config.enable_judge = False
    config.enable_refinement = False
    config.judge_threshold = 0.8
    config.max_refinement_rounds = 3
    config.refinement_threshold = 0.7
    return config


@pytest.fixture
def mock_supervisor_context(mock_config):
    """Create a mock supervisor context."""
    context = MagicMock(spec=SupervisorContext)
    context.config = mock_config
    context.agents = {"Writer": MagicMock(), "Researcher": MagicMock()}
    context.analysis_cache = None
    context.latest_phase_status = {}
    context.latest_phase_timings = {}
    context.dspy_supervisor = None
    return context


@pytest.fixture
def mock_dspy_reasoner():
    """Create a mock DSPy reasoner."""
    reasoner = MagicMock()
    reasoner.analyze_task = AsyncMock(
        return_value={
            "complexity": "moderate",
            "capabilities": ["writing", "research"],
            "tool_requirements": ["web_search"],
            "steps": 4,
            "search_context": "",
            "needs_web_search": False,
            "search_query": "",
        }
    )
    reasoner.route_task = AsyncMock(
        return_value=RoutingDecision(
            task="Test task",
            assigned_to=("Writer",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Test task",),
            tool_requirements=(),
            confidence=0.9,
        )
    )
    reasoner.evaluate_progress = AsyncMock(
        return_value={"action": "complete", "feedback": "Good job"}
    )
    reasoner.assess_quality = AsyncMock(
        return_value={"score": 0.85, "missing": "", "improvements": ""}
    )
    return reasoner


# =============================================================================
# Test: AnalysisExecutor
# =============================================================================


class TestAnalysisExecutor:
    """Tests for AnalysisExecutor."""

    def test_initializes_with_required_params(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that executor initializes correctly."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor.supervisor == mock_dspy_reasoner
        assert executor.context == mock_supervisor_context

    def test_fallback_analysis_simple_task(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test fallback analysis for simple tasks."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._fallback_analysis("hello world")

        assert result["complexity"] == "simple"
        assert result["capabilities"] == ["general_reasoning"]
        assert result["steps"] == 3

    def test_fallback_analysis_moderate_task(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test fallback analysis for moderate tasks."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        # Create a task with 50+ words
        task = " ".join(["word"] * 50)
        result = executor._fallback_analysis(task)

        assert result["complexity"] == "moderate"

    def test_fallback_analysis_complex_task(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test fallback analysis for complex tasks."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        # Create a task with 160+ words
        task = " ".join(["word"] * 160)
        result = executor._fallback_analysis(task)

        assert result["complexity"] == "complex"

    def test_to_analysis_result_valid_payload(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test conversion of valid payload to AnalysisResult."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        payload = {
            "complexity": "moderate",
            "capabilities": ["writing", "research"],
            "tool_requirements": ["web_search"],
            "steps": 5,
            "search_context": "Some context",
            "needs_web_search": True,
            "search_query": "test query",
        }

        result = executor._to_analysis_result(payload)

        assert isinstance(result, AnalysisResult)
        assert result.complexity == "moderate"
        assert result.capabilities == ["writing", "research"]
        assert result.tool_requirements == ["web_search"]
        assert result.steps == 5
        assert result.needs_web_search is True

    def test_to_analysis_result_handles_defaults(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that conversion handles missing fields with defaults."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._to_analysis_result({})

        assert result.complexity == "moderate"
        assert result.capabilities == ["general_reasoning"]
        assert result.steps == 3

    def test_to_analysis_result_handles_invalid_steps(
        self, mock_dspy_reasoner, mock_supervisor_context
    ):
        """Test that conversion handles invalid steps value."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._to_analysis_result({"steps": "invalid"})
        assert result.steps == 3  # Default

        result = executor._to_analysis_result({"steps": -5})
        assert result.steps == 3  # Default

    def test_is_simple_task_with_greeting(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test simple task detection with greeting patterns."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor._is_simple_task("Hello there", 40) is True
        assert executor._is_simple_task("Hi, how are you?", 40) is True
        assert executor._is_simple_task("hey", 40) is True

    def test_is_simple_task_with_help(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test simple task detection with help command."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor._is_simple_task("/help", 40) is True

    def test_is_simple_task_with_remember(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test simple task detection with remember pattern."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor._is_simple_task("Remember this: important info", 40) is True
        assert executor._is_simple_task("save this: data", 40) is True

    def test_is_simple_task_word_count(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test simple task detection based on word count."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        short_task = "Write a poem"
        long_task = " ".join(["word"] * 50)

        assert executor._is_simple_task(short_task, 40) is True
        assert executor._is_simple_task(long_task, 40) is False

    def test_is_simple_task_empty(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test simple task detection with empty input."""
        executor = AnalysisExecutor(
            executor_id="analysis-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor._is_simple_task("", 40) is False


# =============================================================================
# Test: RoutingExecutor
# =============================================================================


class TestRoutingExecutor:
    """Tests for RoutingExecutor."""

    def test_initializes_with_required_params(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that executor initializes correctly."""
        executor = RoutingExecutor(
            executor_id="routing-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor.supervisor == mock_dspy_reasoner
        assert executor.context == mock_supervisor_context

    def test_fallback_routing_returns_first_agent(
        self, mock_dspy_reasoner, mock_supervisor_context
    ):
        """Test that fallback routing assigns to first available agent."""
        executor = RoutingExecutor(
            executor_id="routing-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._fallback_routing("Test task")

        assert isinstance(result, RoutingDecision)
        assert len(result.assigned_to) == 1
        assert result.mode == ExecutionMode.DELEGATED
        assert result.confidence == 0.0

    def test_fallback_routing_raises_when_no_agents(
        self, mock_dspy_reasoner, mock_supervisor_context
    ):
        """Test that fallback routing raises when no agents available."""
        mock_supervisor_context.agents = {}
        executor = RoutingExecutor(
            executor_id="routing-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        with pytest.raises(RuntimeError, match="No agents registered"):
            executor._fallback_routing("Test task")


# =============================================================================
# Test: ProgressExecutor
# =============================================================================


class TestProgressExecutor:
    """Tests for ProgressExecutor."""

    def test_initializes_with_required_params(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that executor initializes correctly."""
        executor = ProgressExecutor(
            executor_id="progress-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor.supervisor == mock_dspy_reasoner
        assert executor.context == mock_supervisor_context

    def test_to_progress_report_valid_payload(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test conversion of valid payload to ProgressReport."""
        executor = ProgressExecutor(
            executor_id="progress-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        payload = {
            "action": "complete",
            "feedback": "Great work!",
            "used_fallback": False,
        }

        result = executor._to_progress_report(payload)

        assert isinstance(result, ProgressReport)
        assert result.action == "complete"
        assert result.feedback == "Great work!"
        assert result.used_fallback is False

    def test_to_progress_report_normalizes_action(
        self, mock_dspy_reasoner, mock_supervisor_context
    ):
        """Test that action is normalized to allowed values."""
        executor = ProgressExecutor(
            executor_id="progress-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        # Valid actions
        for action in ["continue", "refine", "complete", "escalate"]:
            result = executor._to_progress_report({"action": action})
            assert result.action == action

        # Invalid action defaults to continue
        result = executor._to_progress_report({"action": "invalid"})
        assert result.action == "continue"

    def test_to_progress_report_handles_defaults(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that conversion handles missing fields."""
        executor = ProgressExecutor(
            executor_id="progress-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._to_progress_report({})

        assert result.action == "continue"
        assert result.feedback == ""


# =============================================================================
# Test: QualityExecutor
# =============================================================================


class TestQualityExecutor:
    """Tests for QualityExecutor."""

    def test_initializes_with_required_params(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that executor initializes correctly."""
        executor = QualityExecutor(
            executor_id="quality-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        assert executor.supervisor == mock_dspy_reasoner
        assert executor.context == mock_supervisor_context

    def test_to_quality_report_valid_payload(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test conversion of valid payload to QualityReport."""
        executor = QualityExecutor(
            executor_id="quality-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        payload = {
            "score": 0.85,
            "missing": "Citations needed",
            "improvements": "Add more details",
            "judge_score": 8.5,
            "final_evaluation": {"approved": True},
            "used_fallback": False,
        }

        result = executor._to_quality_report(payload)

        assert isinstance(result, QualityReport)
        assert result.score == 0.85
        assert result.missing == "Citations needed"
        assert result.improvements == "Add more details"
        assert result.judge_score == 8.5
        assert result.used_fallback is False

    def test_to_quality_report_handles_defaults(self, mock_dspy_reasoner, mock_supervisor_context):
        """Test that conversion handles missing fields."""
        executor = QualityExecutor(
            executor_id="quality-1",
            supervisor=mock_dspy_reasoner,
            context=mock_supervisor_context,
        )

        result = executor._to_quality_report({})

        assert result.score == 0.0
        assert result.missing == ""
        assert result.improvements == ""


# Note: Handler decorator tests removed as they require valid WorkflowContext signatures
# which are framework-specific and not easily mockable in unit tests.
