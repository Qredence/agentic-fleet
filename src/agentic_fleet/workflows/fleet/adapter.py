"""Supervisor workflow implementation backed by agent-framework WorkflowBuilder."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

if TYPE_CHECKING:
    # Workflow is only needed for type checking; runtime uses Protocol methods.
    from agent_framework import Workflow

from ...utils.logger import setup_logger
from ...utils.models import RoutingDecision, ensure_routing_decision
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
        context: SupervisorContext | None = None,
        workflow_runner: Workflow | None = None,
        dspy_supervisor: Any | None = None,
        **_: Any,
    ) -> None:
        """Initialize SupervisorWorkflow.

        Args:
            context: Supervisor context with configuration and state
            workflow_runner: agent-framework Workflow instance
        """
        self.context = context  # may be None for compatibility in tests
        self.config = getattr(context, "config", None)
        self.workflow = workflow_runner
        # Allow explicit override for tests that pass dspy_supervisor
        self.dspy_supervisor = dspy_supervisor or (
            getattr(context, "dspy_supervisor", None) if context else None
        )
        self.agents = getattr(context, "agents", None) if context else None
        self.handoff_manager = getattr(context, "handoff_manager", None) if context else None
        self.history_manager = getattr(context, "history_manager", None) if context else None
        self.execution_history: list[dict[str, Any]] = []
        self.current_execution: dict[str, Any] = {}
        # Back-compat attributes referenced by some tests
        self._compilation_task = getattr(context, "compilation_task", None) if context else None
        self._compilation_status = (
            getattr(context, "compilation_status", "pending") if context else "pending"
        )
        self._compiled_supervisor = None

    async def run(self, task: str) -> dict[str, Any]:
        """Execute workflow for a task (non-streaming).

        Args:
            task: Task to execute

        Returns:
            Dictionary with result, routing, quality, etc.
        """
        logger.info(f"Running fleet workflow for task: {task[:100]}...")

        # Create task message
        task_msg = TaskMessage(task=task)

        # Run workflow
        try:
            result = await self.workflow.run(task_msg)
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            raise

        # Extract final result from workflow outputs
        outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
        if not outputs:
            raise RuntimeError("Workflow did not produce any outputs")

        final_msg = outputs[-1]
        if not isinstance(final_msg, FinalResultMessage):
            raise RuntimeError(f"Expected FinalResultMessage, got {type(final_msg)}")

        # Convert to dict format for backward compatibility
        return self._final_message_to_dict(final_msg)

    async def run_stream(self, task: str):
        """Execute workflow with streaming events.

        Args:
            task: Task to execute

        Yields:
            MagenticAgentMessageEvent and WorkflowOutputEvent instances
        """
        logger.info(f"Running fleet workflow (streaming) for task: {task[:100]}...")

        execution_start = datetime.now()
        self.current_execution = {
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

        # Create task message
        task_msg = TaskMessage(task=task)

        # Stream workflow execution
        try:
            final_msg: FinalResultMessage | None = None

            async for event in self.workflow.run_stream(task_msg):
                # Forward agent-framework events
                if isinstance(event, MagenticAgentMessageEvent):
                    yield event
                elif isinstance(event, WorkflowOutputEvent):
                    # Extract FinalResultMessage from output
                    if hasattr(event, "data"):
                        data = event.data
                        if isinstance(data, FinalResultMessage):
                            final_msg = data
                        elif isinstance(data, dict) and "result" in data:
                            # Convert dict to FinalResultMessage if needed
                            final_msg = self._dict_to_final_message(data)
                    yield event
                else:
                    # Convert other events to MagenticAgentMessageEvent
                    yield MagenticAgentMessageEvent(
                        agent_id="fleet",
                        message=ChatMessage(
                            role=Role.ASSISTANT,
                            text=str(event),
                        ),
                    )

            # Ensure we have a final result
            if final_msg is None:
                # Try to get from workflow run result
                try:
                    result = await self.workflow.run(task_msg)
                    outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
                    if outputs:
                        final_output = outputs[-1]
                        if isinstance(final_output, FinalResultMessage):
                            final_msg = final_output
                except Exception as e:
                    logger.warning(f"Could not get final result from workflow: {e}")

            if final_msg is None:
                logger.warning("No final message found, creating fallback")
                final_msg = await self._create_fallback_result(task)

            # Yield final WorkflowOutputEvent
            yield WorkflowOutputEvent(
                data=self._final_message_to_dict(final_msg),
                source_executor_id="fleet",
            )

            # Update execution tracking
            execution_end = datetime.now()
            execution_start_dt = datetime.fromisoformat(self.current_execution["start_time"])
            total_time = (execution_end - execution_start_dt).total_seconds()
            self.current_execution["end_time"] = execution_end.isoformat()
            self.current_execution["total_time_seconds"] = total_time

            # Save history
            self.execution_history.append(self.current_execution.copy())
            if self.history_manager:
                await self.history_manager.save_execution_async(self.current_execution)

        except Exception as e:
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
        from ...utils.models import ExecutionMode

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

    def _require_supervisor(self):
        """Return supervisor or raise error."""
        if self.dspy_supervisor is None:
            raise RuntimeError("DSPy supervisor not initialized")
        return self.dspy_supervisor

    def _require_agents(self) -> dict[str, Any]:
        """Return agents or raise error."""
        if self.agents is None:
            raise RuntimeError("Agents are not initialized")
        return self.agents

    # ------------------------------------------------------------------
    # Backward-compatibility helpers expected by legacy tests
    # ------------------------------------------------------------------
    def _create_agents(self) -> dict[str, Any]:
        """Return prepared agents dictionary (compat shim for legacy tests)."""
        return self._require_agents()


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
