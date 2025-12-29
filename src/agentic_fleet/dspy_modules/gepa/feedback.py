"""
GEPA Feedback Logic Module

This module explicitly implements the feedback and scoring mechanisms for the GEPA optimizer.
It separates the "how to score" logic from the "how to optimize" loop in `gepa_optimizer.py`.

It adheres to the DSPy `ScoreWithFeedback` interface, providing:
1. A numerical score (0.0-1.0 or scaled to perfect_score).
2. Detailed, actionable text feedback for the optimizer to include in prompt reflection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

logger = logging.getLogger(__name__)


@dataclass
class GEPAHeuristics:
    """Configurable heuristics and weights for the feedback metric."""

    ASSIGNMENT_WEIGHT: float = 0.5
    MODE_WEIGHT: float = 0.3
    TOOL_WEIGHT: float = 0.1
    LATENCY_WEIGHT: float = 0.1

    # Keyword lists for edge case detection
    AMBIGUOUS_KEYWORDS: tuple[str, ...] = (
        "maybe",
        "possibly",
        "could",
        "might",
        "perhaps",
        "either",
        "or",
    )
    TIME_KEYWORDS: tuple[str, ...] = (
        "latest",
        "current",
        "recent",
        "today",
        "now",
        "2025",
        "2026",
        "future",
    )

    # Task type keywords for pattern matching
    RESEARCH_KEYWORDS: tuple[str, ...] = ("research", "find", "search", "latest", "current")
    ANALYSIS_KEYWORDS: tuple[str, ...] = ("analyze", "calculate", "data", "compute")
    WRITING_KEYWORDS: tuple[str, ...] = ("write", "create", "draft", "compose")
    REVIEW_KEYWORDS: tuple[str, ...] = ("review", "check", "validate", "verify")
    MULTISTEP_KEYWORDS: tuple[str, ...] = ("and", "also", "then", "multiple")


DEFAULT_HEURISTICS = GEPAHeuristics()


@dataclass
class RoutingDecision:
    """Represents routing decisions for comparison and analysis."""

    agents: list[str]
    mode: str
    tools: list[str]
    latency_budget: str = "medium"


def normalize_agents(value: Any) -> list[str]:
    """Normalize agent identifiers into a list of non-empty, stripped strings."""
    if not value:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [str(value)]
    return [part.strip() for part in parts if part and str(part).strip()]


def normalize_mode(value: Any) -> str:
    """Normalize the execution mode value."""
    if not value:
        return ""
    return str(value).strip().lower()


def normalize_tools(value: Any) -> list[str]:
    """Normalize a value representing tool names into a list of lowercased, stripped strings."""
    if not value:
        return []
    parts = value.replace("\n", ",").split(",") if isinstance(value, str) else list(value)
    return [part.strip().lower() for part in parts if part and str(part).strip()]


def jaccard_similarity(expected: list[str], predicted: list[str]) -> float:
    """Calculate Jaccard similarity index between two lists of strings."""
    if not expected and not predicted:
        return 1.0
    if not expected or not predicted:
        return 0.0
    exp_set = {item.lower() for item in expected}
    pred_set = {item.lower() for item in predicted}
    intersection = len(exp_set & pred_set)
    union = len(exp_set | pred_set)
    return intersection / union if union else 0.0


class RoutingFeedbackMetric:
    """
    Callable metric class for GEPA that provides both scoring and rich, actionable feedback.
    """

    def __init__(self, perfect_score: float = 1.0, heuristics: GEPAHeuristics = DEFAULT_HEURISTICS):
        self.perfect_score = perfect_score
        self.heuristics = heuristics

        # specific check to ensure weights are valid
        total_weight = (
            self.heuristics.ASSIGNMENT_WEIGHT
            + self.heuristics.MODE_WEIGHT
            + self.heuristics.TOOL_WEIGHT
            + self.heuristics.LATENCY_WEIGHT
        )
        if abs(total_weight - 1.0) >= 1e-8:
            raise ValueError(f"GEPA scoring weights must sum to 1.0. Current sum: {total_weight}")

    def _detect_edge_cases(
        self,
        task: str,
        expected: RoutingDecision,
        predicted: RoutingDecision,
    ) -> list[str]:
        """Detect edge cases in routing decisions."""
        edge_cases = []
        task_lower = task.lower()

        # Detect ambiguous tasks
        if any(kw in task_lower for kw in self.heuristics.AMBIGUOUS_KEYWORDS):
            edge_cases.append(
                "This task involves ambiguity - consider clarifying requirements before routing."
            )

        # Detect tool conflicts
        if expected.tools and predicted.tools:
            missing_tools = set(expected.tools) - set(predicted.tools)
            extra_tools = set(predicted.tools) - set(expected.tools)
            # FIX: Previously checked `if missing_tools and extra_tools`
            # Now we report if there is ANY mismatch (conflict isn't just swapping, it's any diff)
            if missing_tools or extra_tools:
                edge_cases.append(
                    f"Tool conflict detected: missing {missing_tools} and/or included {extra_tools}."
                )

        # Detect mode edge cases
        if expected.mode != predicted.mode:
            if expected.mode == "parallel" and predicted.mode == "sequential":
                edge_cases.append(
                    "Edge case: Parallel mode required for independent subtasks, but sequential was chosen."
                )
            elif expected.mode == "sequential" and predicted.mode == "parallel":
                edge_cases.append(
                    "Edge case: Sequential mode required for dependent subtasks, but parallel was chosen."
                )

        # Detect agent mismatch patterns
        if expected.agents != predicted.agents:
            if len(expected.agents) > len(predicted.agents):
                edge_cases.append(
                    "Edge case: Under-assignment. Task complex/multifaceted but assigned to fewer agents."
                )
            elif len(expected.agents) < len(predicted.agents):
                edge_cases.append(
                    "Edge case: Over-assignment. Simple task assigned to too many agents."
                )

        # Detect time-sensitive queries
        if any(kw in task_lower for kw in self.heuristics.TIME_KEYWORDS):
            pred_tools_lower = [t.lower() for t in predicted.tools]
            if "tavilysearchtool" not in pred_tools_lower:
                edge_cases.append(
                    "Edge case: Time-sensitive query likely requires TavilySearchTool for current data."
                )

        return edge_cases

    def _get_clarifying_examples(
        self,
        task: str,
        expected_mode: str,
        expected_tools: list[str],
        assignment_score: float,
        mode_score: float,
        tool_score: float,
    ) -> list[str]:
        """Generate clarifying examples for similar tasks."""
        examples = []
        task_lower = task.lower()

        # Agent selection examples
        if assignment_score < 1.0:
            if any(k in task_lower for k in self.heuristics.RESEARCH_KEYWORDS):
                examples.append("For research tasks, assign to Researcher agent.")
            if any(k in task_lower for k in self.heuristics.ANALYSIS_KEYWORDS):
                examples.append("For analysis tasks, assign to Analyst agent.")
            if any(k in task_lower for k in self.heuristics.WRITING_KEYWORDS):
                examples.append("For writing tasks, assign to Writer agent.")
            if any(k in task_lower for k in self.heuristics.REVIEW_KEYWORDS):
                examples.append("For review tasks, assign to Reviewer agent.")

        # Mode selection examples
        if mode_score < 1.0:
            if expected_mode == "parallel":
                examples.append(
                    "Use parallel mode when subtasks are independent (e.g., 'Research X, analyze Y')."
                )
            elif expected_mode == "sequential":
                examples.append(
                    "Use sequential mode when subtasks depend on each other (e.g., 'Research X then write Y')."
                )
            elif expected_mode == "delegated":
                examples.append("Use delegated mode for simple, atomic tasks handled by one agent.")

        # Tool selection examples
        if tool_score < 1.0:
            exp_tools_lower = [t.lower() for t in expected_tools]
            if "tavilysearchtool" in exp_tools_lower:
                examples.append("Tasks needing real-time info require TavilySearchTool.")
            if "hostedcodeinterpretertool" in exp_tools_lower:
                examples.append("Tasks needing computation/math require HostedCodeInterpreterTool.")

        return examples

    def __call__(
        self, gold: Any, pred: Any, trace=None, pred_name=None, pred_trace=None
    ) -> ScoreWithFeedback:
        """
        Calculate score and generate feedback following DSPy GEPA best practices.

        This method implements the GEPAFeedbackMetric interface required by dspy.GEPA.
        It provides both numerical scoring (0.0 to perfect_score) and detailed textual
        feedback for the optimizer to use in prompt refinement.

        Args:
            gold: Ground truth example (dspy.Example with expected routing decision)
            pred: Predicted example (dspy.Example with model's routing decision)
            trace: Optional execution trace (for debugging)
            pred_name: Optional prediction name (for debugging)
            pred_trace: Optional prediction trace (for debugging)

        Returns:
            ScoreWithFeedback containing score (float) and feedback (str)
        """
        # Extract task for edge-case detection
        task = getattr(gold, "task", getattr(pred, "task", ""))

        expected_agents = normalize_agents(getattr(gold, "assigned_to", ""))
        predicted_agents = normalize_agents(getattr(pred, "assigned_to", ""))

        assignment_score = jaccard_similarity(expected_agents, predicted_agents)

        expected_mode = normalize_mode(getattr(gold, "execution_mode", getattr(gold, "mode", "")))
        predicted_mode = normalize_mode(getattr(pred, "execution_mode", getattr(pred, "mode", "")))
        mode_score = 1.0 if expected_mode == predicted_mode else 0.0

        expected_tools = normalize_tools(getattr(gold, "tool_requirements", []))
        predicted_tools = normalize_tools(getattr(pred, "tool_requirements", []))

        # Tool score: Jaccard is generally more robust for sets than pure Recall
        # But sticking closer to original logic for now: Intersection / Expected
        # If expected is empty, and predicted is not, penalize?
        # Original logic: if expected is empty, score 1.0 regardless of predicted.
        # Let's improve: if expected is empty and predicted is NOT empty, that's a penalty (precision loss).
        # Let's switch to Jaccard for tools as well for symmetry.
        tool_score = jaccard_similarity(expected_tools, predicted_tools)

        # Latency check
        expected_latency = getattr(gold, "latency_budget", "medium")
        predicted_latency = getattr(pred, "latency_budget", "medium")
        latency_score = 1.0 if expected_latency == predicted_latency else 0.0

        weighted_score = (
            (assignment_score * self.heuristics.ASSIGNMENT_WEIGHT)
            + (mode_score * self.heuristics.MODE_WEIGHT)
            + (tool_score * self.heuristics.TOOL_WEIGHT)
            + (latency_score * self.heuristics.LATENCY_WEIGHT)
        )
        final_score = max(0.0, min(self.perfect_score, weighted_score * self.perfect_score))

        # Build comprehensive feedback following DSPy tutorial patterns
        feedback_parts = []

        # Step 1: Overall assessment
        if final_score >= 0.9 * self.perfect_score:
            feedback_parts.append("✅ Routing decision is correct.")
        elif final_score >= 0.7 * self.perfect_score:
            feedback_parts.append("⚠️ Routing decision is mostly correct but has minor issues.")
        else:
            feedback_parts.append("❌ Routing decision needs significant improvement.")

        # Step 2: Edge-case detection
        expected_decision = RoutingDecision(
            agents=expected_agents,
            mode=expected_mode,
            tools=expected_tools,
            latency_budget=expected_latency,
        )
        predicted_decision = RoutingDecision(
            agents=predicted_agents,
            mode=predicted_mode,
            tools=predicted_tools,
            latency_budget=predicted_latency,
        )
        edge_cases = self._detect_edge_cases(task, expected_decision, predicted_decision)
        if edge_cases:
            feedback_parts.append("\n🔍 Edge Cases Detected:")
            for edge_case in edge_cases:
                feedback_parts.append(f"  • {edge_case}")

        # Step 3: Detailed component analysis
        feedback_parts.append("\n📊 Component Analysis:")

        # Agent assignment feedback
        if assignment_score == 1.0:
            feedback_parts.append("  ✅ Agent select: Match.")
        else:
            feedback_parts.append(
                f"  ❌ Agent select: Assigned {predicted_agents} but expected {expected_agents}."
            )

        # Mode selection feedback
        if mode_score == 1.0:
            feedback_parts.append(f"  ✅ Mode: '{expected_mode}' match.")
        else:
            feedback_parts.append(
                f"  ❌ Mode: Used '{predicted_mode}' but should use '{expected_mode}'."
            )

        # Tool selection feedback
        if tool_score == 1.0:
            feedback_parts.append("  ✅ Tools: Match.")
        else:
            missing = sorted(set(expected_tools) - set(predicted_tools))
            extra = sorted(set(predicted_tools) - set(expected_tools))
            if missing:
                feedback_parts.append(f"  ❌ Tools Missing: {', '.join(missing)}.")
            if extra:
                feedback_parts.append(f"  ⚠️ Tools Unnecessary: {', '.join(extra)}.")

        # Latency feedback
        if latency_score == 1.0:
            feedback_parts.append(f"  ✅ Latency match ('{expected_latency}').")
        else:
            feedback_parts.append(
                f"  ❌ Latency mismatch: {predicted_latency} vs {expected_latency}."
            )

        # Step 4: Clarifying examples for similar tasks
        if final_score < 0.9 * self.perfect_score:
            examples = self._get_clarifying_examples(
                task,
                expected_mode,
                expected_tools,
                assignment_score,
                mode_score,
                tool_score,
            )
            if examples:
                feedback_parts.append("\n💡 Hints:")
                for rule in examples:
                    feedback_parts.append(f"  • {rule}")

        feedback = "\n".join(feedback_parts)
        if not feedback.strip():
            feedback = "No specific feedback."

        return ScoreWithFeedback(score=final_score, feedback=feedback)
