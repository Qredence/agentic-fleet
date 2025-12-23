"""Langfuse evaluation utilities for AgenticFleet.

Provides helpers for:
- LLM as judge evaluations
- Custom score tracking
- Trace evaluation
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from langfuse import get_client

    _LANGFUSE_AVAILABLE = True

    def evaluate_with_llm_judge(
        trace_id: str,
        criteria: str,
        *,
        model: str = "gpt-4o-mini",
        score_name: str = "llm_judge_score",
    ) -> dict[str, Any]:
        """Use LLM as a judge to evaluate a trace.

        Args:
            trace_id: The trace ID to evaluate
            criteria: Evaluation criteria (e.g., "Is the response accurate and complete?")
            model: Model to use for judging
            score_name: Name for the score

        Returns:
            Dictionary with evaluation results
        """
        try:
            client = get_client()

            # Fetch trace data
            trace = client.fetch_trace(trace_id)  # type: ignore[attr-defined]
            if not trace:
                logger.warning(f"Trace {trace_id} not found")
                return {"error": "Trace not found"}

            # Extract input and output from trace
            trace_input = trace.get("input", "")
            trace_output = trace.get("output", "")

            # Create evaluation prompt
            eval_prompt = f"""Evaluate the following interaction based on this criteria: {criteria}

Input: {trace_input}
Output: {trace_output}

Provide:
1. A score from 0.0 to 1.0
2. A brief explanation

Format your response as:
Score: <0.0-1.0>
Explanation: <your explanation>
"""

            # Call LLM for evaluation
            from openai import OpenAI

            openai_client = OpenAI()

            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator. Provide objective, constructive evaluations.",
                    },
                    {"role": "user", "content": eval_prompt},
                ],
                temperature=0.0,
            )

            eval_text = response.choices[0].message.content or ""

            # Parse score from response
            score = 0.5  # Default
            explanation = eval_text

            for line in eval_text.split("\n"):
                if line.lower().startswith("score:"):
                    try:
                        score_str = line.split(":")[1].strip()
                        score = float(score_str)
                        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                    except (ValueError, IndexError):
                        pass
                elif line.lower().startswith("explanation:"):
                    explanation = line.split(":", 1)[1].strip()

            # Add score to trace
            client.score(  # type: ignore[attr-defined]
                trace_id=trace_id,
                name=score_name,
                value=score,
                comment=explanation,
                metadata={
                    "evaluator": "llm_judge",
                    "model": model,
                    "criteria": criteria,
                },
            )

            return {
                "trace_id": trace_id,
                "score": score,
                "explanation": explanation,
                "criteria": criteria,
            }
        except Exception as e:
            logger.error(f"Failed to evaluate trace {trace_id}: {e}", exc_info=True)
            return {"error": str(e)}

    def add_custom_score(
        trace_id: str,
        name: str,
        value: float,
        *,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Add a custom score to a trace.

        Args:
            trace_id: The trace ID
            name: Score name (e.g., "quality", "relevance", "user_satisfaction")
            value: Score value (typically 0.0 to 1.0 or 0 to 10)
            comment: Optional comment
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_client()
            client.score(  # type: ignore[attr-defined]
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
                metadata=metadata or {},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add score to trace {trace_id}: {e}")
            return False

except ImportError:
    _LANGFUSE_AVAILABLE = False
    logger.debug("Langfuse not available - evaluation utilities disabled")

    def evaluate_with_llm_judge(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        """Placeholder for evaluate_with_llm_judge when Langfuse is unavailable."""
        return {"error": "Langfuse not available"}

    def add_custom_score(*args: Any, **kwargs: Any) -> bool:  # noqa: ARG001
        """Placeholder for add_custom_score when Langfuse is unavailable."""
        return False
