from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentic_fleet.core.middleware import ChatMiddleware
from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.models import FinalResultMessage, QualityReport
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


class CaptureMiddleware(ChatMiddleware):
    def __init__(self):
        self.end_result = None

    async def on_start(self, task, context):
        return None

    async def on_end(self, result):
        self.end_result = result


@pytest.mark.asyncio
async def test_run_schedules_background_quality_eval_for_group_chat_mode():
    middleware = CaptureMiddleware()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [middleware]
    context.config = MagicMock()

    workflow_runner = AsyncMock()
    workflow_runner.run.return_value = [MagicMock(text="Final answer")]

    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=MagicMock(),
        mode="group_chat",
    )
    supervisor._should_fast_path = MagicMock(return_value=False)

    with patch("agentic_fleet.services.background_evaluation.schedule_quality_evaluation") as sched:
        result = await supervisor.run("Test task")

    assert result["quality"]["pending"] is True
    assert middleware.end_result is not None
    assert middleware.end_result["quality"]["pending"] is True
    sched.assert_called_once()


@pytest.mark.asyncio
async def test_run_schedules_background_quality_eval_for_standard_placeholder_score():
    middleware = CaptureMiddleware()
    context = MagicMock(spec=SupervisorContext)
    context.middlewares = [middleware]
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
        quality=QualityReport(score=0.0),
        judge_evaluations=[],
        execution_summary={},
        phase_timings={},
        phase_status={},
        metadata={},
    )

    workflow_result = MagicMock()
    workflow_result.get_outputs.return_value = [final_msg]
    workflow_runner.run.return_value = workflow_result

    supervisor = SupervisorWorkflow(
        context=context,
        workflow_runner=workflow_runner,
        dspy_supervisor=MagicMock(),
        mode="standard",
    )
    supervisor._should_fast_path = MagicMock(return_value=False)

    with patch("agentic_fleet.services.background_evaluation.schedule_quality_evaluation") as sched:
        result = await supervisor.run("Test task")

    assert result["quality"]["pending"] is True
    assert middleware.end_result is not None
    assert middleware.end_result["quality"]["pending"] is True
    sched.assert_called_once()
