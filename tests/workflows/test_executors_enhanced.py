"""Enhanced comprehensive tests for workflows/executors.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.utils.models import ExecutionMode
from agentic_fleet.workflows.executors import (
    AnalysisExecutor,
    ProgressExecutor,
    QualityExecutor,
    RoutingExecutor,
)
from agentic_fleet.workflows.models import (
    AnalysisMessage,
    AnalysisResult,
    ExecutionMessage,
    ExecutionOutcome,
    ProgressMessage,
    ProgressReport,
    RoutingMessage,
    TaskMessage,
)


class TestAnalysisExecutor:
    """Test suite for AnalysisExecutor."""

    class _StubMsg:
        def __init__(self, role: str, text: str):
            self.role = role
            self.text = text

    class _StubStore:
        def __init__(self, messages):
            self.messages = messages

    class _StubThread:
        def __init__(self, messages):
            self.message_store = TestAnalysisExecutor._StubStore(messages)

    @pytest.fixture
    def mock_supervisor(self):
        supervisor = MagicMock()
        supervisor.analyze_task = AsyncMock(
            return_value={
                "complexity": "moderate",
                "capabilities": ["reasoning"],
                "steps": 3,
                "needs_web_search": False,
            }
        )
        return supervisor

    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.config = MagicMock()
        context.config.pipeline_profile = "full"
        context.config.simple_task_max_words = 40
        context.config.dspy_retry_attempts = 1
        context.config.dspy_retry_backoff_seconds = 0.0
        context.analysis_cache = MagicMock()
        context.analysis_cache.get.return_value = None
        context.latest_phase_status = {}
        context.latest_phase_timings = {}
        return context

    @pytest.fixture
    def executor(self, mock_supervisor, mock_context):
        return AnalysisExecutor("analysis", mock_supervisor, mock_context)

    async def test_handle_task_success(self, executor, mock_supervisor):
        task_msg = TaskMessage(task="Analyze this", metadata={})
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_task(task_msg, ctx)

        mock_supervisor.analyze_task.assert_called_once()
        ctx.send_message.assert_called_once()
        call_args = ctx.send_message.call_args[0][0]
        assert isinstance(call_args, AnalysisMessage)
        assert call_args.task == "Analyze this"
        assert call_args.analysis.complexity == "moderate"

    async def test_handle_task_injects_conversation_context(
        self, executor, mock_supervisor, mock_context
    ):
        # Simulate a previous assistant question so a short follow-up can be interpreted.
        mock_context.conversation_thread = self._StubThread(
            [
                self._StubMsg(
                    "assistant",
                    "Which theme(s) would you like more recommendations for? Tell me the reading level.",
                )
            ]
        )

        task_msg = TaskMessage(task="popular, intermediate", metadata={})
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_task(task_msg, ctx)

        called_task = mock_supervisor.analyze_task.call_args.args[0]
        assert "Conversation context" in called_task
        assert "Which theme(s) would you like more recommendations for?" in called_task
        assert "popular, intermediate" in called_task

    async def test_handle_task_fallback(self, executor, mock_supervisor):
        mock_supervisor.analyze_task.side_effect = Exception("DSPy error")
        task_msg = TaskMessage(task="Analyze this", metadata={})
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_task(task_msg, ctx)

        ctx.send_message.assert_called_once()
        call_args = ctx.send_message.call_args[0][0]
        assert isinstance(call_args, AnalysisMessage)
        assert call_args.metadata["used_fallback"] is True


class TestRoutingExecutor:
    """Test suite for RoutingExecutor."""

    @pytest.fixture
    def mock_supervisor(self):
        supervisor = MagicMock()
        supervisor.route_task = AsyncMock(
            return_value={
                "assigned_to": ["Researcher"],
                "mode": "delegated",
                "subtasks": ["subtask1"],
                "confidence": 0.9,
            }
        )
        return supervisor

    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.config = MagicMock()
        context.config.pipeline_profile = "full"
        context.config.dspy_retry_attempts = 1
        context.config.dspy_retry_backoff_seconds = 0.0
        context.agents = {"Researcher": MagicMock()}
        context.latest_phase_status = {}
        context.latest_phase_timings = {}
        return context

    @pytest.fixture
    def executor(self, mock_supervisor, mock_context):
        return RoutingExecutor("routing", mock_supervisor, mock_context)

    async def test_handle_analysis_success(self, executor, mock_supervisor):
        analysis_msg = AnalysisMessage(
            task="Route this",
            analysis=AnalysisResult(
                complexity="moderate",
                capabilities=[],
                tool_requirements=[],
                steps=1,
                search_context="",
                needs_web_search=False,
                search_query="",
            ),
            metadata={},
        )
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_analysis(analysis_msg, ctx)

        mock_supervisor.route_task.assert_called_once()
        ctx.send_message.assert_called_once()
        call_args = ctx.send_message.call_args[0][0]
        assert isinstance(call_args, RoutingMessage)
        assert call_args.routing.decision.assigned_to == ("Researcher",)

    async def test_handle_analysis_includes_conversation_context_and_skips_cache(
        self, executor, mock_supervisor
    ):
        analysis_msg = AnalysisMessage(
            task="popular, intermediate",
            analysis=AnalysisResult(
                complexity="moderate",
                capabilities=[],
                tool_requirements=[],
                steps=1,
                search_context="",
                needs_web_search=False,
                search_query="",
            ),
            metadata={
                "conversation_context": "Assistant: Which theme(s) would you like more recommendations for?",
            },
        )
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_analysis(analysis_msg, ctx)

        kwargs = mock_supervisor.route_task.call_args.kwargs
        assert "Conversation context" in (kwargs.get("context") or "")
        assert kwargs.get("skip_cache") is True

    async def test_handle_analysis_fallback(self, executor, mock_supervisor):
        mock_supervisor.route_task.side_effect = Exception("Routing error")
        analysis_msg = AnalysisMessage(
            task="Route this",
            analysis=AnalysisResult(
                complexity="moderate",
                capabilities=[],
                tool_requirements=[],
                steps=1,
                search_context="",
                needs_web_search=False,
                search_query="",
            ),
            metadata={},
        )
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_analysis(analysis_msg, ctx)

        ctx.send_message.assert_called_once()
        call_args = ctx.send_message.call_args[0][0]
        assert isinstance(call_args, RoutingMessage)
        assert call_args.routing.used_fallback is True


class TestProgressExecutor:
    """Test suite for ProgressExecutor."""

    @pytest.fixture
    def mock_supervisor(self):
        supervisor = MagicMock()
        supervisor.evaluate_progress = AsyncMock(
            return_value={"action": "continue", "feedback": "Keep going"}
        )
        return supervisor

    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.config = MagicMock()
        context.config.pipeline_profile = "full"
        context.config.enable_progress_eval = True
        context.config.dspy_retry_attempts = 1
        context.config.dspy_retry_backoff_seconds = 0.0
        context.latest_phase_status = {}
        context.latest_phase_timings = {}
        return context

    @pytest.fixture
    def executor(self, mock_supervisor, mock_context):
        return ProgressExecutor("progress", mock_supervisor, mock_context)

    async def test_handle_execution_success(self, executor, mock_supervisor):
        execution_msg = ExecutionMessage(
            task="Execute this",
            outcome=ExecutionOutcome(
                result="Done",
                mode=ExecutionMode.DELEGATED,
                assigned_agents=["Researcher"],
                subtasks=[],
                status="success",
                artifacts={},
            ),
            metadata={},
        )
        ctx = MagicMock()
        ctx.send_message = AsyncMock()

        await executor.handle_execution(execution_msg, ctx)

        mock_supervisor.evaluate_progress.assert_called_once()
        ctx.send_message.assert_called_once()
        call_args = ctx.send_message.call_args[0][0]
        assert isinstance(call_args, ProgressMessage)
        assert call_args.progress.action == "continue"


class TestQualityExecutor:
    """Test suite for QualityExecutor."""

    @pytest.fixture
    def mock_supervisor(self):
        supervisor = MagicMock()
        supervisor.assess_quality = AsyncMock(
            return_value={"score": 9.0, "missing": "", "improvements": ""}
        )
        return supervisor

    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.config = MagicMock()
        context.config.pipeline_profile = "full"
        context.config.enable_quality_eval = True
        context.config.dspy_retry_attempts = 1
        context.config.dspy_retry_backoff_seconds = 0.0
        context.latest_phase_status = {}
        context.latest_phase_timings = {}
        context.dspy_supervisor = MagicMock()
        context.dspy_supervisor.get_execution_summary.return_value = {}
        return context

    @pytest.fixture
    def executor(self, mock_supervisor, mock_context):
        return QualityExecutor("quality", mock_supervisor, mock_context)

    async def test_handle_progress_success(self, executor, mock_supervisor):
        progress_msg = ProgressMessage(
            task="Check quality",
            result="Good result",
            progress=ProgressReport(action="complete", feedback="", used_fallback=False),
            metadata={},
        )
        ctx = MagicMock()
        ctx.yield_output = AsyncMock()

        await executor.handle_progress(progress_msg, ctx)

        mock_supervisor.assess_quality.assert_called_once()
        ctx.yield_output.assert_called_once()
