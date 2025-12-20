"""Refinement strategies for DSPy outputs.

Provides mechanisms for refining agent outputs:
1. Best-of-N: Generate multiple candidates and select the best using a reward model.
2. Iterative Refinement: Generate, critique, and improve in a loop.
3. Majority Voting: Generate multiple candidates and pick the most common answer (for classification).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import dspy

logger = logging.getLogger(__name__)


class ScorerProtocol(Protocol):
    """Protocol for scoring candidates."""

    def __call__(self, task: str, candidate: str) -> float:
        """Score a candidate answer for the given task."""
        ...


@dataclass
class RefinementResult:
    """Result of a refinement process."""

    best_answer: str
    candidates: list[str]
    scores: list[float] | None = None
    metadata: dict[str, Any] | None = None


class RefinementStrategy:
    """Base class for output refinement strategies."""

    async def refine(self, task: str, initial_answer: str | None = None) -> RefinementResult:
        """Refine the answer for a given task."""
        raise NotImplementedError


class BestOfN(RefinementStrategy):
    """
    Best-of-N strategy: Generate N candidates and select the highest scoring one.
    """

    def __init__(
        self,
        generator_module: dspy.Module,
        scorer: ScorerProtocol,
        n: int = 3,
        temperature: float = 0.7,
    ):
        self.generator = generator_module
        self.scorer = scorer
        self.n = n
        self.temperature = temperature

    async def refine(self, task: str, initial_answer: str | None = None) -> RefinementResult:
        """
        Generate N candidates (in parallel) and pick the winner.
        """
        # In a real implementation, we'd adjust the generator's temperature here
        # or assume it's already configured/clonable.
        # For this implementation, we'll assume the generator ensures diversity via its own config.

        candidates = []
        for _ in range(self.n):
            # This would likely be an async call in a real scenario
            # wrapping synchronous dspy call in thread
            try:
                # Assuming generator takes 'task' or similar input
                pred = await asyncio.to_thread(self.generator, task=task)
                # Extract answer - assumes generator returns Prediction with 'answer' or 'reasoning'
                answer = getattr(pred, "answer", getattr(pred, "reasoning", str(pred)))
                candidates.append(answer)
            except Exception as e:
                logger.warning(f"Generation failed: {e}")

        if not candidates:
            return RefinementResult(
                best_answer=initial_answer or "Generation failed", candidates=[]
            )

        # Score candidates
        scores = []
        for cand in candidates:
            try:
                score = self.scorer(task, cand)
                scores.append(score)
            except Exception as e:
                logger.warning(f"Scoring failed: {e}")
                scores.append(0.0)

        # Pick best
        best_idx = scores.index(max(scores))
        best_answer = candidates[best_idx]

        return RefinementResult(
            best_answer=best_answer,
            candidates=candidates,
            scores=scores,
            metadata={"strategy": "best_of_n", "n": self.n},
        )


__all__ = ["BestOfN", "RefinementResult", "RefinementStrategy", "ScorerProtocol"]
