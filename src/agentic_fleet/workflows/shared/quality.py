from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict
from typing import Any

from ..quality import (
    assess_quality as _assess_quality_dict,
)
from ..quality import (
    build_refinement_task,
)
from ..quality import (
    judge_phase as _judge_phase_dict,
)
from .models import QualityReport


def quality_report_from_legacy(payload: Mapping[str, Any]) -> QualityReport:
    return QualityReport(
        score=float(payload.get("score", 0.0) or 0.0),
        missing=str(payload.get("missing", "")),
        improvements=str(payload.get("improvements", "")),
        judge_score=payload.get("judge_score"),
        final_evaluation=payload.get("final_evaluation"),
        used_fallback=bool(payload.get("used_fallback", False)),
    )


def quality_report_to_legacy(report: QualityReport) -> dict[str, Any]:
    legacy = asdict(report)
    legacy["missing"] = report.missing
    legacy["improvements"] = report.improvements
    legacy["used_fallback"] = report.used_fallback
    return legacy


async def run_quality_phase(
    *,
    task: str,
    result: str,
    compiled_supervisor: Any,
    call_with_retry: Callable[..., Awaitable[Any] | Any],
    normalize_quality: Callable[[Any, str, str], dict[str, Any]],
    fallback_quality: Callable[[str, str], dict[str, Any]],
    record_status: Callable[[str, str], None],
) -> QualityReport:
    quality_dict = await _assess_quality_dict(
        task=task,
        result=result,
        compiled_supervisor=compiled_supervisor,
        call_with_retry=call_with_retry,
        normalize_quality=normalize_quality,
        fallback_quality=fallback_quality,
        record_status=record_status,
    )
    return quality_report_from_legacy(quality_dict)


async def run_judge_phase(
    *,
    task: str,
    result: str,
    agents: dict[str, Any],
    config: Any,
    get_quality_criteria_fn: Callable[[str], Awaitable[str]],
    parse_judge_response_fn: Callable[
        [str, str, str, str, Any, Callable[[str], str | None]], dict[str, Any]
    ],
    determine_refinement_agent_fn: Callable[[str], str | None],
    record_status: Callable[[str, str], None],
) -> dict[str, Any]:
    return await _judge_phase_dict(
        task=task,
        result=result,
        agents=agents,
        config=config,
        get_quality_criteria_fn=get_quality_criteria_fn,
        parse_judge_response_fn=parse_judge_response_fn,
        determine_refinement_agent_fn=determine_refinement_agent_fn,
        record_status=record_status,
    )


__all__ = [
    "build_refinement_task",
    "quality_report_from_legacy",
    "quality_report_to_legacy",
    "run_judge_phase",
    "run_quality_phase",
]
