from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.utils.models import ExecutionMode
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.executors import AnalysisExecutor, ProgressExecutor, RoutingExecutor
from agentic_fleet.workflows.messages import (
    AnalysisMessage,
    ExecutionMessage,
    RoutingMessage,
    TaskMessage,
)
from agentic_fleet.workflows.models import (
    ExecutionOutcome,
)


# Mock context helper
def create_mock_context():
    config = SimpleNamespace(
        pipeline_profile="full",
        simple_task_max_words=10,
        dspy_retry_attempts=1,
        dspy_retry_backoff_seconds=0.0,
        slow_execution_threshold=0.1,  # Set low threshold to trigger warnings if needed
    )
    context = MagicMock(spec=SupervisorContext)
    context.config = config
    context.analysis_cache = None
    context.agents = {"Researcher": SimpleNamespace(description="Research & search")}
    context.latest_phase_timings = {}
    context.latest_phase_status = {}
    return context


# Mock supervisor helper
def create_mock_supervisor():
    supervisor = MagicMock()

    # Mock analyze_task
    supervisor.analyze_task = AsyncMock(
        return_value={
            "complexity": "simple",
            "required_capabilities": ["general_reasoning"],
            "tool_requirements": [],
            "estimated_steps": 3,
            "search_context": "",
            "needs_web_search": False,
            "search_query": "",
        }
    )

    # Mock route_task
    supervisor.route_task = AsyncMock(
        return_value={
            "assigned_to": ["Researcher"],
            "execution_mode": "delegated",
            "subtasks": ["Task"],
            "confidence": 0.9,
        }
    )

    # Mock evaluate_progress
    supervisor.evaluate_progress = AsyncMock(
        return_value={
            "action": "complete",
            "feedback": "",
        }
    )

    return supervisor


@pytest.mark.asyncio
async def test_phase_timings_and_statuses():
    context = create_mock_context()
    supervisor = create_mock_supervisor()

    # --- Analysis Phase ---
    analysis_executor = AnalysisExecutor("analysis", supervisor, context)
    task_msg = TaskMessage(task="Quick test task")

    # Mock ctx.send_message to capture output
    analysis_ctx = MagicMock()
    analysis_ctx.send_message = AsyncMock()

    await analysis_executor.handle_task(task_msg, analysis_ctx)

    # Verify timing and status recorded
    assert "analysis" in context.latest_phase_timings
    assert context.latest_phase_timings["analysis"] >= 0.0
    assert context.latest_phase_status.get("analysis") == "success"

    # Capture the analysis message for next step
    analysis_msg = analysis_ctx.send_message.call_args[0][0]
    assert isinstance(analysis_msg, AnalysisMessage)

    # --- Routing Phase ---
    routing_executor = RoutingExecutor("routing", supervisor, context)
    routing_ctx = MagicMock()
    routing_ctx.send_message = AsyncMock()

    await routing_executor.handle_analysis(analysis_msg, routing_ctx)

    assert "routing" in context.latest_phase_timings
    assert context.latest_phase_timings["routing"] >= 0.0
    assert context.latest_phase_status.get("routing") == "success"

    # Capture routing message
    routing_msg = routing_ctx.send_message.call_args[0][0]
    assert isinstance(routing_msg, RoutingMessage)

    # --- Progress Phase ---
    # Skip execution phase as it requires more setup, go straight to progress
    progress_executor = ProgressExecutor("progress", supervisor, context)

    # Create a dummy execution message
    outcome = ExecutionOutcome(
        result="Task complete",
        mode=ExecutionMode.DELEGATED,
        assigned_agents=["Researcher"],
        subtasks=["Task"],
        status="success",
    )
    execution_msg = ExecutionMessage(task="Quick test task", outcome=outcome, metadata={})

    progress_ctx = MagicMock()
    progress_ctx.send_message = AsyncMock()

    await progress_executor.handle_execution(execution_msg, progress_ctx)

    assert "progress" in context.latest_phase_timings
    assert context.latest_phase_timings["progress"] >= 0.0
    assert context.latest_phase_status.get("progress") == "success"
