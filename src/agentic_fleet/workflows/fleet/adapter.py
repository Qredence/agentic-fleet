"""Supervisor workflow implementation backed by agent-framework WorkflowBuilder.

This adapter is the canonical implementation used by the CLI and application
code.  It also provides a set of backward-compatibility shims so that legacy
tests which exercised the old, DSPy-centric ``SupervisorWorkflow`` API
continue to pass while the runtime migrates to the fleet workflow design.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

if TYPE_CHECKING:
    # Workflow is only needed for type checking; runtime uses Protocol methods.
    from agent_framework import Workflow

from ...utils.history_manager import HistoryManager
from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ...utils.tool_registry import ToolRegistry
from ..handoff_manager import HandoffManager
from ..orchestration import SupervisorContext
from ..shared.models import QualityReport
from ..shared.quality import quality_report_to_legacy
from .builder import build_fleet_workflow
from .messages import FinalResultMessage, TaskMessage

logger = setup_logger(__name__)


class SupervisorWorkflow:
    """Workflow that drives the AgenticFleet orchestration pipeline."""

    def __init__(
        self,
        context: SupervisorContext,
        workflow_runner: Workflow | None = None,
        dspy_supervisor: Any | None = None,
        *,
        agents: dict[str, Any] | None = None,
        history_manager: HistoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
        handoff_manager: HandoffManager | None = None,
        **_: Any,
    ) -> None:
        """Initialize SupervisorWorkflow.

        The constructor requires a ``SupervisorContext`` (fleet mode) and
        delegates to an agent-framework workflow agent.
        """
        if not isinstance(context, SupervisorContext):
            raise TypeError("SupervisorWorkflow requires a SupervisorContext instance.")

        self.context = context
        self.config = context.config
        self.workflow = workflow_runner

        # Allow explicit override for tests that pass dspy_supervisor; fall
        # back to context supervisor when available.
        self.dspy_supervisor = dspy_supervisor or getattr(self.context, "dspy_supervisor", None)

        # Agents, tool registry, and managers come from explicit parameters
        # first, then fall back to context-provided instances.
        self.agents = agents or getattr(self.context, "agents", None)
        self.tool_registry = tool_registry or getattr(self.context, "tool_registry", None)
        self.handoff_manager = handoff_manager or getattr(self.context, "handoff_manager", None)
        self.history_manager = history_manager or getattr(self.context, "history_manager", None)

        # Default managers if missing from context
        if self.history_manager is None:
            self.history_manager = HistoryManager()
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        # Handoff toggle
        self.enable_handoffs = bool(getattr(self.context, "enable_handoffs", True))

        # Optional analysis cache
        self.analysis_cache = getattr(self.context, "analysis_cache", None)

        self.execution_history: list[dict[str, Any]] = []
        self.current_execution: dict[str, Any] = {}

        # Back-compat attributes referenced by some tests (kept for now but initialized safely)
        self._compilation_task = getattr(context, "compilation_task", None)
        self._compilation_status = getattr(context, "compilation_status", "pending")
        self._compiled_supervisor = None

    async def run(self, task: str) -> dict[str, Any]:
        """Execute workflow for a task (non-streaming).

        Args:
            task: Task to execute

        Returns:
            Dictionary with result, routing, quality, etc.
        """
        if self.workflow is None:
            raise RuntimeError(
                "Workflow runner not initialized. Use create_fleet_workflow factory."
            )

        logger.info(f"Running fleet workflow for task: {task[:100]}...")

        task_msg = TaskMessage(task=task)
        try:
            result = await self.workflow.run(task_msg)
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            raise

        outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
        if not outputs:
            raise RuntimeError("Workflow did not produce any outputs")

        final_msg = outputs[-1]
        if not isinstance(final_msg, FinalResultMessage):
            raise RuntimeError(f"Expected FinalResultMessage, got {type(final_msg)}")

        return self._final_message_to_dict(final_msg)

    async def run_stream(self, task: str):
        """Execute workflow with streaming events.

        Args:
            task: Task to execute

        Yields:
            MagenticAgentMessageEvent and WorkflowOutputEvent instances
        """
        if self.workflow is None:
            raise RuntimeError(
                "Workflow runner not initialized. Use create_fleet_workflow factory."
            )

        logger.info(f"Running fleet workflow (streaming) for task: {task[:100]}...")

        execution_start = datetime.now()
        workflow_id = str(uuid4())
        self.current_execution = {
            "workflowId": workflow_id,
            "task": task,
            "start_time": execution_start.isoformat(),
            "events": [],
            "dspy_analysis": {},
            "routing": {},
            "progress": {},
            "agent_executions": [],
            "quality": {},
            "result": None,
            "phase_timings": {},
            "phase_status": {},
        }

        task_msg = TaskMessage(task=task)

        try:
            final_msg: FinalResultMessage | None = None

            async for event in self.workflow.run_stream(task_msg):
                if isinstance(event, MagenticAgentMessageEvent):
                    yield event
                elif isinstance(event, WorkflowOutputEvent):
                    if hasattr(event, "data"):
                        data = event.data
                        if isinstance(data, FinalResultMessage):
                            final_msg = data
                        elif isinstance(data, dict) and "result" in data:
                            final_msg = self._dict_to_final_message(data)
                    yield event
                else:
                    yield MagenticAgentMessageEvent(
                        agent_id="fleet",
                        message=ChatMessage(
                            role=Role.ASSISTANT,
                            text=str(event),
                        ),
                    )

            if final_msg is None:
                logger.warning("No final message found in stream, creating fallback result")
                final_msg = await self._create_fallback_result(task)

            yield WorkflowOutputEvent(
                data=self._final_message_to_dict(final_msg),
                source_executor_id="fleet",
            )

            execution_end = datetime.now()
            execution_start_dt = datetime.fromisoformat(self.current_execution["start_time"])
            total_time = (execution_end - execution_start_dt).total_seconds()
            self.current_execution["end_time"] = execution_end.isoformat()
            self.current_execution["total_time_seconds"] = total_time

            self.execution_history.append(self.current_execution.copy())
            if self.history_manager:
                await self.history_manager.save_execution_async(self.current_execution)

        except Exception as e:  # pragma: no cover - fleet path exercised elsewhere
            logger.exception(f"Workflow streaming failed: {e}")
            raise

    def _final_message_to_dict(self, final_msg: FinalResultMessage) -> dict[str, Any]:
        """Convert FinalResultMessage to dict format for backward compatibility."""
        # Convert quality report to dict
        quality_dict = quality_report_to_legacy(final_msg.quality)

        return {
            "result": final_msg.result,
            "routing": final_msg.routing.to_dict(),
            "quality": quality_dict,
            "judge_evaluations": final_msg.judge_evaluations,
            "execution_summary": final_msg.execution_summary,
            "phase_timings": final_msg.phase_timings,
            "phase_status": final_msg.phase_status,
        }

    def _dict_to_final_message(self, data: dict[str, Any]) -> FinalResultMessage:
        """Convert dict to FinalResultMessage."""
        from ..shared.quality import quality_report_from_legacy

        routing = ensure_routing_decision(data.get("routing", {}))
        quality = quality_report_from_legacy(data.get("quality", {}))

        return FinalResultMessage(
            result=data.get("result", ""),
            routing=routing,
            quality=quality,
            judge_evaluations=data.get("judge_evaluations", []),
            execution_summary=data.get("execution_summary", {}),
            phase_timings=data.get("phase_timings", {}),
            phase_status=data.get("phase_status", {}),
            metadata=data.get("metadata", {}),
        )

    async def _create_fallback_result(self, task: str) -> FinalResultMessage:
        """Create fallback result if workflow doesn't produce one."""

        return FinalResultMessage(
            result="Workflow execution completed but no result was produced",
            routing=RoutingDecision(
                task=task,
                assigned_to=(),
                mode=ExecutionMode.DELEGATED,
                subtasks=(),
                tool_requirements=(),
                confidence=None,
            ),
            quality=QualityReport(score=0.0, used_fallback=True),
            judge_evaluations=[],
            execution_summary={},
            phase_timings={},
            phase_status={},
            metadata={"fallback": True},
        )


async def create_fleet_workflow(
    context: SupervisorContext,
    compile_dspy: bool = True,
) -> SupervisorWorkflow:
    """Create and initialize the supervisor workflow.

    Args:
        context: Supervisor context with configuration and state
        compile_dspy: Whether to compile DSPy supervisor (unused, kept for compatibility)

    Returns:
        SupervisorWorkflow instance
    """
    # Maintain async signature for future extensibility; satisfy lint by explicit await.
    await asyncio.sleep(0)
    supervisor = context.dspy_supervisor
    if supervisor is None:
        raise RuntimeError("DSPy supervisor must be initialized in context")

    # Ensure supervisor has tool registry
    if context.tool_registry and not supervisor.tool_registry:
        supervisor.set_tool_registry(context.tool_registry)

    # Build workflow using WorkflowBuilder
    workflow_builder = build_fleet_workflow(supervisor, context)

    # Build workflow and wrap as agent
    workflow = workflow_builder.build()

    # Create workflow entrypoint
    workflow = SupervisorWorkflow(context, workflow)

    logger.info("Supervisor workflow created successfully")
    return workflow
