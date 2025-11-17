"""Refinement logic."""

from __future__ import annotations

from typing import Any


def build_refinement_task(current_result: str, judge_eval: dict[str, Any]) -> str:
    """Build a refinement task based on judge evaluation."""
    missing_elements = judge_eval.get("missing_elements", "")
    required_improvements = judge_eval.get("required_improvements", "")

    refinement_task = f"""Improve the following response based on the judge's evaluation:

Missing elements: {missing_elements}
Required improvements: {required_improvements}

Current response:
{current_result}

Please enhance the response by addressing the missing elements and required improvements."""

    return refinement_task


async def refine_results(
    results: Any,
    improvements: str,
    agents: dict[str, Any],
) -> Any:
    """Refine results based on quality assessment."""
    writer = agents.get("Writer")
    if writer is None:
        raise KeyError("Writer agent is required for refinement")
    refinement_task = f"Refine these results based on improvements needed:\n{results}\n\nImprovements: {improvements}"
    try:
        response = await writer.run(refinement_task)
        return str(response) if response is not None else str(results)
    except Exception:
        # Defensive: on any failure, return original results
        return str(results)
