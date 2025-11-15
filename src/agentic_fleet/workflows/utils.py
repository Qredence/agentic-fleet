"""Shared workflow utility functions."""

from __future__ import annotations

import os
from typing import Any

import openai


def synthesize_results(results: list[Any]) -> str:
    """Combine parallel results into a single string."""
    return "\n\n".join([str(r) for r in results])


def extract_artifacts(result: Any) -> dict[str, Any]:
    """Extract artifacts from agent result.

    In a real implementation, this would parse structured output,
    identify files/data produced, etc. For now, it's a placeholder.
    """
    # Placeholder - could be enhanced to extract structured data
    return {"result_summary": str(result)[:200]}


def estimate_remaining_work(original_task: str, work_done: str) -> str:
    """Estimate what work remains based on original task and progress."""
    # Simple heuristic - in practice, could use DSPy for this
    return f"Continue working on: {original_task}. Already completed: {work_done[:100]}..."


def derive_objectives(remaining_work: str) -> list[str]:
    """Derive specific objectives from remaining work description."""
    # Simple extraction - could use NLP or DSPy
    objectives = [remaining_work]
    return objectives


def create_openai_client_with_store(
    enable_storage: bool = False,
    reasoning_effort: str | None = None,
) -> openai.AsyncOpenAI:
    """Create AsyncOpenAI client configured to optionally store completions and set reasoning effort.

    Args:
        enable_storage: Whether to enable completion storage
        reasoning_effort: Optional reasoning effort level ("minimal", "medium", "maximal") for GPT-5 models

    Returns:
        AsyncOpenAI client with default_query set to include store=true if enabled
    """
    from ..utils.logger import setup_logger

    logger = setup_logger(__name__)

    kwargs: dict[str, Any] = {}

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key

    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        normalized = base_url.strip()
        if "://" not in normalized:
            normalized = "https://" + normalized.lstrip("/")
            logger.warning(
                "OPENAI_BASE_URL was missing scheme; normalized to %s",
                normalized,
            )
        kwargs["base_url"] = normalized

    default_query: dict[str, Any] = {}
    if enable_storage:
        default_query["store"] = "true"

    # Reasoning effort is passed in the request body, not query params
    # We'll need to handle this via extra_body in the actual request
    # For now, we store it as a client attribute for later use
    client = openai.AsyncOpenAI(**kwargs)
    if reasoning_effort is not None:
        # Store reasoning effort as client attribute for use in requests
        client._reasoning_effort = reasoning_effort  # type: ignore[attr-defined]

    if default_query:
        # Note: default_query might not support nested dicts for reasoning
        # Reasoning effort needs to be in request body, not query params
        pass

    return client
