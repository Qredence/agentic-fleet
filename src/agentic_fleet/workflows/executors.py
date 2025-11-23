"""Core workflow executors.

Consolidated from former fleet/ executors.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
from dataclasses import replace
from time import perf_counter
from typing import Any

from agent_framework import (
    Executor,
    MagenticAgentMessageEvent,
    WorkflowContext,
    WorkflowOutputEvent,
)

from ..dspy_modules.reasoner import DSPyReasoner
from ..utils.logger import setup_logger
from ..utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ..utils.telemetry import optional_span
from .context import SupervisorContext
from .exceptions import ToolError
from .helpers import (
    build_refinement_task,
    call_judge_with_reasoning,
    detect_routing_edge_cases,
    get_quality_criteria,
    normalize_routing_decision,
    parse_judge_response,
    refine_results,
)
from .messages import (
    AnalysisMessage,
    ExecutionMessage,
    FinalResultMessage,
    ProgressMessage,
    QualityMessage,
    RoutingMessage,
    TaskMessage,
)
from .models import AnalysisResult, ExecutionOutcome, ProgressReport, QualityReport, RoutingPlan
from .strategies import run_execution_phase_streaming

logger = setup_logger(__name__)


# --- Decorator helper (local implementation) ---
def handler(func):
    """Decorator to handle type hints for executors."""
    from typing import get_type_hints

    from agent_framework import handler as _framework_handler

    try:
        hints = get_type_hints(func, globalns=func.__globals__, localns=None)
        annotations = dict(getattr(func, "__annotations__", {}))
        annotations.update(hints)
        func.__annotations__ = annotations
    except Exception:
        pass
    return _framework_handler(func)


# --- Executors ---


class AnalysisExecutor(Executor):
    """Executor that analyzes tasks using DSPy reasoner."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the analysis executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_task(
        self,
        task_msg: TaskMessage,
        ctx: WorkflowContext[AnalysisMessage],
    ) -> None:
        """Handle a task message."""
        with optional_span("AnalysisExecutor.handle_task", attributes={"task": task_msg.task}):
            logger.info(f"Analyzing task: {task_msg.task[:100]}...")

            start_t = perf_counter()
            cfg = self.context.config
            pipeline_profile = getattr(cfg, "pipeline_profile", "full")
            simple_threshold = getattr(cfg, "simple_task_max_words", 40)

            is_simple = self._is_simple_task(task_msg.task, simple_threshold)
            use_light_path = pipeline_profile == "light" and is_simple

            try:
                if use_light_path:
                    analysis_dict = self._fallback_analysis(task_msg.task)
                    metadata = {**task_msg.metadata, "simple_mode": True}
                else:
                    cache = self.context.analysis_cache
                    cache_key = task_msg.task.strip()
                    cached = cache.get(cache_key) if cache is not None else None

                    if cached is not None:
                        logger.info("Using cached DSPy analysis for task")
                        analysis_dict = cached
                        self.context.latest_phase_status["analysis"] = "cached"
                    else:
                        analysis_dict = await self._call_with_retry(
                            self.supervisor.analyze_task,
                            task_msg.task,
                            use_tools=True,
                            perform_search=True,
                        )
                        if cache is not None:
                            cache.set(cache_key, analysis_dict)
                        self.context.latest_phase_status["analysis"] = "success"
                    metadata = {**task_msg.metadata, "simple_mode": False}

                # Convert to AnalysisResult
                analysis_result = self._to_analysis_result(analysis_dict)

                # Async search if needed
                if (
                    analysis_result.needs_web_search
                    and analysis_result.search_query
                    and not analysis_result.search_context
                    and not use_light_path
                ):
                    try:
                        search_context = await self.supervisor.perform_web_search_async(
                            analysis_result.search_query
                        )
                        if search_context:
                            analysis_result = replace(
                                analysis_result, search_context=search_context
                            )
                    except TimeoutError:
                        logger.warning(
                            "Async web search timed out for query: %s",
                            analysis_result.search_query,
                        )
                    except ToolError as exc:
                        logger.warning("Async web search tool error: %s", exc)
                    except Exception as exc:
                        logger.warning("Async web search failed: %s", exc)

                # Record timing
                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["analysis"] = duration

                analysis_msg = AnalysisMessage(
                    task=task_msg.task,
                    analysis=analysis_result,
                    metadata=metadata,
                )

                logger.info(
                    f"Analysis complete: complexity={analysis_result.complexity}, "
                    f"steps={analysis_result.steps}, capabilities={analysis_result.capabilities[:3]}"
                )
                await ctx.send_message(analysis_msg)

            except Exception as e:
                logger.exception(f"Analysis failed: {e}")
                fallback_dict = self._fallback_analysis(task_msg.task)
                analysis_result = self._to_analysis_result(fallback_dict)
                analysis_msg = AnalysisMessage(
                    task=task_msg.task,
                    analysis=analysis_result,
                    metadata={**task_msg.metadata, "used_fallback": True},
                )
                self.context.latest_phase_status["analysis"] = "fallback"
                await ctx.send_message(analysis_msg)

    def _fallback_analysis(self, task: str) -> dict[str, Any]:
        """Perform fallback analysis when DSPy fails."""
        word_count = len(task.split())
        complexity = "simple"
        if word_count > 150:
            complexity = "complex"
        elif word_count > 40:
            complexity = "moderate"

        return {
            "complexity": complexity,
            "capabilities": ["general_reasoning"],
            "tool_requirements": [],
            "steps": max(3, min(6, word_count // 40 + 1)),
            "search_context": "",
            "needs_web_search": False,
            "search_query": "",
        }

    def _to_analysis_result(self, payload: dict[str, Any]) -> AnalysisResult:
        """Convert dictionary payload to AnalysisResult."""
        complexity = str(payload.get("complexity", "moderate") or "moderate")
        capabilities = [
            str(cap).strip() for cap in payload.get("capabilities", []) if str(cap).strip()
        ]
        tool_requirements = [
            str(tool).strip() for tool in payload.get("tool_requirements", []) if str(tool).strip()
        ]
        steps_raw = payload.get("steps", 3)
        try:
            steps = int(steps_raw)
        except (TypeError, ValueError):
            steps = 3
        if steps <= 0:
            steps = 3

        return AnalysisResult(
            complexity=complexity,
            capabilities=capabilities or ["general_reasoning"],
            tool_requirements=tool_requirements,
            steps=steps,
            search_context=str(payload.get("search_context", "") or ""),
            needs_web_search=bool(payload.get("needs_web_search")),
            search_query=str(payload.get("search_query", "") or ""),
        )

    def _is_simple_task(self, task: str, max_words: int) -> bool:
        """Check if a task is simple enough for light path."""
        if not task:
            return False
        simple_patterns = [
            r"(?i)^(remember|save)\s+this:?",
            r"(?i)^(hello|hi|hey|greetings)",
            r"(?i)^/help",
        ]
        if any(re.search(p, task) for p in simple_patterns):
            return True
        words = task.strip().split()
        return len(words) <= max_words

    async def _call_with_retry(self, fn, *args, **kwargs):
        """Call a function with retry logic."""
        from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_fixed(backoff),
            reraise=True,
        ):
            with attempt:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

        # Defensive fallback: This line should never be reached due to reraise=True in AsyncRetrying.
        # If reached, it indicates unexpected behavior or a bug in the tenacity library.
        raise RuntimeError("Retry loop completed without result or exception")


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
        """Handle an analysis message."""
        with optional_span(
            "RoutingExecutor.handle_analysis", attributes={"task": analysis_msg.task}
        ):
            logger.info(f"Routing task: {analysis_msg.task[:100]}...")
            start_t = perf_counter()

            metadata = analysis_msg.metadata or {}
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
                    team_descriptions = {
                        name: getattr(agent, "description", "") or getattr(agent, "name", "")
                        for name, agent in agents.items()
                    }

                    raw_routing = await self._call_with_retry(
                        self.supervisor.route_task,
                        task=analysis_msg.task,
                        team=team_descriptions,
                        context=analysis_msg.analysis.search_context or "",
                        handoff_history="",
                        max_backtracks=getattr(cfg, "dspy_max_backtracks", 2),
                    )

                    routing_decision = ensure_routing_decision(raw_routing)
                    routing_decision = normalize_routing_decision(
                        routing_decision, analysis_msg.task
                    )

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
                    metadata=analysis_msg.metadata,
                )

                logger.info(
                    f"Routing decision: mode={routing_decision.mode.value}, "
                    f"agents={list(routing_decision.assigned_to)}"
                )
                await ctx.send_message(routing_msg)

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
                    metadata={**analysis_msg.metadata, "used_fallback": True},
                )
                await ctx.send_message(routing_msg)

    def _fallback_routing(self, task: str) -> RoutingDecision:
        """Perform fallback routing when DSPy fails."""
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

    async def _call_with_retry(self, fn, *args, **kwargs):
        """Call a function with retry logic."""
        from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_fixed(backoff),
            reraise=True,
        ):
            with attempt:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

        # This line should never be reached due to reraise=True above
        raise RuntimeError("Retry loop completed without result or exception")


