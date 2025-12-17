from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.core.middleware import ChatMiddleware
from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.models import FinalResultMessage, QualityReport
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


class MockMiddleware(ChatMiddleware):
    def __init__(self):
        self.on_start_called = False
        self.on_end_called = False
        self.start_context = None
        self.end_result = None

    async def on_start(self, task, context):
        self.on_start_called = True
        self.start_context = context
        self.start_context["task"] = task

    async def on_end(self, result):
        self.on_end_called = True
        self.end_result = result


@pytest.mark.asyncio
async def test_supervisor_calls_middleware():
    # Setup context with middleware
    middleware = MockMiddleware()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [middleware]
    context.config = MagicMock()

    # Setup workflow
    workflow_runner = AsyncMock()

    # Create a valid FinalResultMessage
    final_msg = FinalResultMessage(
        result="Success",
        routing=RoutingDecision(
            task="Test task",
            assigned_to=("Agent1",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Test task",),
        ),
        quality=QualityReport(score=1.0),
        judge_evaluations=[],
        execution_summary={},
        phase_timings={},
        phase_status={},
        metadata={},
    )

    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = [final_msg]
    workflow_runner.run.return_value = workflow_result

    dspy_reasoner = MagicMock()

    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=dspy_reasoner,
        mode="standard",
    )

    # Mock _should_fast_path to return False so we run the full workflow
    # We can't easily patch a method on an instance if it's bound, but we can assign a new mock
    supervisor._should_fast_path = MagicMock(return_value=False)

    # Run workflow
    await supervisor.run("Test task")

    # Verify middleware calls
    assert middleware.on_start_called
    assert middleware.start_context is not None
    assert middleware.start_context["task"] == "Test task"
    assert middleware.on_end_called
    assert middleware.end_result is not None
    assert middleware.end_result["result"] == "Success"


@pytest.mark.asyncio
async def test_supervisor_calls_middleware_fast_path():
    # Setup context with middleware
    middleware = MockMiddleware()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [middleware]
    context.config = MagicMock()

    # Setup workflow
    workflow_runner = AsyncMock()

    # Create a valid FinalResultMessage
    final_msg = FinalResultMessage(
        result="Success",
        routing=RoutingDecision(
            task="Test task fast",
            assigned_to=("Agent1",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Test task fast",),
        ),
        quality=QualityReport(score=1.0),
        judge_evaluations=[],
        execution_summary={},
        phase_timings={},
        phase_status={},
        metadata={},
    )

    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = [final_msg]
    workflow_runner.run.return_value = workflow_result

    dspy_reasoner = MagicMock()
    dspy_reasoner.generate_simple_response = MagicMock(return_value="Fast path response")

    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=dspy_reasoner,
        mode="standard",
    )

    # Mock _should_fast_path to return True so the fast-path code path is run
    supervisor._should_fast_path = MagicMock(return_value=True)

    # Run workflow
    await supervisor.run("Test task fast")

    # Verify fast-path logic was checked
    supervisor._should_fast_path.assert_called_once()

    # Fast-path should still call middleware hooks (on_start before fast-path, on_end after)
    assert middleware.on_start_called
    assert middleware.on_end_called


@pytest.mark.asyncio
async def test_supervisor_middleware_error_handling():
    # Middleware whose on_start throws
    class FailingMiddleware(ChatMiddleware):
        async def on_start(self, task, context):
            raise RuntimeError("on_start error")

        async def on_end(self, result):
            self.called = True  # Should not be called in this case

    middleware = FailingMiddleware()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [middleware]
    context.config = MagicMock()

    workflow_runner = AsyncMock()
    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = []
    workflow_runner.run.return_value = workflow_result

    dspy_reasoner = MagicMock()
    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=dspy_reasoner,
        mode="standard",
    )
    supervisor._should_fast_path = MagicMock(return_value=False)

    with pytest.raises(RuntimeError, match="on_start error"):
        await supervisor.run("Test task")


@pytest.mark.asyncio
async def test_supervisor_middleware_chaining():
    call_log = []

    class MW1(ChatMiddleware):
        async def on_start(self, task, context):
            call_log.append("MW1_start")

        async def on_end(self, result):
            call_log.append("MW1_end")

    class MW2(ChatMiddleware):
        async def on_start(self, task, context):
            call_log.append("MW2_start")

        async def on_end(self, result):
            call_log.append("MW2_end")

    mw1 = MW1()
    mw2 = MW2()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [mw1, mw2]
    context.config = MagicMock()

    workflow_runner = AsyncMock()
    final_msg = FinalResultMessage(
        result="Success",
        routing=RoutingDecision(
            task="Test task",
            assigned_to=("Agent1",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Test task",),
        ),
        quality=QualityReport(score=1.0),
        judge_evaluations=[],
        execution_summary={},
        phase_timings={},
        phase_status={},
        metadata={},
    )
    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = [final_msg]
    workflow_runner.run.return_value = workflow_result

    dspy_reasoner = MagicMock()
    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=dspy_reasoner,
        mode="standard",
    )
    supervisor._should_fast_path = MagicMock(return_value=False)

    await supervisor.run("Test task")
    # Both should be called; on_end hooks are called in same order as on_start
    assert call_log == ["MW1_start", "MW2_start", "MW1_end", "MW2_end"]


@pytest.mark.asyncio
async def test_supervisor_empty_middleware_list():
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = []
    context.config = MagicMock()

    workflow_runner = AsyncMock()
    final_msg = FinalResultMessage(
        result="Success",
        routing=RoutingDecision(
            task="Test task",
            assigned_to=("Agent1",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Test task",),
        ),
        quality=QualityReport(score=1.0),
        judge_evaluations=[],
        execution_summary={},
        phase_timings={},
        phase_status={},
        metadata={},
    )
    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = [final_msg]
    workflow_runner.run.return_value = workflow_result

    dspy_reasoner = MagicMock()
    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=dspy_reasoner,
        mode="standard",
    )
    supervisor._should_fast_path = MagicMock(return_value=False)

    # Should not raise and finish successfully
    await supervisor.run("Test task")
    # Nothing to assert as no hooks, but we assert no error
