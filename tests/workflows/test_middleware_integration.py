from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.api.middlewares import ChatMiddleware
from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.messages import FinalResultMessage
from agentic_fleet.workflows.models import QualityReport
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
