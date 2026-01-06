"""
GEPA (Generalized Evolutionary Prompt Adaptation) Module

Combines feedback/scoring logic with optimization utilities for DSPy GEPA integration.

This module provides:
  • Feedback metrics (RoutingFeedbackMetric) for scoring routing decisions
  • Dataset preparation utilities (loading, splitting, harvesting from history)
  • GEPA optimizer integration (optimize_with_gepa)
  • Self-improvement utilities
"""

from __future__ import annotations

import contextlib
import json
import logging
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import dspy
from dspy.teleprompt.gepa.gepa import GEPAFeedbackMetric
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

from agentic_fleet.dspy_modules.lifecycle import get_reflection_lm
from agentic_fleet.utils.progress import NullProgressCallback, ProgressCallback
from agentic_fleet.utils.storage import HistoryManager
from agentic_fleet.utils.storage.cosmos import get_default_user_id, record_dspy_optimization_run

from .self_improvement import SelfImprovementEngine

logger = logging.getLogger(__name__)


# =============================================================================
# Feedback & Scoring (formerly feedback.py)
# =============================================================================


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


# =============================================================================
# Optimization Utilities (formerly optimizer.py)
# =============================================================================


class MaxWarningFilter(logging.Filter):
    """Filter to limit specific warning messages to max occurrences."""

    def __init__(self, max_count: int = 5, message_pattern: str = ""):
        super().__init__()
        self.max_count = max_count
        self.message_pattern = message_pattern
        self.count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records, limiting matches to max_count."""
        if self.message_pattern and self.message_pattern in record.getMessage():
            self.count += 1
            if self.count > self.max_count:
                # Suppress after max_count
                return False
            elif self.count == self.max_count:
                # Log a summary message on the last allowed warning
                logger.info(
                    f"Suppressing further '{self.message_pattern}' warnings "
                    f"(showed {self.max_count}, these are expected during GEPA reflection)"
                )
        return True


@contextlib.contextmanager
def warning_filter_context(target_logger: logging.Logger, filter_instance: logging.Filter):
    """Context manager for temporarily applying a logging filter.

    Ensures the filter is properly removed even if an exception occurs.

    Args:
        target_logger: Logger to apply filter to
        filter_instance: Filter instance to add/remove

    Example:
        >>> with warning_filter_context(logger, MaxWarningFilter(5, "pattern")):
        ...     # Filter is active here
        ...     run_noisy_code()
        # Filter is automatically removed here
    """
    target_logger.addFilter(filter_instance)
    try:
        yield
    finally:
        target_logger.removeFilter(filter_instance)


def load_example_dicts(examples_path: str) -> list[dict[str, Any]]:
    """
    Load supervisor training examples from JSON file.

    Args:
        examples_path: Path to JSON list of training records.

    Returns:
        List of example dictionaries (possibly empty).
    """
    path = Path(examples_path)
    if not path.exists():
        logger.warning("Training examples file not found: %s", examples_path)
        return []

    try:
        with open(path) as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.warning("Unexpected training data format at %s (expected list)", examples_path)
            return []

        return [record for record in data if isinstance(record, dict)]
    except Exception as exc:
        logger.error("Failed to load training examples from %s: %s", examples_path, exc)
        return []


def harvest_history_examples(
    *,
    min_quality: float = 8.0,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Convert recent high-quality executions into routing examples.

    Args:
        min_quality: Minimum quality score (0-10) required.
        limit: Max number of history entries to scan.

    Returns:
        List of example dictionaries derived from history.
    """
    history_manager = HistoryManager()
    executions = history_manager.load_history(limit=limit)
    if not executions:
        return []

    engine = SelfImprovementEngine(min_quality_score=min_quality, history_lookback=limit)
    harvested: list[dict[str, Any]] = []

    for execution in executions:
        quality = execution.get("quality", {})
        if quality.get("score", 0) < min_quality:
            continue

        example = engine.execution_to_example(execution)
        if example:
            harvested.append(example)

    return harvested


def dedupe_examples(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate routing examples based on task + assignment + mode."""
    seen = set()
    unique: list[dict[str, Any]] = []

    for record in records:
        assigned_to = record.get("assigned_to", [])
        normalized_agents = sorted(normalize_agents(assigned_to))
        fingerprint = "|".join(
            [
                record.get("task", "").strip().lower(),
                str(normalized_agents),
                record.get("mode", record.get("execution_mode", "")),
            ]
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(record)

    return unique


def convert_to_dspy_examples(records: Sequence[dict[str, Any]]) -> list[dspy.Example]:
    """Convert raw dictionaries into DSPy Example objects."""
    examples: list[dspy.Example] = []
    for record in records:
        try:
            example = dspy.Example(
                task=record.get("task", ""),
                team_capabilities=record.get("team", record.get("team_capabilities", "")),
                available_tools=record.get("available_tools", "No tools available"),
                current_context=record.get("context", ""),
                assigned_to=record.get("assigned_to", ""),
                execution_mode=record.get("mode", record.get("execution_mode", "")),
                tool_requirements=record.get("tool_requirements", []),
            ).with_inputs("task", "team_capabilities", "available_tools", "current_context")
            examples.append(example)
        except Exception as exc:
            logger.warning(
                "Skipping invalid training record (%s): %s",
                record.get("task", "unknown"),
                exc,
            )
            continue
    return examples


def prepare_gepa_datasets(
    *,
    base_examples_path: str,
    base_records: Sequence[dict[str, Any]] | None = None,
    extra_examples: Iterable[dict[str, Any]] | None = None,
    val_split: float = 0.2,
    seed: int = 13,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """
    Load, merge, dedupe, and split routing examples for GEPA.

    Args:
        base_examples_path: Path to core training JSON.
        extra_examples: Optional iterable (e.g., harvested history) to append.
        val_split: Fraction of records reserved for validation.
        seed: RNG seed for deterministic shuffles.

    Returns:
        (trainset, valset) of DSPy Example objects.
    """
    records: list[dict[str, Any]]
    if base_records is not None:
        records = list(base_records)
    else:
        records = load_example_dicts(base_examples_path)
    if extra_examples:
        records.extend(extra_examples)

    records = dedupe_examples(records)
    if not records:
        return [], []

    rng = random.Random(seed)
    rng.shuffle(records)

    val_size = int(len(records) * val_split) if val_split > 0 else 0
    if val_size == 0 and val_split > 0 and len(records) > 4:
        val_size = 1  # keep at least one validation example when we have data

    val_records = records[:val_size] if val_size else []
    train_records = records[val_size:] if val_size else records

    return convert_to_dspy_examples(train_records), convert_to_dspy_examples(val_records)


def _resolve_optimization_budget(
    auto: Literal["light", "medium", "heavy"] | None,
    max_full_evals: int | None,
    max_metric_calls: int | None,
    max_iterations: int | None,
) -> tuple[Literal["light", "medium", "heavy"] | None, int | None, int | None]:
    """
    Resolve optimization budget parameters, converting max_iterations if needed.

    GEPA iterations are genetic algorithm generations, while max_full_evals controls
    the number of full evaluation cycles. When max_iterations is provided, we map it
    to max_full_evals using a 1:1 heuristic as a conservative upper bound.

    Args:
        auto: Auto-tuning mode
        max_full_evals: Maximum full evaluation cycles
        max_metric_calls: Maximum metric evaluation calls
        max_iterations: Maximum GEPA generations (converted to max_full_evals)

    Returns:
        Tuple of (auto, max_full_evals, max_metric_calls) with max_iterations resolved
    """
    if max_iterations is not None and max_iterations > 0:
        if auto is not None and max_full_evals is None and max_metric_calls is None:
            # Convert max_iterations to max_full_evals when using auto mode
            # We use a 1:1 mapping as a conservative heuristic
            estimated_max_evals = max(1, max_iterations)
            logger.info(
                f"Converting max_iterations={max_iterations} to max_full_evals={estimated_max_evals} "
                f"in auto={auto} mode (1:1 heuristic)"
            )
            max_full_evals = estimated_max_evals
            auto = None  # Disable auto mode since we're using explicit limit
        elif max_full_evals is None and max_metric_calls is None:
            # If no budget params set, use max_iterations as max_full_evals
            max_full_evals = max(1, max_iterations)
            logger.info(
                f"Using max_iterations={max_iterations} as max_full_evals={max_full_evals} (1:1 heuristic)"
            )

    return auto, max_full_evals, max_metric_calls


def optimize_with_gepa(
    module: Any,
    trainset: Sequence[dspy.Example],
    valset: Sequence[dspy.Example] | None = None,
    *,
    auto: Literal["light", "medium", "heavy"] | None = None,
    max_full_evals: int | None = None,
    max_metric_calls: int | None = None,
    max_iterations: int | None = None,  # Limit number of GEPA generations/iterations
    reflection_model: str | None = None,
    perfect_score: float = 1.0,
    log_dir: str = ".var/logs/gepa",
    metric: Any | None = None,  # type: ignore[type-arg]
    progress_callback: ProgressCallback | None = None,
    **gepa_kwargs: Any,
) -> Any:
    """
    Compile the DSPy module using dspy.GEPA with routing-aware feedback.

    Follows DSPy best practices:
    - Validates exactly ONE optimization budget parameter is set
    - Ensures module is properly initialized before optimization
    - Uses proper error handling and progress reporting
    - Supports tool optimization when applicable

    Note: Exactly ONE of auto, max_full_evals, or max_metric_calls must be set.
    If none are explicitly set, defaults to auto="light".

    The max_iterations parameter can be used to limit the number of GEPA generations
    when using auto mode. It will be converted to max_full_evals if not already set.

    Args:
        module: DSPy module to optimize (must be a dspy.Module instance)
        trainset: Training examples (must be non-empty)
        valset: Validation examples (optional, recommended for better optimization)
        auto: Auto mode for GEPA ("light", "medium", "heavy"). Mutually exclusive with max_full_evals and max_metric_calls.
        max_full_evals: Maximum full evaluations. Mutually exclusive with auto and max_metric_calls.
        max_metric_calls: Maximum metric calls. Mutually exclusive with auto and max_full_evals.
        max_iterations: Maximum number of GEPA iterations/generations. When using auto mode,
                        this will override the auto mode's internal limits by converting to max_full_evals.
                        Ignored if max_full_evals or max_metric_calls is explicitly set.
        reflection_model: Model for reflection (uses main LM if None)
        perfect_score: Perfect score threshold (default: 1.0)
        log_dir: Directory for GEPA logs
        metric: Custom metric (optional, uses RoutingFeedbackMetric by default)
        progress_callback: Optional callback for progress reporting
        **gepa_kwargs: Additional GEPA options (e.g., enable_tool_optimization, num_threads)

    Returns:
        Compiled DSPy module

    Raises:
        ValueError: If parameter validation fails or module is invalid
    """
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    # Validate module
    if not isinstance(module, dspy.Module):
        error_msg = f"Module must be a dspy.Module instance, got {type(module)}"
        progress_callback.on_error(error_msg)
        raise ValueError(error_msg)

    # Ensure DSPy settings are configured (required for module initialization)
    if (
        not hasattr(dspy, "settings")
        or not hasattr(dspy.settings, "lm")
        or dspy.settings.lm is None
    ):
        error_msg = "DSPy settings must be configured with an LM before optimization. Call dspy.settings.configure(lm=...) first."
        progress_callback.on_error(error_msg)
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Ensure module is fully initialized before optimization
    # This is critical for GEPA to access predictor signatures correctly
    if hasattr(module, "_ensure_modules_initialized"):
        try:
            module._ensure_modules_initialized()
            logger.debug("Module modules initialized before GEPA optimization")
        except Exception as e:
            logger.warning(f"Could not ensure module initialization: {e}, continuing anyway")

    # Validate predictor signatures are accessible (required for GEPA)
    # This ensures GEPA can access pred.signature.instructions for all predictors
    if hasattr(module, "named_predictors"):
        try:
            from agentic_fleet.dspy_modules.reasoner_modules import _get_predictor_signature

            named_preds = list(module.named_predictors())
            predictors_without_signature = []
            for name, pred in named_preds:
                sig = _get_predictor_signature(pred)
                if sig is None:
                    predictors_without_signature.append(name)
                else:
                    # Ensure signature is cached on the predictor for GEPA access
                    if not hasattr(pred, "signature"):
                        pred.signature = sig

            if predictors_without_signature:
                logger.warning(
                    f"Some predictors lack accessible signatures: {predictors_without_signature}. "
                    "GEPA may have issues with reflection for these predictors. "
                    "Optimization will continue but reflection may skip these predictors."
                )
            else:
                logger.debug(
                    f"All {len(named_preds)} predictors have accessible signatures for GEPA"
                )
        except Exception as e:
            logger.warning(
                f"Could not validate predictor signatures: {e}. Continuing with optimization."
            )

    # Validate training data
    # Note: GEPA requires at least some training data to optimize.
    # If trainset is empty, we can't optimize, but we allow it to pass through
    # so the caller can handle bootstrap mode (using history as training data).
    if not trainset:
        logger.warning(
            "No training data provided to GEPA. Optimization will be skipped. "
            "Consider providing initial training data or enabling history harvesting with --use-history."
        )
        # Return original module - can't optimize without training data
        progress_callback.on_complete("Skipped GEPA optimization (no training data)")
        return module

    # Resolve optimization budget, converting max_iterations if provided
    auto, max_full_evals, max_metric_calls = _resolve_optimization_budget(
        auto, max_full_evals, max_metric_calls, max_iterations
    )

    # Validate optimization budget parameters (exactly one must be set)
    budget_params = [auto is not None, max_full_evals is not None, max_metric_calls is not None]
    if sum(budget_params) > 1:
        error_msg = "Exactly one of auto, max_full_evals, or max_metric_calls must be set"
        progress_callback.on_error(error_msg)
        raise ValueError(error_msg)

    # Set default if none provided
    if not any(budget_params):
        auto = "light"
        logger.info("No optimization budget specified, defaulting to auto='light'")

    progress_callback.on_progress(
        f"Setting up GEPA optimizer (train={len(trainset)}, val={len(valset or [])})..."
    )

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"GEPA logs will be written to {log_path.absolute()}")

    # Initialize metric (must implement GEPAFeedbackMetric interface)
    if metric is None:
        metric = RoutingFeedbackMetric(perfect_score=perfect_score)
    elif not callable(metric):
        error_msg = "Metric must be callable (implement GEPAFeedbackMetric interface)"
        progress_callback.on_error(error_msg)
        raise ValueError(error_msg)

    # Get reflection LM (uses main LM if not specified)
    reflection_lm = None
    if reflection_model:
        progress_callback.on_progress(f"Initializing reflection model: {reflection_model}...")
        reflection_lm = get_reflection_lm(reflection_model)
        if reflection_lm is None:
            logger.warning(
                f"Failed to initialize reflection model {reflection_model}, continuing without reflection"
            )
    else:
        # Use current DSPy LM as reflection LM if available
        try:
            current_lm = (
                dspy.settings.lm
                if hasattr(dspy, "settings") and hasattr(dspy.settings, "lm")
                else None
            )
            if current_lm:
                reflection_lm = current_lm
                logger.debug("Using current DSPy LM as reflection LM")
        except Exception:
            logger.debug("Could not access current DSPy LM for reflection")

    # Create GEPA optimizer instance following DSPy best practices
    progress_callback.on_progress("Creating GEPA optimizer instance...")
    try:
        optimizer_kwargs: dict[str, Any] = {
            "metric": cast(GEPAFeedbackMetric, metric),
            "perfect_score": perfect_score,
            "log_dir": str(log_path),
            "track_stats": gepa_kwargs.pop("track_stats", True),
            "warn_on_score_mismatch": gepa_kwargs.pop("warn_on_score_mismatch", True),
        }

        # Set optimization budget (exactly one)
        if auto is not None:
            optimizer_kwargs["auto"] = auto
        elif max_full_evals is not None:
            optimizer_kwargs["max_full_evals"] = max_full_evals
        elif max_metric_calls is not None:
            optimizer_kwargs["max_metric_calls"] = max_metric_calls

        # Reflection settings
        if reflection_lm:
            optimizer_kwargs["reflection_lm"] = reflection_lm
            # Reduce reflection_minibatch_size for faster compilation (default 3 -> 2)
            optimizer_kwargs["reflection_minibatch_size"] = gepa_kwargs.pop(
                "reflection_minibatch_size", 2
            )

        # Merging additional kwargs happens later
        # We only set standard GEPA parameters here

        # Threading for parallel evaluation
        if "num_threads" in gepa_kwargs:
            optimizer_kwargs["num_threads"] = gepa_kwargs.pop("num_threads")

        # Filter out parameters that GEPA doesn't accept
        # The 'optimizer' parameter is used to select between bootstrap/gepa at a higher level
        # but GEPA itself doesn't need it
        gepa_kwargs.pop("optimizer", None)
        gepa_kwargs.pop("harvest_history", None)  # Already handled in dataset preparation
        gepa_kwargs.pop("min_quality", None)  # Used for filtering, not GEPA config
        gepa_kwargs.pop("max_examples", None)  # Used for limiting examples, not GEPA config
        gepa_kwargs.pop("is_self_improvement", None)  # Metadata flag, not GEPA config
        gepa_kwargs.pop("stats_only", None)  # Metadata flag, not GEPA config
        gepa_kwargs.pop("max_iterations", None)  # Already converted to max_full_evals if needed
        # Handle enable_tool_optimization - not currently supported by GEPA
        if "enable_tool_optimization" in gepa_kwargs:
            value = gepa_kwargs.pop("enable_tool_optimization")
            if value:
                logger.warning(
                    "GEPA optimizer does not currently support 'enable_tool_optimization'; "
                    "ignoring provided value %r. If this parameter is now supported in your "
                    "DSPy/GEPA version, update the optimizer integration to pass it through.",
                    value,
                )

        # Merge any remaining kwargs
        optimizer_kwargs.update(gepa_kwargs)

        optimizer = dspy.GEPA(**optimizer_kwargs)  # type: ignore[attr-defined]
    except Exception as exc:
        error_msg = f"Failed to create GEPA optimizer: {exc}"
        progress_callback.on_error(error_msg)
        logger.error(error_msg, exc_info=True)
        raise

    # Run optimization with periodic progress updates
    import threading
    import time

    progress_callback.on_progress(
        f"Starting GEPA optimization (train={len(trainset)}, val={len(valset or [])})..."
    )
    logger.info(
        "Starting GEPA compilation. Note: 'No valid predictions found' warnings during "
        "reflection are expected and don't prevent optimization from completing."
    )

    # Track compilation start time and provide periodic updates
    compilation_start = time.time()
    update_interval = 30.0  # Update every 30 seconds
    is_compiling = threading.Event()
    is_compiling.set()

    def periodic_progress_update():
        """Periodically update progress during long compilation."""
        while is_compiling.is_set():
            time.sleep(update_interval)
            if is_compiling.is_set():
                elapsed = time.time() - compilation_start
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                progress_callback.on_progress(
                    f"GEPA optimization in progress... ({minutes}m {seconds}s elapsed, "
                    f"check {log_path} for detailed logs)"
                )

    progress_thread = threading.Thread(target=periodic_progress_update, daemon=True)
    progress_thread.start()

    # Use context manager to ensure filter is removed even if exception occurs
    warning_filter = MaxWarningFilter(max_count=5, message_pattern="No valid predictions found")
    dspy_logger = logging.getLogger("dspy")

    try:
        with warning_filter_context(dspy_logger, warning_filter):
            # GEPA.compile() accepts module as first positional arg or as 'student' keyword
            # The "No valid predictions found" messages are INFO logs from GEPA's reflection
            # mechanism and are expected when reflection can't find suitable predictions.
            # Optimization continues successfully using other mutation strategies.
            compiled = optimizer.compile(  # type: ignore[attr-defined]
                module,
                trainset=list(trainset),
                valset=list(valset) if valset else None,
            )
    except Exception as exc:
        error_msg = f"GEPA optimization failed: {exc}"
        progress_callback.on_error(error_msg)
        logger.error(error_msg, exc_info=True)
        raise
    finally:
        # Stop periodic updates
        is_compiling.clear()
        # Report final elapsed time
        elapsed = time.time() - compilation_start
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        logger.info(f"GEPA compilation completed in {minutes}m {seconds}s")

    progress_callback.on_complete(
        f"GEPA optimization complete (train={len(trainset)}, val={len(valset or [])})"
    )
    logger.info(
        "GEPA optimization complete (train=%d, val=%d, log_dir=%s)",
        len(trainset),
        len(valset or []),
        log_path,
    )

    # Record optimization run metadata (best effort)
    try:
        record_dspy_optimization_run(
            {
                "optimizerType": "gepa",
                "autoMode": auto,
                "trainExampleCount": len(trainset),
                "valExampleCount": len(valset or []),
                "maxFullEvaluations": max_full_evals,
                "maxMetricCalls": max_metric_calls,
                "reflectionModel": reflection_model,
                "logDir": str(log_path),
                "completedAt": datetime.now(UTC).isoformat(),
            },
            user_id=get_default_user_id(),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Skipping optimization run metadata recording: %s", exc)

    return compiled
