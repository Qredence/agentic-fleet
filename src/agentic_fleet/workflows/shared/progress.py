from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict
from time import perf_counter
from typing import Any

from ...dspy_modules.supervisor import DSPySupervisor
from ..orchestration import SupervisorContext
from .models import ProgressReport

logger = logging.getLogger(__name__)

CallWithRetry = Callable[..., Awaitable[Any]]
NormalizeProgress = Callable[[Any], dict[str, Any]]
FallbackProgress = Callable[[], dict[str, Any]]
RecordPhaseStatus = Callable[[str, str], None]


def progress_report_from_legacy(payload: Mapping[str, Any]) -> ProgressReport:
    action = str(payload.get("action", "continue") or "continue").strip().lower()
    if action not in {"continue", "refine", "complete", "escalate"}:
        action = "continue"

    return ProgressReport(
        action=action,
        feedback=str(payload.get("feedback", "") or ""),
        used_fallback=bool(payload.get("used_fallback", False)),
    )


def progress_report_to_legacy(progress: ProgressReport) -> dict[str, Any]:
    legacy = asdict(progress)
    legacy["used_fallback"] = progress.used_fallback
    return legacy


async def run_progress_phase(
    *,
    task: str,
    result: str,
    context: SupervisorContext,
    supervisor: DSPySupervisor,
    call_with_retry: CallWithRetry,
    normalize_progress: NormalizeProgress,
    fallback_progress: FallbackProgress,
    record_phase_status: RecordPhaseStatus,
) -> ProgressReport:
    start_t = perf_counter()
    used_fallback = False
    try:
        raw_progress = await call_with_retry(
            supervisor.evaluate_progress,
            original_task=task,
            completed=result,
            status="completion",
        )
        payload = normalize_progress(raw_progress)
    except Exception as exc:
        logger.exception("DSPy progress evaluation failed; using fallback: %s", exc)
        payload = fallback_progress()
        used_fallback = True

    record_phase_status("progress", "fallback" if used_fallback else "success")
    payload["used_fallback"] = used_fallback
    # Record timing and guardrail
    duration = max(0.0, perf_counter() - start_t)
    context.latest_phase_timings["progress"] = duration
    try:
        threshold = float(getattr(context.config, "slow_execution_threshold", 0))
        if threshold and duration > threshold:
            logger.warning(
                "Progress phase exceeded slow_execution_threshold: %.2fs > %.2fs",
                duration,
                threshold,
            )
    except Exception as exc:
        logger.debug("Failed to check slow_execution_threshold in progress phase: %s", exc)
    return progress_report_from_legacy(payload)
