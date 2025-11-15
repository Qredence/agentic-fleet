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
    agents: dict[str, Any],
    results: Any,
    improvements: str,
) -> Any:
    """Refine results based on quality assessment."""
    refinement_task = f"Refine these results based on improvements needed:\n{results}\n\nImprovements: {improvements}"
    response = await agents["Writer"].run(refinement_task)
    return str(response)
