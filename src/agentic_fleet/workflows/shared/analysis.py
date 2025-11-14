from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict
from typing import Any

from ...dspy_modules.supervisor import DSPySupervisor
from ..orchestration import SupervisorContext
from .models import AnalysisResult

logger = logging.getLogger(__name__)

CallWithRetry = Callable[..., Awaitable[Any]]
NormalizeAnalysis = Callable[[Any, str], dict[str, Any]]
FallbackAnalysis = Callable[[str], dict[str, Any]]
RecordPhaseStatus = Callable[[str, str], None]


def _to_analysis_result(payload: Mapping[str, Any]) -> AnalysisResult:
    complexity = str(payload.get("complexity", "moderate") or "moderate")
    capabilities = [str(cap).strip() for cap in payload.get("capabilities", []) if str(cap).strip()]
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
        needs_web_search=bool(payload.get("needs_web_search", False)),
        search_query=str(payload.get("search_query", "") or ""),
    )


def analysis_result_from_legacy(payload: Mapping[str, Any]) -> AnalysisResult:
    return _to_analysis_result(payload)


def analysis_result_to_legacy(result: AnalysisResult) -> dict[str, Any]:
    legacy = asdict(result)
    legacy["capabilities"] = list(result.capabilities)
    legacy["tool_requirements"] = list(result.tool_requirements)
    return legacy


async def run_analysis_phase(
    *,
    task: str,
    context: SupervisorContext,
    compiled_supervisor: DSPySupervisor,
    supervisor: DSPySupervisor,
    call_with_retry: CallWithRetry,
    normalize_analysis_result: NormalizeAnalysis,
    fallback_analysis: FallbackAnalysis,
    record_phase_status: RecordPhaseStatus,
) -> AnalysisResult:
    cache_key = task.strip()
    cache = context.analysis_cache
    if cache:
        cached = cache.get(cache_key)
        if cached:
            logger.info("Cache hit: reusing DSPy task analysis for task hash.")
            record_phase_status("analysis", "cached")
            return _to_analysis_result(cached)

    used_fallback = False
    try:
        raw_analysis = await call_with_retry(
            compiled_supervisor.analyze_task,
            task,
            perform_search=False,
        )
        analysis_payload = normalize_analysis_result(raw_analysis, task)
    except Exception as exc:
        logger.exception("DSPy task analysis failed; using fallback: %s", exc)
        analysis_payload = fallback_analysis(task)
        used_fallback = True

    if (
        analysis_payload.get("needs_web_search")
        and analysis_payload.get("search_query")
        and not analysis_payload.get("search_context")
    ):
        try:
            search_context = await call_with_retry(
                supervisor.perform_web_search_async,
                analysis_payload["search_query"],
            )
            if search_context:
                analysis_payload["search_context"] = search_context
        except Exception as exc:
            logger.warning("Async web search failed: %s", exc)

    if cache:
        cache.set(cache_key, dict(analysis_payload))

    record_phase_status("analysis", "fallback" if used_fallback else "success")
    return _to_analysis_result(analysis_payload)
