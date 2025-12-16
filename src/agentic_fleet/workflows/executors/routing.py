"""Routing phase executor.

Split out of `workflows/executors.py` to keep each executor implementation focused.
"""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any, cast

from agent_framework._workflows import Executor, WorkflowContext

from ...dspy_modules.assertions import detect_task_type, validate_full_routing
from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ...utils.resilience import async_call_with_retry
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from ..helpers import detect_routing_edge_cases, normalize_routing_decision
from ..models import AnalysisMessage, RoutingMessage, RoutingPlan
from .base import handler

logger = setup_logger(__name__)


class RoutingExecutor(Executor):
    """Executor that routes tasks using DSPy reasoner."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the routing executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_analysis(
        self,
        analysis_msg: AnalysisMessage,
        ctx: WorkflowContext[RoutingMessage],
    ) -> None:
        """
        Determine and emit a routing plan for the given analysis, then send a RoutingMessage.

        Uses DSPy-based routing when available and appropriate; for light-profile or on any routing failure, falls back to a heuristic routing decision. Updates workflow phase timings and status, may add metadata keys such as `routing_tool_plan`, `task_type`, and `used_fallback`, and detects routing edge cases and automatic promotion to parallel execution when applicable. On success or fallback, sends a RoutingMessage containing a RoutingPlan with `decision`, `edge_cases`, and `used_fallback`.

        Parameters:
            analysis_msg (AnalysisMessage): Incoming analysis containing the task text and analysis details.
            ctx (WorkflowContext[RoutingMessage]): Workflow context used to send the resulting RoutingMessage and access workflow state.
        """
        with optional_span(
            "RoutingExecutor.handle_analysis", attributes={"task": analysis_msg.task}
        ):
            logger.info(f"Routing task: {analysis_msg.task[:100]}...")
            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()

            metadata = dict(analysis_msg.metadata or {})
            simple_mode = bool(metadata.get("simple_mode"))
            cfg = self.context.config
            pipeline_profile = getattr(cfg, "pipeline_profile", "full")
            use_light_routing = pipeline_profile == "light" and simple_mode

            try:
                if use_light_routing:
                    logger.info("Using heuristic routing for simple task in light profile")
                    routing_decision = self._fallback_routing(analysis_msg.task)
                    routing_decision = normalize_routing_decision(
                        routing_decision, analysis_msg.task
                    )
                    edge_cases = []
                    used_fallback = True
                else:
                    agents = self.context.agents or {}

                    team_descriptions = {}
                    for name, agent in agents.items():
                        desc = getattr(agent, "description", "") or getattr(agent, "name", "")

                        # Inspect for rich metadata (Tools)
                        tools_info: list[str] = []
                        tool_names_obj = getattr(agent, "tool_names", None)
                        tools_obj = getattr(agent, "tools", None)
                        if tool_names_obj:
                            # Foundry Agents might store names directly
                            if isinstance(tool_names_obj, str):
                                tools_info = [tool_names_obj]
                            elif isinstance(tool_names_obj, Iterable):
                                tools_info = [
                                    str(name) for name in cast(Iterable[Any], tool_names_obj)
                                ]
                        elif tools_obj:
                            # Local agents have tool objects
                            if isinstance(tools_obj, str):
                                tools_info = [tools_obj]
                            elif isinstance(tools_obj, Iterable):
                                tools_info = [
                                    getattr(t, "name", str(t))
                                    for t in cast(Iterable[Any], tools_obj)
                                ]

                        # Inspect for Capabilities
                        caps_info: list[str] = []
                        caps_obj = getattr(agent, "capabilities", None)
                        if caps_obj:
                            if isinstance(caps_obj, str):
                                caps_info = [caps_obj]
                            elif isinstance(caps_obj, Iterable):
                                caps_info = [str(cap) for cap in cast(Iterable[Any], caps_obj)]

                        # Construct rich description
                        extras = []
                        if tools_info:
                            extras.append(f"Tools: [{', '.join(tools_info)}]")
                        if caps_info:
                            extras.append(f"Capabilities: [{', '.join(caps_info)}]")

                        if extras:
                            desc += " " + " ".join(extras)

                        team_descriptions[name] = desc

                    retry_attempts = max(1, int(cfg.dspy_retry_attempts))
                    retry_backoff = max(0.0, float(cfg.dspy_retry_backoff_seconds))

                    conversation_context = str(metadata.get("conversation_context", "") or "")
                    routing_context_parts: list[str] = []
                    if conversation_context:
                        routing_context_parts.append(
                            "Conversation context (most recent messages):\n" + conversation_context
                        )
                    if analysis_msg.analysis.search_context:
                        routing_context_parts.append(
                            "Web/search context:\n" + str(analysis_msg.analysis.search_context)
                        )
                    routing_context = "\n\n".join(routing_context_parts).strip()

                    raw_routing = await async_call_with_retry(
                        self.supervisor.route_task,
                        task=analysis_msg.task,
                        team=team_descriptions,
                        context=routing_context,
                        handoff_history="",
                        max_backtracks=getattr(cfg, "dspy_max_backtracks", 2),
                        # Routing cache keys are task-only; bypass cache when conversation context is present.
                        skip_cache=bool(conversation_context),
                        attempts=retry_attempts,
                        backoff_seconds=retry_backoff,
                    )

                    if isinstance(raw_routing, dict):
                        tool_plan = raw_routing.get("tool_plan")
                        tool_goals = raw_routing.get("tool_goals")
                        latency_budget = raw_routing.get("latency_budget")
                        routing_reasoning = raw_routing.get("reasoning")
                        if tool_plan or tool_goals or latency_budget or routing_reasoning:
                            metadata["routing_tool_plan"] = {
                                "tool_plan": tool_plan or [],
                                "tool_goals": tool_goals or "",
                                "latency_budget": latency_budget or "",
                                "reasoning": routing_reasoning or "",
                            }

                    routing_decision = ensure_routing_decision(raw_routing)
                    routing_decision = normalize_routing_decision(
                        routing_decision, analysis_msg.task
                    )

                    # Validate routing decision with DSPy assertions
                    # This enables soft suggestions for routing improvements during optimization
                    available_agent_names = list(agents.keys())
                    tool_registry = getattr(self.supervisor, "tool_registry", None)
                    available_tool_names = (
                        [t.name for t in tool_registry.get_all_tools()]
                        if tool_registry and hasattr(tool_registry, "get_all_tools")
                        else []
                    )
                    try:
                        validate_full_routing(
                            routing_decision,
                            analysis_msg.task,
                            available_agents=available_agent_names,
                            available_tools=available_tool_names if available_tool_names else None,
                        )
                    except Exception as validation_err:
                        # Log but don't fail - assertions are for optimization guidance
                        logger.debug(f"Routing validation note: {validation_err}")

                    # Add task type to metadata for downstream components
                    task_type = detect_task_type(analysis_msg.task)
                    metadata["task_type"] = task_type

                    # Auto-parallelization check
                    parallel_threshold = getattr(cfg, "parallel_threshold", 2)
                    if (
                        len(routing_decision.subtasks) >= parallel_threshold
                        and routing_decision.mode == ExecutionMode.DELEGATED
                    ):
                        logger.info(
                            f"Upgrading to PARALLEL execution (subtasks={len(routing_decision.subtasks)} >= threshold={parallel_threshold})"
                        )
                        # RoutingDecision is a frozen dataclass, use .update() (which wraps replace)
                        routing_decision = routing_decision.update(mode=ExecutionMode.PARALLEL)

                    edge_cases = detect_routing_edge_cases(analysis_msg.task, routing_decision)
                    if edge_cases:
                        logger.info(f"Edge cases detected: {', '.join(edge_cases)}")
                    used_fallback = False

                routing_plan = RoutingPlan(
                    decision=routing_decision,
                    edge_cases=edge_cases,
                    used_fallback=used_fallback,
                )

                # Record timing
                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["routing"] = duration
                self.context.latest_phase_status["routing"] = (
                    "fallback" if used_fallback else "success"
                )

                routing_msg = RoutingMessage(
                    task=analysis_msg.task,
                    routing=routing_plan,
                    metadata=metadata,
                )

                logger.info(
                    f"Routing decision: mode={routing_decision.mode.value}, "
                    f"agents={list(routing_decision.assigned_to)}"
                )
                await ctx.send_message(routing_msg)

            # Broad exception handling is intentional here:
            # During the routing phase, various exception types can occur, including but not limited to:
            # - Model inference errors (e.g., timeouts, response parsing failures),
            # - Network, serialization, or deserialization errors,
            # - Transient infrastructure issues or unexpected inputs from agent plugins.
            # Since any of these errors make the routing output invalid, *all* exceptions are handled
            # uniformly by degrading to the fallback routing strategy. This ensures graceful degradation
            # and avoids disrupting the workflow due to unpredictable exceptions.
            # It is considered safe in this context because the fallback is guaranteed to yield a valid, minimal routing plan.
            except Exception as e:
                logger.exception(f"Routing failed: {e}")
                fallback_routing = self._fallback_routing(analysis_msg.task)
                routing_decision = normalize_routing_decision(fallback_routing, analysis_msg.task)
                routing_plan = RoutingPlan(
                    decision=routing_decision,
                    edge_cases=[],
                    used_fallback=True,
                )
                self.context.latest_phase_status["routing"] = "fallback"
                routing_msg = RoutingMessage(
                    task=analysis_msg.task,
                    routing=routing_plan,
                    metadata={**metadata, "used_fallback": True},
                )
                await ctx.send_message(routing_msg)
            finally:
                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb["routing"] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb["routing"] = end_mem_mb - start_mem_mb
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass

    def _fallback_routing(self, task: str) -> RoutingDecision:
        """Perform fallback routing when DSPy fails.

        Assigns the task to the first available agent when the DSPy
        router is unavailable or returns invalid results.

        Args:
            task: The task to route.

        Returns:
            RoutingDecision with the first available agent assigned.

        Raises:
            RuntimeError: If no agents are registered.
        """
        agents = self.context.agents or {}
        if not agents:
            raise RuntimeError("No agents registered for routing.")
        fallback_agent = next(iter(agents.keys()))
        return RoutingDecision(
            task=task,
            assigned_to=(fallback_agent,),
            mode=ExecutionMode.DELEGATED,
            subtasks=(task,),
            tool_requirements=(),
            confidence=0.0,
        )