# Shared retry utility for executors
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
            msg = f"DEBUG: ctx attributes: {dir(ctx)}"
            logger.info(msg)
            print(msg)  # Force stdout

            routing_decision = routing_msg.routing.decision
            task = routing_msg.task
            start_t = perf_counter()

            logger.info(f"Executing task in {routing_decision.mode.value} mode")
            logger.info(f"Assigned agents: {routing_decision.assigned_to}")
            logger.info(f"Subtasks: {routing_decision.subtasks}")

            try:
                # Tool planning hint (optional)
                tool_plan_info = None
                try:
                    dspy_supervisor = getattr(self.context, "dspy_supervisor", None)
                    if dspy_supervisor:
                        team = {
                            name: getattr(agent, "description", "")
                            for name, agent in (self.context.agents or {}).items()
                        }
                        tool_plan_info = dspy_supervisor.decide_tools(task, team, "")
                except Exception:
                    pass

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
                            ctx.add_event(event)
                    elif isinstance(event, WorkflowOutputEvent) and isinstance(event.data, dict):
                        # Capture final result
                        final_result = event.data.get("result")
                        # Try to extract tool usage if available, or ignore for now
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

                metadata = routing_msg.metadata.copy()
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


class ProgressExecutor(Executor):
    """Executor that evaluates progress."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the progress executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_execution(
        self,
        execution_msg: ExecutionMessage,
        ctx: WorkflowContext[ProgressMessage],
    ) -> None:
        """Handle an execution message."""
        with optional_span(
            "ProgressExecutor.handle_execution", attributes={"task": execution_msg.task}
        ):
            logger.info("Evaluating progress...")
            start_t = perf_counter()

            try:
                cfg = self.context.config
                pipeline_profile = getattr(cfg, "pipeline_profile", "full")
                enable_eval = getattr(cfg, "enable_progress_eval", True)

                if pipeline_profile == "light" or not enable_eval:
                    progress_report = ProgressReport(
                        action="complete", feedback="", used_fallback=True
                    )
                    used_fallback = True
                else:
                    progress_dict = await self._call_with_retry(
                        self.supervisor.evaluate_progress,
                        original_task=execution_msg.task,
                        completed=execution_msg.outcome.result,
                        status="completion",
                    )
                    progress_report = self._to_progress_report(progress_dict)
                    used_fallback = False

                routing = None
                if hasattr(execution_msg.outcome, "routing"):
                    routing = execution_msg.outcome.routing
                elif "routing" in execution_msg.metadata:
                    routing_data = execution_msg.metadata["routing"]
                    if isinstance(routing_data, RoutingDecision):
                        routing = routing_data
                    elif isinstance(routing_data, dict):
                        routing = RoutingDecision.from_mapping(routing_data)

                metadata = execution_msg.metadata.copy()
                if routing:
                    metadata["routing"] = routing

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["progress"] = duration
                self.context.latest_phase_status["progress"] = (
                    "fallback" if used_fallback else "success"
                )

                progress_msg = ProgressMessage(
                    task=execution_msg.task,
                    result=execution_msg.outcome.result,
                    progress=progress_report,
                    metadata=metadata,
                )
                await ctx.send_message(progress_msg)

            except Exception as e:
                logger.exception(f"Progress evaluation failed: {e}")
                progress_report = ProgressReport(action="continue", feedback="", used_fallback=True)
                self.context.latest_phase_status["progress"] = "failed"
                progress_msg = ProgressMessage(
                    task=execution_msg.task,
                    result=execution_msg.outcome.result,
                    progress=progress_report,
                    metadata={**execution_msg.metadata, "used_fallback": True},
                )
                await ctx.send_message(progress_msg)

    def _to_progress_report(self, payload: dict[str, Any]) -> ProgressReport:
        """Convert dictionary payload to ProgressReport."""
        action = str(payload.get("action", "continue") or "continue").strip().lower()
        if action not in {"continue", "refine", "complete", "escalate"}:
            action = "continue"
        return ProgressReport(
            action=action,
            feedback=str(payload.get("feedback", "") or ""),
            used_fallback=bool(payload.get("used_fallback")),
        )

    async def _call_with_retry(self, fn, *args, **kwargs):
        """Call a function with retry logic."""
        from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_fixed(backoff),
            reraise=True,
        ):
            with attempt:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

        # This line should never be reached due to reraise=True above
        raise RuntimeError("Retry loop completed without result or exception")


class QualityExecutor(Executor):
    """Executor that assesses quality."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the quality executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_progress(
        self,
        progress_msg: ProgressMessage,
        ctx: WorkflowContext[QualityMessage],
    ) -> None:
        """Handle a progress message."""
        with optional_span(
            "QualityExecutor.handle_progress", attributes={"task": progress_msg.task}
        ):
            logger.info("Assessing quality...")
            start_t = perf_counter()

            try:
                cfg = self.context.config
                pipeline_profile = getattr(cfg, "pipeline_profile", "full")
                enable_eval = getattr(cfg, "enable_quality_eval", True)

                if pipeline_profile == "light" or not enable_eval:
                    # Use 0.0 to indicate "not evaluated" or missing quality data
                    quality_report = QualityReport(
                        score=0.0, missing="", improvements="", used_fallback=True
                    )
                    used_fallback = True
                else:
                    quality_dict = await self._call_with_retry(
                        self.supervisor.assess_quality,
                        requirements=progress_msg.task,
                        results=progress_msg.result,
                    )
                    quality_report = self._to_quality_report(quality_dict)
                    used_fallback = False

                routing = None
                if "routing" in progress_msg.metadata:
                    routing_data = progress_msg.metadata["routing"]
                    if isinstance(routing_data, RoutingDecision):
                        routing = routing_data
                    elif isinstance(routing_data, dict):
                        routing = RoutingDecision.from_mapping(routing_data)

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["quality"] = duration
                self.context.latest_phase_status["quality"] = (
                    "fallback" if used_fallback else "success"
                )

                quality_msg = QualityMessage(
                    task=progress_msg.task,
                    result=progress_msg.result,
                    quality=quality_report,
                    routing=routing,
                    metadata=progress_msg.metadata,
                )
                await ctx.send_message(quality_msg)

            except Exception as e:
                logger.exception(f"Quality assessment failed: {e}")
                # Use 0.0 to indicate "not evaluated" or missing quality data
                quality_report = QualityReport(
                    score=0.0, missing="", improvements="", used_fallback=True
                )
                self.context.latest_phase_status["quality"] = "failed"
                quality_msg = QualityMessage(
                    task=progress_msg.task,
                    result=progress_msg.result,
                    quality=quality_report,
                    metadata={**progress_msg.metadata, "used_fallback": True},
                )
                await ctx.send_message(quality_msg)

    def _to_quality_report(self, payload: dict[str, Any]) -> QualityReport:
        """Convert dictionary payload to QualityReport."""
        return QualityReport(
            score=float(payload.get("score", 0.0) or 0.0),
            missing=str(payload.get("missing", "")),
            improvements=str(payload.get("improvements", "")),
            judge_score=payload.get("judge_score"),
            final_evaluation=payload.get("final_evaluation"),
            used_fallback=bool(payload.get("used_fallback")),
        )

    async def _call_with_retry(self, fn, *args, **kwargs):
        """Call a function with retry logic."""
        from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_fixed(backoff),
            reraise=True,
        ):
            with attempt:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

        # This line should never be reached due to reraise=True above
        raise RuntimeError("Retry loop completed without result or exception")


