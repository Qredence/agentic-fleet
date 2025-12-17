"""
Utilities for integrating dspy.GEPA with the agent framework.

Provides helper functions for:
  • Loading/splitting routing examples into DSPy datasets
  • Building feedback-rich metrics for GEPA optimization
  • Running the GEPA optimizer with sensible defaults
  • Harvesting additional training examples from execution history
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import dspy
from dspy.teleprompt.gepa.gepa import GEPAFeedbackMetric
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

from ..dspy_modules.lifecycle import get_reflection_lm
from .cosmos import get_default_user_id, record_dspy_optimization_run
from .history_manager import HistoryManager
from .progress import NullProgressCallback, ProgressCallback
from .self_improvement import SelfImprovementEngine

logger = logging.getLogger(__name__)

# Scoring weights for GEPA routing decision metric
# The weights below must sum to 1.0 (100% of the score).
# If you change these, ensure the sum remains 1.0.
ASSIGNMENT_WEIGHT = 0.5
MODE_WEIGHT = 0.3
TOOL_WEIGHT = 0.1
LATENCY_WEIGHT = 0.1

# Validate that weights sum to 1.0 (allowing for floating point error)
if abs(ASSIGNMENT_WEIGHT + MODE_WEIGHT + TOOL_WEIGHT + LATENCY_WEIGHT - 1.0) >= 1e-8:
    raise ValueError(
        "GEPA scoring weights must sum to 1.0. "
        f"Current sum: {ASSIGNMENT_WEIGHT + MODE_WEIGHT + TOOL_WEIGHT + LATENCY_WEIGHT}"
    )


@dataclass
class RoutingDecision:
    """Represents routing decisions for comparison and analysis."""

    agents: list[str]
    mode: str
    tools: list[str]
    latency_budget: str = "medium"


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
        normalized_agents = sorted(_normalize_agents(assigned_to))
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


def _normalize_agents(value: Any) -> list[str]:
    """
    Normalize agent identifiers into a list of non-empty, stripped strings.

    Args:
        value: Agent(s) to normalize. Can be:
            - A comma-separated string of agent names.
            - An iterable (list, tuple, set) of agent names.
            - A single value (e.g., string, number) representing one agent.

    Returns:
        List of normalized (stripped) non-empty agent names as strings.
    """
    if not value:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [str(value)]
    return [part.strip() for part in parts if part and str(part).strip()]


def _normalize_mode(value: Any) -> str:
    """
    Normalize the execution mode value.

    Converts the input value to a lowercased, stripped string. If the input is falsy (None, empty, etc.),
    returns an empty string. This normalization ensures consistent handling of execution mode strings for downstream logic.

    Args:
        value: Any input representing execution mode (expected to be convertible to str).

    Returns:
        A lowercased, stripped string representation of the mode, or an empty string if input is falsy.
    """
    if not value:
        return ""
    return str(value).strip().lower()


def _normalize_tools(value: Any) -> list[str]:
    """
    Normalize a value representing tool names into a list of lowercased, stripped strings.

    Accepts:
        - A string (tool names separated by commas, newlines, or both).
        - An iterable (list, tuple, set) of tool names.

    Strategy:
        - If given a string, splits on newlines and commas.
        - Lowercases and strips whitespace from each tool name.
        - Filters out empty or blank entries.

    Args:
        value: Tool names as a string or iterable.

    Returns:
        List of normalized tool names (lowercased, stripped).
    """
    if not value:
        return []
    parts = value.replace("\n", ",").split(",") if isinstance(value, str) else list(value)
    return [part.strip().lower() for part in parts if part and str(part).strip()]


def _jaccard_similarity(expected: list[str], predicted: list[str]) -> float:
    if not expected and not predicted:
        return 1.0
    if not expected or not predicted:
        return 0.0
    exp_set = {item.lower() for item in expected}
    pred_set = {item.lower() for item in predicted}
    intersection = len(exp_set & pred_set)
    union = len(exp_set | pred_set)
    return intersection / union if union else 0.0


def _detect_edge_cases(
    task: str,
    expected: RoutingDecision,
    predicted: RoutingDecision,
) -> list[str]:
    """Detect edge cases in routing decisions."""
    edge_cases = []
    task_lower = task.lower()

    # Detect ambiguous tasks
    ambiguous_keywords = ["maybe", "possibly", "could", "might", "perhaps", "either", "or"]
    if any(kw in task_lower for kw in ambiguous_keywords):
        edge_cases.append(
            "This task involves ambiguity - consider clarifying requirements before routing."
        )

    # Detect tool conflicts
    if expected.tools and predicted.tools:
        missing_tools = set(expected.tools) - set(predicted.tools)
        extra_tools = set(predicted.tools) - set(expected.tools)
        if missing_tools and extra_tools:
            edge_cases.append(
                f"Tool conflict detected: missing {missing_tools} but included {extra_tools}."
            )

    # Detect mode edge cases
    if expected.mode != predicted.mode:
        if expected.mode == "parallel" and predicted.mode == "sequential":
            edge_cases.append(
                "Edge case: Tasks requiring parallel execution were routed sequentially. Parallel mode is needed when subtasks are independent."
            )
        elif expected.mode == "sequential" and predicted.mode == "parallel":
            edge_cases.append(
                "Edge case: Tasks requiring sequential execution were routed in parallel. Sequential mode is needed when subtasks have dependencies."
            )

    # Detect agent mismatch patterns
    if expected.agents != predicted.agents:
        if len(expected.agents) > len(predicted.agents):
            edge_cases.append(
                "Edge case: Task requires multiple agents but was assigned to fewer. Consider task complexity and required capabilities."
            )
        elif len(expected.agents) < len(predicted.agents):
            edge_cases.append(
                "Edge case: Task was over-assigned. Consider if a single agent can handle this task."
            )

    # Detect time-sensitive queries
    time_keywords = ["latest", "current", "recent", "today", "now", "2025", "2026", "future"]
    if any(kw in task_lower for kw in time_keywords) and "tavilysearchtool" not in [
        t.lower() for t in predicted.tools
    ]:
        edge_cases.append(
            "Edge case: Time-sensitive query detected but web search tool not assigned. Tasks about current events, latest data, or future dates require TavilySearchTool."
        )

    return edge_cases


def _get_clarifying_examples(
    task: str,
    expected_agents: list[str],
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
        if "research" in task_lower or "find" in task_lower or "search" in task_lower:
            examples.append(
                "For research tasks, assign to Researcher agent. Example: 'Research AI trends' → Researcher"
            )
        if "analyze" in task_lower or "calculate" in task_lower or "data" in task_lower:
            examples.append(
                "For analysis tasks, assign to Analyst agent. Example: 'Analyze sales data' → Analyst"
            )
        if "write" in task_lower or "create" in task_lower or "draft" in task_lower:
            examples.append(
                "For writing tasks, assign to Writer agent. Example: 'Write a blog post' → Writer"
            )
        if "review" in task_lower or "check" in task_lower or "validate" in task_lower:
            examples.append(
                "For review tasks, assign to Reviewer agent. Example: 'Review this document' → Reviewer"
            )

    # Mode selection examples
    if mode_score < 1.0:
        if expected_mode == "parallel":
            examples.append(
                "Use parallel mode when subtasks are independent. Example: 'Research X, analyze Y, write Z' → parallel (all can run simultaneously)"
            )
        elif expected_mode == "sequential":
            examples.append(
                "Use sequential mode when subtasks have dependencies. Example: 'Research X, then analyze results, then write report' → sequential (each depends on previous)"
            )
        elif expected_mode == "delegated":
            examples.append(
                "Use delegated mode for simple, single-agent tasks. Example: 'What is the capital of France?' → delegated (one agent, one answer)"
            )

    # Tool selection examples
    if tool_score < 1.0:
        if "tavilysearchtool" in [t.lower() for t in expected_tools]:
            examples.append(
                "Tasks requiring current information need TavilySearchTool. Example: 'What is today's weather?' → requires TavilySearchTool"
            )
        if "hostedcodeinterpretertool" in [t.lower() for t in expected_tools]:
            examples.append(
                "Tasks requiring calculations or data processing need HostedCodeInterpreterTool. Example: 'Calculate the average of these numbers' → requires HostedCodeInterpreterTool"
            )

    return examples


def build_routing_feedback_metric(perfect_score: float = 1.0) -> GEPAFeedbackMetric:  # type: ignore[type-arg]
    """
    Create a GEPA metric that scores routing quality and emits actionable feedback.

    Enhanced with edge-case detection, clarifying examples, and step-by-step guidance
    following DSPy tutorial patterns for iterative prompt learning.
    """

    def metric(
        gold: Any, pred: Any, trace=None, pred_name=None, pred_trace=None
    ) -> ScoreWithFeedback:
        # Extract task for edge-case detection
        task = getattr(gold, "task", getattr(pred, "task", ""))  # type: ignore[attr-defined]

        expected_agents = _normalize_agents(getattr(gold, "assigned_to", ""))  # type: ignore[attr-defined]
        predicted_agents = _normalize_agents(getattr(pred, "assigned_to", ""))  # type: ignore[attr-defined]

        assignment_score = _jaccard_similarity(expected_agents, predicted_agents)

        expected_mode = _normalize_mode(getattr(gold, "execution_mode", getattr(gold, "mode", "")))  # type: ignore[attr-defined]
        predicted_mode = _normalize_mode(getattr(pred, "execution_mode", getattr(pred, "mode", "")))  # type: ignore[attr-defined]
        mode_score = 1.0 if expected_mode and expected_mode == predicted_mode else 0.0

        expected_tools = _normalize_tools(getattr(gold, "tool_requirements", []))  # type: ignore[attr-defined]
        predicted_tools = _normalize_tools(getattr(pred, "tool_requirements", []))  # type: ignore[attr-defined]
        tool_score = (
            len(set(expected_tools) & set(predicted_tools)) / len(set(expected_tools))
            if expected_tools
            else 1.0
        )

        # Latency check
        expected_latency = getattr(gold, "latency_budget", "medium")
        predicted_latency = getattr(pred, "latency_budget", "medium")
        latency_score = 1.0 if expected_latency == predicted_latency else 0.0

        weighted_score = (
            (assignment_score * ASSIGNMENT_WEIGHT)
            + (mode_score * MODE_WEIGHT)
            + (tool_score * TOOL_WEIGHT)
            + (latency_score * LATENCY_WEIGHT)
        )
        final_score = max(0.0, min(perfect_score, weighted_score * perfect_score))

        # Build comprehensive feedback following DSPy tutorial patterns
        feedback_parts = []

        # Step 1: Overall assessment
        if final_score >= 0.9:
            feedback_parts.append("✅ Routing decision is correct.")
        elif final_score >= 0.7:
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
        edge_cases = _detect_edge_cases(task, expected_decision, predicted_decision)
        if edge_cases:
            feedback_parts.append("\n🔍 Edge Cases Detected:")
            for edge_case in edge_cases:
                feedback_parts.append(f"  • {edge_case}")

        # Step 3: Detailed component analysis
        feedback_parts.append("\n📊 Component Analysis:")

        # Agent assignment feedback
        if assignment_score == 1.0:
            feedback_parts.append("  ✅ Agent selection matches ground truth.")
        else:
            feedback_parts.append(
                "  ❌ Agent mismatch: Assigned "
                f"{predicted_agents or ['none']} but expected "
                f"{expected_agents or ['none']}."
            )
            # Provide step-by-step guidance
            if expected_agents:
                feedback_parts.append(
                    "  📝 Step-by-step: First, analyze task requirements. Then, match capabilities:"
                )
                for agent in expected_agents:
                    feedback_parts.append(f"    - {agent} is needed for this task")

        # Mode selection feedback
        if mode_score == 1.0:
            feedback_parts.append(
                f"  ✅ Execution mode '{expected_mode or 'unspecified'}' is correct."
            )
        else:
            feedback_parts.append(
                f"  ❌ Mode mismatch: Used '{predicted_mode or 'delegated'}' but should use '{
                    expected_mode or 'delegated'
                }'."
            )
            # Provide decision criteria
            if expected_mode == "parallel":
                feedback_parts.append(
                    "  📝 Decision criteria: Use parallel mode when subtasks are independent and can run simultaneously."
                )
            elif expected_mode == "sequential":
                feedback_parts.append(
                    "  📝 Decision criteria: Use sequential mode when subtasks have dependencies (output of one feeds into next)."
                )
            elif expected_mode == "delegated":
                feedback_parts.append(
                    "  📝 Decision criteria: Use delegated mode for simple, single-agent tasks that don't need coordination."
                )

        # Tool selection feedback
        if expected_tools:
            if tool_score == 1.0:
                feedback_parts.append("  ✅ Tool selection matches requirements.")
            else:
                missing = sorted(set(expected_tools) - set(predicted_tools))
                extra = sorted(set(predicted_tools) - set(expected_tools))
                if missing:
                    feedback_parts.append(f"  ❌ Missing required tools: {', '.join(missing)}.")
                if extra:
                    feedback_parts.append(f"  ⚠️ Unnecessary tools assigned: {', '.join(extra)}.")
                # Provide tool selection guidance
                feedback_parts.append("  📝 Tool selection process:")
                feedback_parts.append(
                    "    1. Analyze task for information needs (current data → TavilySearchTool)"
                )
                feedback_parts.append(
                    "    2. Check for computation needs (calculations → HostedCodeInterpreterTool)"
                )
                feedback_parts.append("    3. Match tools to assigned agents' capabilities")
        else:
            if predicted_tools:
                feedback_parts.append("  ⚠️ Tools assigned but none required for this task.")
            else:
                feedback_parts.append("  ✅ No tools required (correct).")

        # Latency feedback
        if latency_score == 1.0:
            feedback_parts.append(f"  ✅ Latency budget '{expected_latency}' is correct.")
        else:
            feedback_parts.append(
                f"  ❌ Latency budget mismatch: Used '{predicted_latency}' but expected '{expected_latency}'."
            )

        # Step 4: Clarifying examples for similar tasks
        if final_score < 0.9:
            examples = _get_clarifying_examples(
                task,
                expected_agents,
                expected_mode,
                expected_tools,
                assignment_score,
                mode_score,
                tool_score,
            )
            if examples:
                feedback_parts.append("\n💡 Clarifying Examples for Similar Tasks:")
                for example in examples:
                    feedback_parts.append(f"  • {example}")

        # Step 5: Task-specific patterns
        task_lower = task.lower()
        if final_score < 0.9:
            feedback_parts.append("\n🎯 Task-Specific Patterns:")
            if any(kw in task_lower for kw in ["research", "find", "search", "latest", "current"]):
                feedback_parts.append(
                    "  • Research tasks typically require: Researcher agent + TavilySearchTool + delegated/sequential mode"
                )
            if any(kw in task_lower for kw in ["analyze", "calculate", "data", "compute"]):
                feedback_parts.append(
                    "  • Analysis tasks typically require: Analyst agent + HostedCodeInterpreterTool + delegated/sequential mode"
                )
            if any(kw in task_lower for kw in ["write", "create", "draft", "compose"]):
                feedback_parts.append(
                    "  • Writing tasks typically require: Writer agent + (no tools) + delegated mode"
                )
            if any(kw in task_lower for kw in ["review", "check", "validate", "verify"]):
                feedback_parts.append(
                    "  • Review tasks typically require: Reviewer agent + (no tools) + delegated mode"
                )
            if any(kw in task_lower for kw in ["and", "also", "then", "multiple"]):
                feedback_parts.append(
                    "  • Multi-step tasks typically require: Multiple agents + sequential/parallel mode"
                )

        # Combine all feedback parts
        feedback = "\n".join(feedback_parts)
        if not feedback.strip():
            feedback = "No actionable feedback available."

        return ScoreWithFeedback(score=final_score, feedback=feedback)

    return metric  # type: ignore[return-value]


def optimize_with_gepa(
    module: Any,
    trainset: Sequence[dspy.Example],
    valset: Sequence[dspy.Example] | None = None,
    *,
    auto: Literal["light", "medium", "heavy"] | None = "light",
    max_full_evals: int | None = 50,
    max_metric_calls: int | None = 150,
    reflection_model: str | None = None,
    perfect_score: float = 1.0,
    log_dir: str = ".var/logs/gepa",
    metric: GEPAFeedbackMetric | None = None,  # type: ignore[type-arg]
    progress_callback: ProgressCallback | None = None,
    **gepa_kwargs: Any,
) -> Any:
    """
    Compile the DSPy module using dspy.GEPA with routing-aware feedback.

    Args:
        module: DSPy module to optimize
        trainset: Training examples
        valset: Validation examples (optional)
        auto: Auto mode for GEPA ("light", "medium", "heavy")
        max_full_evals: Maximum full evaluations
        max_metric_calls: Maximum metric calls
        reflection_model: Model for reflection
        perfect_score: Perfect score threshold
        log_dir: Directory for logs
        metric: Custom metric (optional)
        progress_callback: Optional callback for progress reporting
        **gepa_kwargs: Additional GEPA options

    Returns:
        Compiled DSPy module
    """
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    if not trainset:
        progress_callback.on_error("No training data supplied for GEPA")
        logger.warning("No training data supplied for GEPA; returning original module.")
        return module

    progress_callback.on_progress(
        f"Setting up GEPA optimizer (train={len(trainset)}, val={len(valset or [])})..."
    )
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    metric = metric or build_routing_feedback_metric(perfect_score=perfect_score)

    # Use centralized DSPy manager for reflection LM (reuses shared instance)
    progress_callback.on_progress("Initializing reflection model...")
    reflection_lm = get_reflection_lm(reflection_model)

    progress_callback.on_progress("Creating GEPA optimizer instance...")
    optimizer = dspy.GEPA(  # type: ignore[attr-defined]
        metric=metric,
        auto=auto,
        max_full_evals=max_full_evals,
        max_metric_calls=max_metric_calls,
        reflection_minibatch_size=gepa_kwargs.pop("reflection_minibatch_size", 3),
        reflection_lm=reflection_lm,
        perfect_score=perfect_score,
        log_dir=log_dir,
        track_stats=gepa_kwargs.pop("track_stats", True),
        warn_on_score_mismatch=gepa_kwargs.pop("warn_on_score_mismatch", True),
        **gepa_kwargs,
    )

    progress_callback.on_progress(
        f"Running GEPA optimization (this may take a while, check {log_dir} for details)..."
    )
    compiled = optimizer.compile(  # type: ignore[attr-defined]
        module,
        trainset=list(trainset),
        valset=list(valset) if valset else None,
    )

    progress_callback.on_complete(
        f"GEPA optimization complete (train={len(trainset)}, val={len(valset or [])})"
    )
    logger.info(
        "GEPA optimization complete (train=%d, val=%d, log_dir=%s)",
        len(trainset),
        len(valset or []),
        log_dir,
    )

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
                "logDir": log_dir,
                "completedAt": datetime.now(UTC).isoformat(),
            },
            user_id=get_default_user_id(),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Skipping optimization run mirror: %s", exc)

    return compiled
