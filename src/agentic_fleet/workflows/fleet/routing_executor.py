"""Routing executor for fleet workflow.

Uses DSPySupervisor to route tasks and produce RoutingMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import Executor, WorkflowContext, handler

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.logger import setup_logger
from ...utils.models import RoutingDecision, ensure_routing_decision
from ..routing.helpers import detect_routing_edge_cases, normalize_routing_decision
from .messages import AnalysisMessage, RoutingMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class RoutingExecutor(Executor):
    """Executor that routes tasks using DSPy supervisor."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPySupervisor,
        context: SupervisorContext,
    ) -> None:
        """Initialize RoutingExecutor.

        Args:
            executor_id: Unique executor identifier
            supervisor: DSPy supervisor instance for task routing
            context: Supervisor context with configuration and state
        """
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_analysis(
        self,
        analysis_msg: AnalysisMessage,
        ctx: WorkflowContext[RoutingMessage],
    ) -> None:
        """Handle analysis message and produce routing decision.

        Args:
            analysis_msg: Analysis message from previous executor
            ctx: Workflow context for sending messages
        """
        logger.info(f"Routing task: {analysis_msg.task[:100]}...")

        try:
            # Prepare team descriptions
            agents = self.context.agents or {}
            team_descriptions = {
                name: getattr(agent, "description", "") or getattr(agent, "name", "")
                for name, agent in agents.items()
            }

            # Use DSPy supervisor to route task
            routing_decision = await self._call_with_retry(
                self.supervisor.route_task,
                task=analysis_msg.task,
                team=team_descriptions,
                context=analysis_msg.analysis.search_context or "",
                handoff_history="",
            )

            # Ensure we have a RoutingDecision
            routing_decision = ensure_routing_decision(routing_decision)

            # Normalize routing decision
            routing_decision = normalize_routing_decision(routing_decision, analysis_msg.task)

            # Detect edge cases
            edge_cases = detect_routing_edge_cases(analysis_msg.task, routing_decision)
            if edge_cases:
                logger.info(f"Edge cases detected: {', '.join(edge_cases)}")

            # Create routing plan
            from ..shared.models import RoutingPlan

            routing_plan = RoutingPlan(
                decision=routing_decision,
                edge_cases=edge_cases,
                used_fallback=False,
            )

            # Create routing message
            routing_msg = RoutingMessage(
                task=analysis_msg.task,
                routing=routing_plan,
                metadata=analysis_msg.metadata,
            )

            logger.info(
                f"Routing decision: mode={routing_decision.mode.value}, "
                f"agents={list(routing_decision.assigned_to)}, "
                f"confidence={routing_decision.confidence}"
            )

            # Send to next executor
            await ctx.send_message(routing_msg)

        except Exception as e:
            logger.exception(f"Routing failed: {e}")
            # Fallback routing
            fallback_routing = self._fallback_routing(analysis_msg.task)
            routing_decision = ensure_routing_decision(fallback_routing)
            routing_decision = normalize_routing_decision(routing_decision, analysis_msg.task)

            from ..shared.models import RoutingPlan

            routing_plan = RoutingPlan(
                decision=routing_decision,
                edge_cases=[],
                used_fallback=True,
            )

            routing_msg = RoutingMessage(
                task=analysis_msg.task,
                routing=routing_plan,
                metadata={**analysis_msg.metadata, "used_fallback": True},
            )
            await ctx.send_message(routing_msg)

    def _fallback_routing(self, task: str) -> RoutingDecision:
        """Fallback routing that delegates to the first available agent."""
        from ...utils.models import ExecutionMode
        from ..exceptions import RoutingError

        logger.error("Falling back to heuristic routing for task: %s", task[:100])
        agents = self.context.agents or {}
        if not agents:
            raise RoutingError(
                "DSPy routing failed and no agents are registered.",
                {"task": task},
            )
        fallback_agent = next(iter(agents.keys()), None)
        if fallback_agent is None:
            raise RoutingError(
                "DSPy routing failed and no agents are registered.",
                {"task": task},
            )

        return RoutingDecision(
            task=task,
            assigned_to=(fallback_agent,),
            mode=ExecutionMode.DELEGATED,
            subtasks=(task,),
            tool_requirements=tuple(),
            confidence=0.0,
        )

    async def _call_with_retry(
        self,
        fn,
        *args,
        **kwargs,
    ):
        """Call DSPy function with retry logic."""
        import asyncio

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    f"DSPy call {getattr(fn, '__name__', repr(fn))} failed on attempt {attempt}/{attempts}: {exc}"
                )
                if attempt < attempts:
                    await asyncio.sleep(backoff * attempt)

        if last_exc:
            raise last_exc
        raise RuntimeError("DSPy call failed without raising an exception")
