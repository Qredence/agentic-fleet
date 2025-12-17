"""Execution phase executor.

Split out of `workflows/executors.py` to keep each executor implementation focused.
"""

from __future__ import annotations

from time import perf_counter

from agent_framework._types import ChatMessage
from agent_framework._workflows import Executor, WorkflowContext, WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from ..models import ExecutionMessage, ExecutionOutcome, MagenticAgentMessageEvent, RoutingMessage
from ..strategies import run_execution_phase_streaming
from .base import handler

logger = setup_logger(__name__)


class ExecutionExecutor(Executor):
    """Executor that executes tasks based on routing decisions."""

    def __init__(self, executor_id: str, context: SupervisorContext) -> None:
        """Initialize the execution executor."""
        super().__init__(id=executor_id)
        self.context = context

    @handler
    async def handle_routing(
        self,
        routing_msg: RoutingMessage,
        ctx: WorkflowContext[ExecutionMessage],
    ) -> None:
        """Handle a routing message."""
        with optional_span(
            "ExecutionExecutor.handle_routing",
            attributes={
                "task": routing_msg.task,
                "mode": getattr(routing_msg.routing.decision, "mode", None),
            },
        ):
            logger.debug("Workflow context attributes: %s", dir(ctx))

            routing_decision = routing_msg.routing.decision
            task = routing_msg.task
            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()

            logger.info(f"Executing task in {routing_decision.mode.value} mode")
            logger.info(f"Assigned agents: {routing_decision.assigned_to}")
            logger.info(f"Subtasks: {routing_decision.subtasks}")

            try:
                # Tool planning hint (optional)
                tool_plan_info = None
                routing_metadata = routing_msg.metadata or {}
                tool_plan_info = routing_metadata.get("routing_tool_plan")
                if tool_plan_info is None:
                    try:
                        dspy_supervisor = getattr(self.context, "dspy_supervisor", None)
                        if dspy_supervisor:
                            team = {
                                name: getattr(agent, "description", "")
                                for name, agent in (self.context.agents or {}).items()
                            }
                            tool_plan_info = dspy_supervisor.decide_tools(task, team, "")
                    except Exception:
                        # Silently ignore DSPy tool planning errors - workflow can continue
                        # without tool planning information
                        tool_plan_info = None

                # Streaming execution
                final_result = None
                tool_usage = []

                async for event in run_execution_phase_streaming(
                    routing=routing_decision,
                    task=task,
                    context=self.context,
                ):
                    if isinstance(event, MagenticAgentMessageEvent):
                        # Emit intermediate event
                        if hasattr(ctx, "add_event"):
                            await ctx.add_event(event)
                    elif isinstance(event, WorkflowOutputEvent):
                        # Handle list[ChatMessage] format (standard)
                        if (
                            isinstance(event.data, list)
                            and len(event.data) > 0
                            and isinstance(event.data[0], ChatMessage)
                        ):
                            msg = event.data[0]
                            final_result = msg.text
                            if (
                                msg.additional_properties
                                and "tool_usage" in msg.additional_properties
                            ):
                                tool_usage = msg.additional_properties["tool_usage"]
                        # Handle dict format (legacy/fallback)
                        elif isinstance(event.data, dict):
                            final_result = event.data.get("result")
                            if "tool_usage" in event.data:
                                tool_usage = event.data["tool_usage"]

                if final_result is None:
                    # Fallback if no result event received (should not happen)
                    final_result = "No result produced."

                execution_outcome = ExecutionOutcome(
                    result=str(final_result),
                    mode=routing_decision.mode,
                    assigned_agents=list(routing_decision.assigned_to),
                    subtasks=list(routing_decision.subtasks),
                    status="success",
                    artifacts={},
                    tool_usage=tool_usage,
                )

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["execution"] = duration
                self.context.latest_phase_status["execution"] = "success"

                metadata = dict(routing_msg.metadata or {})
                metadata["routing"] = routing_decision
                if tool_plan_info:
                    metadata["tool_plan"] = tool_plan_info

                execution_msg = ExecutionMessage(
                    task=task,
                    outcome=execution_outcome,
                    metadata=metadata,
                )
                # Add tool usage to metadata for downstream tracking
                execution_msg.metadata["tool_usage"] = execution_outcome.tool_usage
                await ctx.send_message(execution_msg)

            except Exception as e:
                # Intentional broad exception handling: Agent execution can fail for many
                # reasons (LLM errors, tool failures, timeouts). Return an error outcome
                # to allow downstream phases to handle appropriately.
                logger.exception(f"Execution failed: {e}")
                error_outcome = ExecutionOutcome(
                    result=f"Execution failed: {e!s}",
                    mode=routing_decision.mode,
                    assigned_agents=list(routing_decision.assigned_to),
                    subtasks=list(routing_decision.subtasks),
                    status="error",
                    artifacts={},
                )
                self.context.latest_phase_status["execution"] = "failed"
                execution_msg = ExecutionMessage(
                    task=task,
                    outcome=error_outcome,
                    metadata={**routing_msg.metadata, "error": str(e)},
                )
                await ctx.send_message(execution_msg)
            finally:
                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb["execution"] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb["execution"] = (
                        end_mem_mb - start_mem_mb
                    )
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass
