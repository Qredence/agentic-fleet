"""Fast-path detection for simple tasks.

This module provides detection logic for tasks that can bypass the full
multi-agent orchestration pipeline and be handled by a simple direct response.
"""

from __future__ import annotations

import re

from ...dspy_modules.reasoner_utils import is_time_sensitive_task


class FastPathDetector:
    """Robust detection for tasks that can bypass the full agent orchestration."""

    def __init__(self, max_words: int = 60) -> None:
        self.max_words = max_words

        # 1. Complex Intent Patterns (Immediate Disqualification)
        # These imply a need for planning, multi-step reasoning, or deep research.
        self.complex_patterns = [
            r"\b(create|plan|design|build|architect)\b.*?\b(detailed|comprehensive|full)\b",
            r"\b(write|draft)\b.*?\b(report|article|paper|essay)\b",
            r"\b(research|investigate|analyze)\s",
            r"\b(compare|contrast)\s+and\s",
            r"\b(step\s+by\s+step|guide|tutorial)\b",
            r"\b(summary|summarize)\s+of\b",  # summarization typically needs context/retrieval
        ]

        # 2. Complex Keywords
        self.complex_keywords = {
            "election",
            "stock",
            "forecast",
            "prediction",
            "medical",
            "legal",
            "advice",  # generic advice often needs safety checks/reasoning
        }

        # 3. Fast Path Patterns (Immediate Qualification if short & not complex)
        self.simple_intents = [
            # Greetings / Heartbeats
            r"^(hi|hello|hey|greetings|ping|test|yo)\b",
            r"^(good\s+morning|good\s+afternoon|good\s+evening)\b",
            r"^(are\s+you\s+(there|awake|online))\?",
            r"^(thanks|thank\s+you)\b",
            # Basic Definitions / Factual
            r"^(define|meaning\s+of)\s+[\w\s]+$",
            r"^(what\s+is|who\s+is|where\s+is)\s+[\w\s]+\??$",
            r"^(what\s+does|what\s+are)\s+[\w\s]+\??$",
            r"^(when\s+is|when\s+was|when\s+did)\s+[\w\s]+\??$",
            r"^(why\s+is|why\s+does|why\s+do)\s+[\w\s]+\??$",
            r"^(how\s+do|how\s+does|how\s+is)\s+[\w\s]+\??$",
            # Simple explanations (short)
            r"^explain\s+[\w\s]{1,50}\??$",
            r"^describe\s+[\w\s]{1,50}\??$",
            # Yes/No questions (short)
            r"^(is|are|can|does|do|will|would|should|could)\s+[\w\s]{1,40}\??$",
            # Simple Math
            r"^\d+\s*[\+\-\*\/]\s*\d+$",
            r"^(calculate|solve)\s+\d+\s*[\+\-\*\/]",
            # Single-word or very short queries
            r"^[\w\-]+\??$",  # Single word questions (e.g., "Python?", "help")
            r"^[\w\-]+\s+[\w\-]+\??$",  # Two-word questions (e.g., "what time", "how many")
        ]

    def is_time_sensitive(self, task: str) -> bool:
        """Reuse the existing time sensitivity check logic."""
        return is_time_sensitive_task(task)

    def classify(self, task: str) -> bool:
        """
        Determine if a task should go to the Fast Path.

        Returns:
            True if the task is simple/routine and qualifies for Fast Path.
            False if the task requires full agent routing/planning.
        """
        task = task.strip()
        if not task:
            return True  # Empty task is trivial

        # 0. Length Check (Hard limit for Fast Path)
        if len(task.split()) > self.max_words:
            return False

        task_lower = task.lower()

        # 1. Check disqualifiers (Complex patterns/keywords)
        for pattern in self.complex_patterns:
            if re.search(pattern, task_lower):
                return False

        if any(w in task_lower for w in self.complex_keywords):
            return False

        # 2. Time Sensitivity Check
        # Fast Path typically cannot do fresh search efficiently (unless tool-enabled, but usually we route)
        if self.is_time_sensitive(task):
            return False

        # 3. Check Qualifiers (Simple Intents)
        for pattern in self.simple_intents:
            if re.search(pattern, task_lower):
                return True

        # 4. Fallback: If very short and not complex, assume simple (chatty)
        return len(task.split()) < 5


def is_simple_task(task: str, max_words: int | None = None) -> bool:
    """Wrapper for FastPathDetector classification."""
    detector = FastPathDetector(max_words=max_words if max_words is not None else 60)
    return detector.classify(task)
