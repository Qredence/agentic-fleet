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

    # Handle max_iterations: convert to max_full_evals to limit GEPA generations
    # GEPA iterations are genetic algorithm generations, not full evaluation cycles.
    # To limit iterations, we need to set a much lower max_full_evals since each
    # full eval cycle can contain multiple iterations.
    if max_iterations is not None and max_iterations > 0:
        if auto is not None and max_full_evals is None and max_metric_calls is None:
            # Convert max_iterations to max_full_evals to limit iterations in auto mode
            # GEPA typically does 1-2 iterations per full eval cycle, so we use a 1:1 ratio
            # to be conservative and ensure we don't exceed the iteration limit
            estimated_max_evals = max(1, max_iterations)
            logger.info(
                f"Converting max_iterations={max_iterations} to max_full_evals={estimated_max_evals} "
                f"to limit iterations in auto={auto} mode (1:1 ratio for conservative limit)"
            )
            max_full_evals = estimated_max_evals
            auto = None  # Disable auto mode since we're using explicit limit
        elif max_full_evals is None and max_metric_calls is None:
            # If no budget params set, use max_iterations directly as max_full_evals
            max_full_evals = max(1, max_iterations)
            logger.info(
                f"Using max_iterations={max_iterations} as max_full_evals={max_full_evals} (1:1 ratio)"
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
        gepa_kwargs.pop("enable_tool_optimization", None)  # Not supported by GEPA __init__

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

    # Add filter to limit "No valid predictions found" warnings to max 5
    warning_filter = MaxWarningFilter(max_count=5, message_pattern="No valid predictions found")
    # Apply to dspy logger (where GEPA logs come from)
    dspy_logger = logging.getLogger("dspy")
    dspy_logger.addFilter(warning_filter)

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

    try:
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
        # Remove the filter after optimization completes
        dspy_logger.removeFilter(warning_filter)
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
