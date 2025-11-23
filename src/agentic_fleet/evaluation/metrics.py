"""Metric computation utilities for evaluation framework.

Each metric function receives the task spec and workflow result metadata.
Functions must degrade gracefully if data is missing.
"""

from __future__ import annotations

import re
from typing import Any


def _safe_get(d: dict[str, Any], *path: str, default: Any = None) -> Any:
    """Safely retrieve nested dictionary values."""
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def metric_quality_score(_task: dict[str, Any], metadata: dict[str, Any]) -> float | None:
    """Extract quality score from metadata."""
    score = _safe_get(metadata, "quality", "score")
    if score is None:
        return None
    try:
        # Coerce numeric strings; ignore dict-like accidental values.
        if isinstance(score, int | float):
            return float(score)
        if isinstance(score, str):
            return float(score.split("/")[0]) if "/" in score else float(score)
        return None
    except (TypeError, ValueError):
        return None


def metric_latency_seconds(_task: dict[str, Any], metadata: dict[str, Any]) -> float | None:
    """Extract execution latency from metadata."""
    lat = metadata.get("execution_time")
    try:
        return float(lat) if lat is not None else None
    except (TypeError, ValueError):
        return None


def metric_routing_efficiency(_task: dict[str, Any], metadata: dict[str, Any]) -> float | None:
    """Calculate routing efficiency (unique agents / assigned agents)."""
    routing = metadata.get("routing") or {}
    agents = routing.get("agents") or []
    # Placeholder: efficiency = unique agents used / agents assigned (currently same list)
    try:
        assigned = len(agents)
        used = len(set(agents))
        return used / assigned if assigned else None
    except Exception:
        return None


def metric_refinement_triggered(_task: dict[str, Any], metadata: dict[str, Any]) -> int | None:
    """Check if refinement was triggered (1 if yes, 0 if no)."""
    # Represent as 1/0 for easier aggregation
    quality = metadata.get("quality") or {}
    improvements = quality.get("improvements")
    if improvements:
        # If improvements suggestions present, we treat as refinement triggered
        return 1
    return 0


def metric_keyword_success(task: dict[str, Any], _metadata: dict[str, Any]) -> int | None:
    """Check if all required keywords are present in the result."""
    keywords: list[str] = task.get("keywords") or []
    if not keywords:
        return None
    output_text = str(task.get("_result_text", ""))
    # All keywords must appear (case-insensitive)
    lowered = output_text.lower()
    success = all(k.lower() in lowered for k in keywords)
    return 1 if success else 0


METRIC_FUNCS = {
    "quality_score": metric_quality_score,
    "latency_seconds": metric_latency_seconds,
    "routing_efficiency": metric_routing_efficiency,
    "refinement_triggered": metric_refinement_triggered,
    "keyword_success": metric_keyword_success,
}


def metric_relevance_score(task: dict[str, Any], _metadata: dict[str, Any]) -> float | None:
    """Return fractional keyword coverage (semantic proxy).

    If 3 of 5 keywords appear, returns 0.6. Returns None if no keywords provided.
    """
    keywords: list[str] = task.get("keywords") or []
    if not keywords:
        return None
    output_text = str(task.get("_result_text", "")).lower()
    if not output_text:
        return 0.0
    matched = sum(1 for k in keywords if k.lower() in output_text)
    return matched / len(keywords)


def _approx_tokenize(text: str) -> list[str]:
    """Lightweight approximate tokenization (non-model specific).

    Splits on whitespace and punctuation boundaries; good enough for cost estimations
    without requiring external tokenizer libraries.
    """
    if not text:
        return []
    # Split on word boundaries and standalone punctuation
    return re.findall(r"\w+|[^\w\s]", text)


def metric_token_count(task: dict[str, Any], _metadata: dict[str, Any]) -> int | None:
    """Approximate token count of result text."""
    output_text = str(task.get("_result_text", "")).strip()
    if not output_text:
        return 0
    return len(_approx_tokenize(output_text))


def metric_estimated_cost_usd(task: dict[str, Any], metadata: dict[str, Any]) -> float | None:
    """Estimated cost in USD based on token_count.

    Uses a simple flat rate (0.0005 / 1K tokens) as a placeholder. If model info
    is available in metadata["model"], could be extended to use per-model pricing.
    """
    count = metric_token_count(task, metadata)
    if count is None:
        return None
    cost_per_1k = 0.0005  # placeholder blended input/output rate
    return round((count / 1000.0) * cost_per_1k, 8)


# Register new metrics
METRIC_FUNCS.update(
    {
        "relevance_score": metric_relevance_score,
        "token_count": metric_token_count,
        "estimated_cost_usd": metric_estimated_cost_usd,
    }
)


def compute_metrics(
    task: dict[str, Any], metadata: dict[str, Any], metric_names: list[str]
) -> dict[str, Any]:
    """Compute requested metrics for a task execution."""
    task_copy = dict(task)
    # Provide result text to keyword metric if available in metadata root result
    computed: dict[str, Any] = {}
    for name in metric_names:
        func = METRIC_FUNCS.get(name)
        if not func:
            computed[name] = None
            continue
        try:
            computed[name] = func(task_copy, metadata)
        except Exception:
            computed[name] = None
    return computed
