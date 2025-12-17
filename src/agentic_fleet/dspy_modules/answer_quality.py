"""DSPy-based answer quality scoring helper.

Scores a final answer against the original user task on simple dimensions:
- groundness (is it grounded / factual w.r.t. the task?)
- relevance (does it address the task?)
- coherence (is it well-structured and readable?)

Falls back to a lightweight heuristic if DSPy or LM settings are unavailable.

NOTE: The DSPy module used here follows the offline-only compilation rule.
The AnswerQualityModule is compiled via `agentic-fleet gepa-optimize` and
cached to `.var/logs/compiled_answer_quality.pkl`. At runtime, the module
is loaded from cache rather than being constructed fresh.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..utils.cfg import DEFAULT_ANSWER_QUALITY_CACHE_PATH

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:  # pragma: no cover - DSPy might not be installed in all envs
    dspy = None  # type: ignore


# Module cache for lazy-loading compiled module (follows reasoner.py pattern)
_MODULE_CACHE: dict[str, Any] = {}


if dspy:

    class AnswerQualitySignature(dspy.Signature):
        """Score an answer on key quality dimensions (0 to 1)."""

        question = dspy.InputField(desc="Original user question/task")
        answer = dspy.InputField(desc="Assistant's final answer")
        groundness = dspy.OutputField(desc="Groundedness 0-1")
        relevance = dspy.OutputField(desc="Relevance to the question 0-1")
        coherence = dspy.OutputField(desc="Coherence/clarity 0-1")

    class AnswerQualityModule(dspy.Module):
        """DSPy module for scoring answer quality.

        This module wraps AnswerQualitySignature and is designed to be
        compiled offline via GEPA or BootstrapFewShot optimization.

        The compiled module is cached to DEFAULT_ANSWER_QUALITY_CACHE_PATH
        and loaded at runtime to avoid constructing dspy.Predict() on-the-fly.
        """

        def __init__(self) -> None:
            """
            Initialize the AnswerQualityModule and attach a DSPy predictor for the AnswerQualitySignature.

            Sets the `predictor` attribute to an object that performs predictions for the signature.
            """
            super().__init__()
            self.predictor: Any = dspy.Predict(AnswerQualitySignature)  # type: ignore[arg-type]

        def forward(self, question: str, answer: str) -> dspy.Prediction:  # type: ignore[name-defined]
            """
            Score an assistant answer along the dimensions of groundness, relevance, and coherence.

            Parameters:
                question (str): The original user question or task.
                answer (str): The assistant's final answer to be scored.

            Returns:
                dspy.Prediction: A prediction object containing quality
                    dimension scores (`groundness`, `relevance`,
                    `coherence`), each in the range 0.0 to 1.0.
            """
            return self.predictor(question=question, answer=answer)


def _get_answer_quality_module() -> Any | None:
    """Get the compiled AnswerQualityModule from cache.

    Follows the lazy-loading pattern from reasoner.py. The module is loaded
    once from the compiled cache and stored in _MODULE_CACHE for reuse.

    Returns:
        Compiled AnswerQualityModule or None if not available
    """
    if not dspy:
        return None

    cache_key = "answer_quality"
    if cache_key in _MODULE_CACHE:
        return _MODULE_CACHE[cache_key]

    cache_path = DEFAULT_ANSWER_QUALITY_CACHE_PATH

    if not os.path.exists(cache_path):
        logger.debug(
            "No compiled AnswerQualityModule found at %s. "
            "Run `agentic-fleet gepa-optimize` to compile. Using heuristic fallback.",
            cache_path,
        )
        _MODULE_CACHE[cache_key] = None
        return None

    try:
        # Import here to avoid circular imports
        from ..utils.compiler import load_compiled_module

        module = load_compiled_module(cache_path)
        if module is not None:
            _MODULE_CACHE[cache_key] = module
            logger.info("Loaded compiled AnswerQualityModule from %s", cache_path)
            return module
        logger.warning("Failed to deserialize AnswerQualityModule from %s", cache_path)
        _MODULE_CACHE[cache_key] = None
        return None
    except Exception as e:
        logger.warning("Error loading AnswerQualityModule: %s", e)
        _MODULE_CACHE[cache_key] = None
        return None


def get_uncompiled_module() -> Any | None:
    """Get an uncompiled AnswerQualityModule for training/compilation.

    This is used by the compilation infrastructure to get a fresh module
    instance for optimization.

    Returns:
        Fresh AnswerQualityModule instance or None if DSPy unavailable
    """
    if not dspy:
        return None
    return AnswerQualityModule()


def clear_module_cache() -> None:
    """Clear the module cache, forcing reload on next use."""
    _MODULE_CACHE.clear()
    logger.debug("AnswerQualityModule cache cleared")


def score_answer_with_dspy(question: str, answer: str) -> dict[str, Any]:
    """Score answer quality using precompiled DSPy module; fallback to heuristic.

    This function loads the precompiled AnswerQualityModule from cache. If the
    compiled module is not available (not yet compiled via `agentic-fleet gepa-optimize`),
    it falls back to a lightweight heuristic scorer.

    Args:
        question: Original user question/task
        answer: Assistant's final answer

    Returns:
        Dictionary with quality_score, quality_flag, and dimension scores
    """
    if not dspy:
        return _heuristic_score(question, answer)

    module = _get_answer_quality_module()
    if module is None:
        return _heuristic_score(question, answer)

    try:
        pred = module(question=question, answer=answer)
        # Ensure numeric and clipped
        g = _clip(pred.groundness)
        r = _clip(pred.relevance)
        c = _clip(pred.coherence)
        score = (g + r + c) / 3
        flag = "low_confidence" if score < 0.35 else None
        return {
            "quality_score": round(score, 3),
            "quality_flag": flag,
            "quality_groundness": g,
            "quality_relevance": r,
            "quality_coherence": c,
        }
    except Exception as e:
        logger.debug("DSPy scoring failed, using heuristic: %s", e)
        return _heuristic_score(question, answer)


def _clip(val: Any) -> float:
    try:
        f = float(val)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, f))


def _heuristic_score(question: str, answer: str) -> dict[str, Any]:
    ans = answer.strip()
    if not ans:
        return {
            "quality_score": 0.0,
            "quality_flag": "empty",
            "quality_groundness": 0.0,
            "quality_relevance": 0.0,
            "quality_coherence": 0.0,
        }

    lower = ans.lower()
    bad_phrases = ["i don't know", "cannot help", "sorry", "unable to", "as an ai"]
    penalty = any(p in lower for p in bad_phrases)

    wc = len(ans.split())
    base = min(wc / 60, 1.0)

    import re

    task_words = {w for w in re.findall(r"[a-zA-Z0-9]+", question.lower()) if len(w) > 3}
    ans_words = {w for w in re.findall(r"[a-zA-Z0-9]+", lower) if len(w) > 3}
    overlap = len(task_words & ans_words) / max(len(task_words) or 1, 1)

    coherence = 0.6 + min(base, 1.0) * 0.4
    ground = base * 0.7 + overlap * 0.3
    rel = overlap
    score = (ground + rel + coherence) / 3
    if penalty:
        score *= 0.6

    flag = "low_confidence" if score < 0.35 else None
    return {
        "quality_score": round(score, 3),
        "quality_flag": flag,
        "quality_groundness": round(ground, 3),
        "quality_relevance": round(rel, 3),
        "quality_coherence": round(coherence, 3),
    }


__all__ = [
    "AnswerQualityModule",
    "AnswerQualitySignature",
    "clear_module_cache",
    "get_uncompiled_module",
    "score_answer_with_dspy",
]
