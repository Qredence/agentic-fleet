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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import dspy
from dspy.teleprompt.gepa.gepa import GEPAFeedbackMetric

from agentic_fleet.dspy_modules.lifecycle import get_reflection_lm
from agentic_fleet.utils.progress import NullProgressCallback, ProgressCallback
from agentic_fleet.utils.storage import HistoryManager
from agentic_fleet.utils.storage.cosmos import get_default_user_id, record_dspy_optimization_run

from .feedback import RoutingFeedbackMetric, normalize_agents
from .self_improvement import SelfImprovementEngine

logger = logging.getLogger(__name__)


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
    metric: Any | None = None,  # type: ignore[type-arg]
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
    metric = metric or RoutingFeedbackMetric(perfect_score=perfect_score)  # type: ignore[arg-type]

    # Use centralized DSPy manager for reflection LM (reuses shared instance)
    progress_callback.on_progress("Initializing reflection model...")
    reflection_lm = get_reflection_lm(reflection_model)

    progress_callback.on_progress("Creating GEPA optimizer instance...")
    optimizer = dspy.GEPA(  # type: ignore[attr-defined]
        metric=cast(GEPAFeedbackMetric, metric),
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
