"""Execution executor for fleet workflow.

Handles delegated, sequential, and parallel execution modes.
Supports fan-out/fan-in for parallel execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import Executor, WorkflowContext, handler

from ...utils.logger import setup_logger
from ..shared.execution import run_execution_phase
from .messages import ExecutionMessage, RoutingMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class ExecutionExecutor(Executor):
    """Executor that executes tasks based on routing decisions."""

    def __init__(
        self,
        executor_id: str,
        context: SupervisorContext,
    ) -> None:
        """Initialize ExecutionExecutor.

        Args:
            executor_id: Unique executor identifier
            context: Supervisor context with configuration and state
        """
        super().__init__(id=executor_id)
        self.context = context

    @handler
    async def handle_routing(
        self,
        routing_msg: RoutingMessage,
        ctx: WorkflowContext[ExecutionMessage],
    ) -> None:
        """Handle routing message and execute task.

        Args:
            routing_msg: Routing message from previous executor
            ctx: Workflow context for sending messages
        """
        routing_decision = routing_msg.routing.decision
        task = routing_msg.task

        logger.info(
            f"Executing task in {routing_decision.mode.value} mode with agents: {list(routing_decision.assigned_to)}"
        )

        try:
            # Use existing execution phase logic
            execution_outcome = await run_execution_phase(
                routing=routing_decision,
                task=task,
                context=self.context,
            )

            # Store routing in metadata for downstream executors
            metadata = routing_msg.metadata.copy()
            metadata["routing"] = routing_decision

            # Create execution message
            execution_msg = ExecutionMessage(
                task=task,
                outcome=execution_outcome,
                metadata=metadata,
            )

            logger.info(f"Execution completed: status={execution_outcome.status}")

            # Send to next executor
            await ctx.send_message(execution_msg)

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            # Create error outcome
            from ..shared.models import ExecutionOutcome

            error_outcome = ExecutionOutcome(
                result=f"Execution failed: {e!s}",
                mode=routing_decision.mode,
                assigned_agents=list(routing_decision.assigned_to),
                subtasks=list(routing_decision.subtasks),
                status="error",
                artifacts={},
            )

            execution_msg = ExecutionMessage(
                task=task,
                outcome=error_outcome,
                metadata={**routing_msg.metadata, "error": str(e)},
            )
            await ctx.send_message(execution_msg)