class JudgeRefineExecutor(Executor):
    """Executor for judge evaluation and refinement."""

    def __init__(self, executor_id: str, context: SupervisorContext) -> None:
        """Initialize the judge refine executor."""
        super().__init__(id=executor_id)
        self.context = context

    @handler
    async def handle_quality(
        self,
        quality_msg: QualityMessage,
        ctx: WorkflowContext[QualityMessage, FinalResultMessage],
    ) -> None:
        """Handle a quality message."""
        with optional_span(
            "JudgeRefineExecutor.handle_quality", attributes={"task": quality_msg.task}
        ):
            task = quality_msg.task
            result = quality_msg.result
            agents = self.context.agents or {}
            start_t = perf_counter()

            logger.info("Starting judge evaluation and refinement phase...")

            judge_evaluations = []
            refinement_performed = False
            current_result = result

            # Helper to yield streaming updates
            async def _yield_update(status_msg: str, phase_state: str = "in_progress"):
                partial_msg = FinalResultMessage(
                    result=current_result,
                    routing=quality_msg.routing
                    or RoutingDecision(
                        task=task, assigned_to=(), mode=ExecutionMode.DELEGATED, subtasks=()
                    ),
                    quality=quality_msg.quality,  # Current quality snapshot
                    judge_evaluations=judge_evaluations,
                    execution_summary={"status": status_msg},
                    phase_timings=self.context.latest_phase_timings.copy(),
                    phase_status={**self.context.latest_phase_status, "judge": phase_state},
                    metadata={**quality_msg.metadata, "streaming_status": status_msg},
                )
                await ctx.yield_output(partial_msg)

            if self.context.config.enable_judge and "Judge" in agents:
                try:
                    await _yield_update("Starting Judge evaluation...")
                    judge_timeout = getattr(self.context.config, "judge_timeout_seconds", None)

                    async def run_judge():
                        return await self._run_judge_phase(task, current_result, agents)

                    if judge_timeout and judge_timeout > 0:
                        try:
                            judge_eval = await asyncio.wait_for(run_judge(), timeout=judge_timeout)
                        except TimeoutError:
                            logger.warning("Judge evaluation timed out")
                            judge_eval = None
                    else:
                        judge_eval = await run_judge()

                    if judge_eval:
                        judge_evaluations.append(judge_eval)
                        await _yield_update(f"Judge score: {judge_eval.get('score', 0)}")

                        refinement_rounds = 0
                        while (
                            refinement_rounds < self.context.config.max_refinement_rounds
                            and judge_eval.get("refinement_needed", "no").lower() == "yes"
                            and judge_eval.get("score", 0.0) < self.context.config.judge_threshold
                        ):
                            refinement_rounds += 1
                            agent_name = judge_eval.get("refinement_agent")
                            if not agent_name:
                                agent_name = self._determine_refinement_agent(
                                    judge_eval.get("missing_elements", "")
                                )

                            if agent_name not in agents:
                                break

                            await _yield_update(
                                f"Refining with {agent_name} (Round {refinement_rounds})..."
                            )

                            refinement_task = self._build_refinement_task(
                                current_result, judge_eval
                            )
                            try:
                                refined_result = await agents[agent_name].run(refinement_task)
                                current_result = (
                                    str(refined_result) if refined_result else current_result
                                )
                                refinement_performed = True
                            except Exception as e:
                                logger.warning(
                                    f"Refinement failed with {agent_name} (Round {refinement_rounds}): {e}"
                                )
                                break

                            # Re-evaluate
                            await _yield_update("Re-evaluating refinement...")
                            if judge_timeout and judge_timeout > 0:
                                try:
                                    judge_eval = await asyncio.wait_for(
                                        run_judge(), timeout=judge_timeout
                                    )
                                except TimeoutError:
                                    break
                            else:
                                judge_eval = await run_judge()

                            if judge_eval:
                                judge_evaluations.append(judge_eval)
                                await _yield_update(
                                    f"New Judge score: {judge_eval.get('score', 0)}"
                                )
                                if (
                                    judge_eval.get("score", 0.0)
                                    >= self.context.config.judge_threshold
                                ):
                                    break
                            else:
                                break

                except Exception as e:
                    logger.exception(f"Judge phase failed: {e}")

            # Fallback refinement
            last_judge_eval = judge_evaluations[-1] if judge_evaluations else None
            judge_passed = (
                self.context.config.enable_judge
                and last_judge_eval
                and last_judge_eval.get("score", 0.0) >= self.context.config.judge_threshold
            )

            if (
                not refinement_performed
                and not judge_passed
                and self.context.config.enable_refinement
                and quality_msg.quality.score < self.context.config.refinement_threshold
            ):
                with contextlib.suppress(Exception):
                    current_result = await refine_results(
                        current_result, quality_msg.quality.improvements, agents
                    )

            duration = max(0.0, perf_counter() - start_t)
            self.context.latest_phase_timings["judge"] = duration
            self.context.latest_phase_status["judge"] = "success"

            final_quality = quality_msg.quality
            if judge_evaluations:
                last_judge = judge_evaluations[-1]
                final_quality = QualityReport(
                    score=last_judge.get("score", final_quality.score),
                    missing=final_quality.missing,
                    improvements=final_quality.improvements,
                    judge_score=last_judge.get("score"),
                    final_evaluation=last_judge,
                    used_fallback=final_quality.used_fallback,
                )

            execution_summary = {}
            if self.context.dspy_supervisor:
                execution_summary = self.context.dspy_supervisor.get_execution_summary()

            # Inject tool usage into summary for history persistence
            if "tool_usage" in quality_msg.metadata:
                execution_summary["tool_usage"] = quality_msg.metadata["tool_usage"]

            routing_decision = quality_msg.routing
            if routing_decision is None and "routing" in quality_msg.metadata:
                routing_data = quality_msg.metadata["routing"]
                if isinstance(routing_data, RoutingDecision):
                    routing_decision = routing_data
                elif isinstance(routing_data, dict):
                    routing_decision = RoutingDecision.from_mapping(routing_data)

            if routing_decision is None:
                routing_decision = RoutingDecision(
                    task=task,
                    assigned_to=(),
                    mode=ExecutionMode.DELEGATED,
                    subtasks=(task,),
                    tool_requirements=(),
                    confidence=0.0,
                )

            final_msg = FinalResultMessage(
                result=current_result,
                routing=routing_decision,
                quality=final_quality,
                judge_evaluations=judge_evaluations,
                execution_summary=execution_summary,
                phase_timings=self.context.latest_phase_timings.copy(),
                phase_status=self.context.latest_phase_status.copy(),
                metadata=quality_msg.metadata,
            )
            await ctx.yield_output(final_msg)  # type: ignore[arg-type]

    async def _run_judge_phase(
        self,
        task: str,
        result: str,
        agents: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the judge phase."""

        async def get_criteria(t):
            return await get_quality_criteria(
                t,
                agents,
                lambda a, p: call_judge_with_reasoning(
                    a, p, self.context.config.judge_reasoning_effort
                ),
            )

        def get_refinement_agent(missing):
            return self._determine_refinement_agent(missing)

        # Inline judge phase logic from shared module
        judge_agent = agents.get("Judge")
        if not judge_agent:
            return {"score": 10.0, "refinement_needed": "no"}

        criteria = await get_criteria(task)
        prompt = f"Evaluate:\nTask: {task}\nCriteria: {criteria}\nResult: {result}\nProvide score, missing elements, refinement needed."

        response = await call_judge_with_reasoning(
            judge_agent, prompt, self.context.config.judge_reasoning_effort
        )

        return parse_judge_response(
            str(response),
            task,
            result,
            criteria,
            self.context.config,
            get_refinement_agent,
        )

    def _determine_refinement_agent(self, missing: str) -> str | None:
        """Determine the best agent for refinement."""
        m = missing.lower()
        if "citation" in m or "source" in m:
            return "Researcher"
        elif "code" in m or "calculation" in m:
            return "Analyst"
        return "Writer"

    def _build_refinement_task(self, result: str, eval_data: dict) -> str:
        """Build a refinement task."""
        return build_refinement_task(result, eval_data)
