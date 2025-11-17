from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from time import perf_counter
from typing import Any

from ...utils.models import RoutingDecision
from ..orchestration import SupervisorContext
from .analysis import analysis_result_from_legacy
from .models import AnalysisResult, RoutingPlan

logger = logging.getLogger(__name__)

CallWithRetry = Callable[..., Awaitable[Any]]
ValidateRoutingPrediction = Callable[[Any, str], RoutingDecision]
NormalizeRoutingDecisionFn = Callable[[RoutingDecision | Mapping[str, Any], str], RoutingDecision]
FallbackRoutingDecision = Callable[[str], RoutingDecision]
RecordPhaseStatus = Callable[[str, str], None]


def routing_plan_to_legacy(plan: RoutingPlan) -> RoutingDecision:
    return plan.decision


async def run_routing_phase(
    *,
    task: str,
    analysis: AnalysisResult | Mapping[str, Any],
    context: SupervisorContext,
    call_with_retry: CallWithRetry,
    compiled_supervisor: Any,
    validate_routing_prediction: ValidateRoutingPrediction,
    normalize_routing_decision_fn: NormalizeRoutingDecisionFn,
    fallback_routing_decision: FallbackRoutingDecision,
    record_phase_status: RecordPhaseStatus,
) -> RoutingPlan:
    start_t = perf_counter()
    analysis_data = (
        analysis if isinstance(analysis, AnalysisResult) else analysis_result_from_legacy(analysis)
    )

    agents = context.agents or {}
    team_descriptions = {name: getattr(agent, "description", "") for name, agent in agents.items()}

    used_fallback = False

    try:
        raw_routing = await call_with_retry(
            compiled_supervisor.route_task,
            task=task,
            team=team_descriptions,
            context=analysis_data.search_context or "",
        )
        routing = validate_routing_prediction(raw_routing, task)
        routing = normalize_routing_decision_fn(routing, task)
    except Exception as exc:
        logger.exception("DSPy routing failed; using fallback: %s", exc)
        routing = normalize_routing_decision_fn(
            fallback_routing_decision(task),
            task,
        )
        used_fallback = True

    from ..routing.helpers import detect_routing_edge_cases  # Local to avoid cycles

    edge_cases = detect_routing_edge_cases(task, routing)
    if edge_cases:
        logger.info(
            "Edge cases detected in routing for task '%s': %s",
            task[:50] + ("..." if len(task) > 50 else ""),
            ", ".join(edge_cases),
        )
        current_execution = context.current_execution or {}
        edge_case_store = current_execution.setdefault("edge_cases", [])
        edge_case_store.extend(edge_cases)

    record_phase_status("routing", "fallback" if used_fallback else "success")
    # Record timing and guardrail
    duration = max(0.0, perf_counter() - start_t)
    context.latest_phase_timings["routing"] = duration
    try:
        threshold = float(getattr(context.config, "slow_execution_threshold", 0))
        if threshold and duration > threshold:
            logger.warning(
                "Routing phase exceeded slow_execution_threshold: %.2fs > %.2fs",
                duration,
                threshold,
            )
    except Exception as exc:
        logger.debug(
            "Exception encountered while checking slow_execution_threshold: %s (ignored because timing is non-critical)",
            exc,
        )
    return RoutingPlan(decision=routing, edge_cases=edge_cases, used_fallback=used_fallback)
