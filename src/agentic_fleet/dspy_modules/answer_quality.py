"""DSPy-based answer quality scoring helper.

Scores a final answer against the original user task on simple dimensions:
- groundness (is it grounded / factual w.r.t. the task?)
- relevance (does it address the task?)
- coherence (is it well-structured and readable?)

Falls back to a lightweight heuristic if DSPy or LM settings are unavailable.
"""

from __future__ import annotations

from typing import Any

try:
    import dspy
except ImportError:  # pragma: no cover - DSPy might not be installed in all envs
    dspy = None  # type: ignore


if dspy:

    class AnswerQualitySignature(dspy.Signature):
        """Score an answer on key quality dimensions (0 to 1)."""

        question = dspy.InputField(desc="Original user question/task")
        answer = dspy.InputField(desc="Assistant's final answer")
        groundness = dspy.OutputField(desc="Groundedness 0-1")
        relevance = dspy.OutputField(desc="Relevance to the question 0-1")
        coherence = dspy.OutputField(desc="Coherence/clarity 0-1")


def score_answer_with_dspy(question: str, answer: str) -> dict[str, Any]:
    """Attempt to score using DSPy; fallback to heuristic on failure."""
    if not dspy or not hasattr(dspy, "Predict"):
        return _heuristic_score(question, answer)

    try:
        predictor = dspy.Predict(AnswerQualitySignature)  # type: ignore[name-defined]
        pred = predictor(question=question, answer=answer)
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
    except Exception:
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


__all__ = ["score_answer_with_dspy"]
