"""Execution executor for fleet workflow.

Handles delegated, sequential, and parallel execution modes.
Supports fan-out/fan-in for parallel execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import Executor, WorkflowContext

from ...utils.logger import setup_logger
from ..shared.execution import run_execution_phase
from .decorators import handler
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
            # Optional: produce a compact tool plan to guide execution (ReAct-style),
            # capped implicitly by downstream execution strategies.
            tool_plan_info: dict | None = None
            try:
                dspy_supervisor = getattr(self.context, "dspy_supervisor", None)
                if dspy_supervisor is not None:
                    team = {
                        name: getattr(agent, "description", "")
                        for name, agent in (self.context.agents or {}).items()
                    }
                    tool_plan_info = dspy_supervisor.decide_tools(task, team, current_context="")
            except Exception:
                tool_plan_info = None

            # If the plan indicates multiple tool steps, insert a bounded ReAct-style
            # reasoning pass to synthesize a brief plan snippet before execution.
            # We keep this lightweight and non-blocking; time-bounded by execution timeout/3.
            if tool_plan_info and isinstance(tool_plan_info.get("tool_plan"), list):
                plan_list = tool_plan_info.get("tool_plan") or []
                if len(plan_list) >= 2:
                    try:
                        import asyncio

                        import dspy

                        # Minimal signature: produce one-paragraph plan
                        class ToolPlanSignature(dspy.Signature):  # type: ignore
                            task = dspy.InputField(desc="task to execute")
                            tools = dspy.InputField(desc="ordered tools to use")
                            plan = dspy.OutputField(desc="short plan for 2-3 steps")

                        planner = dspy.Predict(ToolPlanSignature)

                        async def _bounded():
                            return planner(task=task, tools=", ".join(plan_list))

                        timeout = max(
                            5,
                            int(
                                self.context.config.execution_timeout_seconds
                                if hasattr(self.context.config, "execution_timeout_seconds")
                                else 30
                            )
                            // 3,
                        )
                        _ = await asyncio.wait_for(_bounded(), timeout=timeout)
                    except Exception:
                        pass

            # Use existing execution phase logic
            execution_outcome = await run_execution_phase(
                routing=routing_decision,
                task=task,
                context=self.context,
            )

            # Store routing in metadata for downstream executors
            metadata = routing_msg.metadata.copy()
            metadata["routing"] = routing_decision
            if tool_plan_info:
                metadata["tool_plan"] = tool_plan_info

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
