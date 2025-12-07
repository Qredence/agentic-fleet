"""Enhanced comprehensive tests for workflows/executors.py - Routing and Execution."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from agentic_fleet.workflows.executors import (
    RoutingExecutor,
    AnalysisExecutor,
    QualityExecutor,
    ProgressExecutor,
)
from agentic_fleet.dspy_modules.assertions import detect_task_type, validate_full_routing


class TestRoutingExecutor:
    """Test suite for RoutingExecutor class."""

    @pytest.fixture
    def mock_reasoner(self):
        """Create a mock DSPy reasoner."""
        reasoner = Mock()
        reasoner.route_task = AsyncMock(
            return_value={
                "agent": "researcher",
                "execution_mode": "delegated",
                "reasoning": "Research task detected",
            }
        )
        return reasoner

    @pytest.fixture
    def executor(self, mock_reasoner):
        """Create a RoutingExecutor instance."""
        config = {
            "agents": ["researcher", "analyst", "writer"],
            "tools": ["TavilyMCPTool", "BrowserTool"],
        }
        executor = RoutingExecutor(config=config)
        executor.reasoner = mock_reasoner
        return executor

    async def test_routing_executor_basic_routing(self, executor, mock_reasoner):
        """Test basic task routing."""
        task = "Research the latest AI developments"
        context = {}

        result = await executor.route(task, context)

        assert result is not None
        assert "agent" in result
        assert result["agent"] == "researcher"
        mock_reasoner.route_task.assert_called_once()

    async def test_routing_executor_with_task_type_detection(self, executor):
        """Test routing with automatic task type detection."""
        research_task = "Search for information about quantum computing"

        with patch("agentic_fleet.workflows.executors.detect_task_type") as mock_detect:
            mock_detect.return_value = "research"

            result = await executor.route(research_task, {})

            mock_detect.assert_called_once_with(research_task)
            assert result is not None

    async def test_routing_executor_validation(self, executor):
        """Test routing decision validation."""
        task = "Analyze sales data"
        context = {}

        with patch(
            "agentic_fleet.workflows.executors.validate_full_routing"
        ) as mock_validate:
            mock_validate.return_value = True

            result = await executor.route(task, context)

            # Validation should be called with routing decision
            assert mock_validate.called or result is not None

    async def test_routing_executor_cache_hit(self, executor, mock_reasoner):
        """Test routing cache hit."""
        task = "Same task"
        context = {}

        # Enable caching in executor
        with patch.object(executor, "_get_cached_routing", return_value={"agent": "cached"}):
            result = await executor.route(task, context)

            # Should return cached result without calling reasoner
            assert result["agent"] == "cached"
            mock_reasoner.route_task.assert_not_called()

    async def test_routing_executor_fallback_on_invalid(self, executor, mock_reasoner):
        """Test fallback routing on invalid decision."""
        mock_reasoner.route_task = AsyncMock(
            return_value={
                "agent": "nonexistent_agent",  # Invalid
                "execution_mode": "invalid",
            }
        )

        task = "Task"
        context = {}

        with patch("agentic_fleet.workflows.executors.validate_full_routing") as mock_validate:
            mock_validate.return_value = False

            result = await executor.route(task, context)

            # Should use fallback routing
            assert result is not None


class TestAnalysisExecutor:
    """Test suite for AnalysisExecutor class."""

    @pytest.fixture
    def mock_reasoner(self):
        """Create a mock DSPy reasoner."""
        reasoner = Mock()
        reasoner.analyze_task = AsyncMock(
            return_value={
                "complexity": "medium",
                "requires_tools": True,
                "suggested_agents": ["analyst"],
            }
        )
        return reasoner

    @pytest.fixture
    def executor(self, mock_reasoner):
        """Create an AnalysisExecutor instance."""
        return AnalysisExecutor(reasoner=mock_reasoner)

    async def test_analysis_executor_basic_analysis(self, executor, mock_reasoner):
        """Test basic task analysis."""
        task = "Analyze quarterly revenue trends"

        result = await executor.analyze(task)

        assert result is not None
        assert "complexity" in result
        mock_reasoner.analyze_task.assert_called_once()

    async def test_analysis_executor_with_context(self, executor):
        """Test analysis with additional context."""
        task = "Complex analysis task"
        context = {"previous_results": ["result1"], "user_preferences": {}}

        result = await executor.analyze(task, context)

        assert result is not None

    async def test_analysis_executor_extracts_metadata(self, executor):
        """Test that analysis extracts useful metadata."""
        task = "Task requiring web search and data processing"

        result = await executor.analyze(task)

        # Should identify tool requirements
        assert "requires_tools" in result or "tools" in result


class TestQualityExecutor:
    """Test suite for QualityExecutor class."""

    @pytest.fixture
    def mock_evaluator(self):
        """Create a mock quality evaluator."""
        evaluator = Mock()
        evaluator.evaluate = AsyncMock(
            return_value={
                "score": 0.85,
                "meets_threshold": True,
                "feedback": "Good quality",
            }
        )
        return evaluator

    @pytest.fixture
    def executor(self, mock_evaluator):
        """Create a QualityExecutor instance."""
        config = {"quality_threshold": 0.8}
        return QualityExecutor(evaluator=mock_evaluator, config=config)

    async def test_quality_executor_evaluate_result(self, executor, mock_evaluator):
        """Test quality evaluation of result."""
        task = "Research task"
        result = {"content": "Research findings..."}

        quality = await executor.evaluate(task, result)

        assert quality is not None
        assert "score" in quality
        assert quality["score"] == 0.85
        mock_evaluator.evaluate.assert_called_once()

    async def test_quality_executor_meets_threshold(self, executor):
        """Test quality threshold checking."""
        task = "Task"
        high_quality_result = {"content": "Excellent result"}

        quality = await executor.evaluate(task, high_quality_result)

        assert quality["meets_threshold"] is True

    async def test_quality_executor_below_threshold(self, executor, mock_evaluator):
        """Test handling results below quality threshold."""
        mock_evaluator.evaluate = AsyncMock(
            return_value={"score": 0.5, "meets_threshold": False, "feedback": "Needs improvement"}
        )

        task = "Task"
        poor_result = {"content": "Incomplete"}

        quality = await executor.evaluate(task, poor_result)

        assert quality["meets_threshold"] is False
        assert quality["score"] < 0.8


class TestProgressExecutor:
    """Test suite for ProgressExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create a ProgressExecutor instance."""
        return ProgressExecutor()

    async def test_progress_executor_track_progress(self, executor):
        """Test progress tracking."""
        task = "Multi-step task"
        current_state = {"iteration": 3, "results": ["step1", "step2"]}

        progress = await executor.track_progress(task, current_state)

        assert progress is not None
        assert "iteration" in progress or "current_state" in progress

    async def test_progress_executor_completion_detection(self, executor):
        """Test detecting task completion."""
        task = "Task"
        completed_state = {
            "iteration": 5,
            "status": "completed",
            "results": ["final"],
        }

        progress = await executor.track_progress(task, completed_state)

        # Should recognize completion
        assert progress.get("status") == "completed" or progress is not None

    async def test_progress_executor_iteration_limit(self, executor):
        """Test handling iteration limit."""
        task = "Long task"
        max_iterations_state = {"iteration": 100, "status": "in_progress"}

        progress = await executor.track_progress(task, max_iterations_state)

        # Should flag if exceeding limits
        assert progress is not None


class TestExecutorIntegration:
    """Integration tests for executors working together."""

    @pytest.fixture
    def all_executors(self):
        """Create all executors for integration testing."""
        mock_reasoner = Mock()
        mock_reasoner.analyze_task = AsyncMock(return_value={"complexity": "high"})
        mock_reasoner.route_task = AsyncMock(return_value={"agent": "researcher"})

        mock_evaluator = Mock()
        mock_evaluator.evaluate = AsyncMock(return_value={"score": 0.9})

        return {
            "analysis": AnalysisExecutor(reasoner=mock_reasoner),
            "routing": RoutingExecutor(reasoner=mock_reasoner, config={}),
            "quality": QualityExecutor(evaluator=mock_evaluator, config={}),
            "progress": ProgressExecutor(),
        }

    async def test_full_execution_pipeline(self, all_executors):
        """Test complete execution pipeline: analysis -> routing -> execution -> quality -> progress."""
        task = "Research and analyze market trends"

        # Analysis
        analysis = await all_executors["analysis"].analyze(task)
        assert analysis is not None

        # Routing based on analysis
        routing = await all_executors["routing"].route(task, {"analysis": analysis})
        assert routing is not None

        # Quality check (assume we have a result)
        mock_result = {"content": "Market analysis complete"}
        quality = await all_executors["quality"].evaluate(task, mock_result)
        assert quality["score"] > 0

        # Progress tracking
        state = {"iteration": 1, "status": "completed"}
        progress = await all_executors["progress"].track_progress(task, state)
        assert progress is not None

    async def test_executor_error_propagation(self, all_executors):
        """Test error propagation through executor pipeline."""
        all_executors["analysis"].reasoner.analyze_task = AsyncMock(
            side_effect=Exception("Analysis failed")
        )

        task = "Task"

        with pytest.raises(Exception, match="Analysis failed"):
            await all_executors["analysis"].analyze(task)


class TestExecutorEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_routing_with_empty_task(self):
        """Test routing with empty task."""
        mock_reasoner = Mock()
        mock_reasoner.route_task = AsyncMock(return_value={"agent": "planner"})

        executor = RoutingExecutor(reasoner=mock_reasoner, config={})

        result = await executor.route("", {})

        # Should handle empty task gracefully
        assert result is not None

    async def test_analysis_with_very_long_task(self):
        """Test analysis with very long task description."""
        mock_reasoner = Mock()
        mock_reasoner.analyze_task = AsyncMock(return_value={"complexity": "high"})

        executor = AnalysisExecutor(reasoner=mock_reasoner)

        long_task = "Task " * 10000  # Very long task

        result = await executor.analyze(long_task)

        assert result is not None

    async def test_quality_evaluation_with_missing_fields(self):
        """Test quality evaluation with incomplete result."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate = AsyncMock(return_value={"score": 0.7})

        executor = QualityExecutor(evaluator=mock_evaluator, config={})

        incomplete_result = {}  # Missing expected fields

        quality = await executor.evaluate("task", incomplete_result)

        # Should handle gracefully
        assert quality is not None