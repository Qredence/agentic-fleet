"""
DSPy compilation utilities for optimizing modules.
Simplified to rely on native DSPy persistence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dspy.teleprompt import BootstrapFewShot

from agentic_fleet.dspy_modules.gepa.optimizer import (
    convert_to_dspy_examples,
    harvest_history_examples,
    optimize_with_gepa,
    prepare_gepa_datasets,
)

from .progress import NullProgressCallback, ProgressCallback

logger = logging.getLogger(__name__)


def compile_reasoner(
    module: Any,
    examples_path: str = "src/agentic_fleet/data/supervisor_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    gepa_options: dict[str, Any] | None = None,
    dspy_model: str | None = None,
    agent_config: dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
    allow_gepa_optimization: bool = True,
) -> Any:
    """Compile DSPy reasoner module."""
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    optimizer = optimizer or "bootstrap"
    cache_path = ".var/cache/dspy/compiled_reasoner.json"

    progress_callback.on_start(f"Compiling DSPy reasoner with {optimizer} optimizer")

    if use_cache and os.path.exists(cache_path):
        try:
            progress_callback.on_progress(f"Loading cached module from {cache_path}...")
            module.load(cache_path)
            progress_callback.on_complete(f"Using cached compiled module ({optimizer})")
            logger.info(f"✓ Using cached compiled module from {cache_path}")
            return module
        except Exception as exc:
            logger.warning(f"Failed to load cache, recompiling: {exc}")
            # Note: on_complete was already called in try block if load succeeded,
            # so we don't call on_error here - we'll continue with compilation below

    # Load initial training data (if available)
    data: list[dict[str, Any]] = []
    if os.path.exists(examples_path):
        progress_callback.on_progress(f"Loading training examples from {examples_path}...")
        try:
            with open(examples_path) as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning(f"Training data at {examples_path} is not a list, ignoring")
                data = []
        except Exception as exc:
            logger.warning(f"Failed to load training data from {examples_path}: {exc}")
            data = []
    else:
        logger.info(
            f"No initial training data at {examples_path}. "
            "Will use history data if available (bootstrap mode)."
        )

    if optimizer == "gepa" and allow_gepa_optimization:
        gepa_options = gepa_options or {}
        extra_examples: list[dict[str, Any]] = list(gepa_options.get("extra_examples", []))

        # Harvest history examples if requested OR if no initial training data (bootstrap mode)
        # Self-improvement mode automatically enables history harvesting
        use_history = gepa_options.get("use_history_examples", False) or gepa_options.get(
            "is_self_improvement", False
        )
        bootstrap_mode = not data  # No initial training data

        if use_history or bootstrap_mode:
            progress_callback.on_progress("Harvesting high-quality history examples...")
            history_examples = harvest_history_examples(
                min_quality=gepa_options.get("history_min_quality", 8.0),
                limit=gepa_options.get("history_limit", 200),
            )
            if history_examples:
                extra_examples.extend(history_examples)
                progress_callback.on_progress(
                    f"Harvested {len(history_examples)} history examples "
                    f"({'bootstrap mode' if bootstrap_mode else 'augmentation mode'})"
                )
            else:
                if bootstrap_mode:
                    progress_callback.on_progress(
                        "No high-quality history examples found. "
                        "GEPA will use zero-shot mode (no optimization)."
                    )
                else:
                    progress_callback.on_progress("No high-quality history examples found")

        # Prepare datasets with proper validation
        progress_callback.on_progress("Preparing GEPA datasets...")
        trainset, valset = prepare_gepa_datasets(
            base_examples_path=examples_path,
            base_records=data if data else [],
            extra_examples=extra_examples if extra_examples else None,
            val_split=gepa_options.get("val_split", 0.2),
            seed=gepa_options.get("seed", 13),
        )

        # Bootstrap mode: if no initial data but history exists, use history as training data
        if not trainset:
            if extra_examples:
                logger.info(
                    f"Bootstrap mode: Using {len(extra_examples)} history examples as training data"
                )
                # Convert history examples directly to training set
                # Split into train/val if we have enough examples
                if len(extra_examples) > 4:
                    val_split = gepa_options.get("val_split", 0.2)
                    val_size = max(1, int(len(extra_examples) * val_split))
                    val_examples = extra_examples[:val_size]
                    train_examples = extra_examples[val_size:]
                    trainset = convert_to_dspy_examples(train_examples)
                    valset = convert_to_dspy_examples(val_examples)
                else:
                    # Too few examples - use all for training
                    trainset = convert_to_dspy_examples(extra_examples)
                    valset = []
                progress_callback.on_progress(
                    f"Bootstrap mode: {len(trainset)} training, {len(valset)} validation examples"
                )
            else:
                error_msg = (
                    "No training examples available. "
                    "Either provide initial training data or enable history harvesting with --use-history. "
                    "GEPA requires at least some training examples to optimize."
                )
                progress_callback.on_error(error_msg)
                logger.error(error_msg)
                return module

        # Check for stats_only mode (used for self-improvement preview)
        if gepa_options.get("stats_only", False):
            progress_callback.on_complete(
                f"Self-improvement preview complete: {len(trainset)} potential training examples "
                "identified from high-quality history."
            )
            return module

        # Validate optimization budget parameters
        auto = gepa_options.get("auto")
        max_full_evals = gepa_options.get("max_full_evals")
        max_metric_calls = gepa_options.get("max_metric_calls")
        max_iterations = gepa_options.get("max_iterations")

        # Run GEPA optimization with improved error handling
        progress_callback.on_progress("Running GEPA optimization...")
        try:
            compiled = optimize_with_gepa(
                module,
                trainset,
                valset if valset else None,
                auto=auto,
                max_full_evals=max_full_evals,
                max_metric_calls=max_metric_calls,
                max_iterations=max_iterations,
                reflection_model=gepa_options.get("reflection_model"),
                perfect_score=gepa_options.get("perfect_score", 1.0),
                log_dir=gepa_options.get("log_dir", ".var/logs/gepa"),
                progress_callback=progress_callback,
                enable_tool_optimization=gepa_options.get("enable_tool_optimization", False),
                num_threads=gepa_options.get("num_threads"),
            )
            progress_callback.on_complete("GEPA optimization complete")
        except ValueError as ve:
            # Parameter validation errors
            progress_callback.on_error(f"GEPA parameter error: {ve}")
            logger.error(f"GEPA optimization failed due to parameter error: {ve}")
            return module
        except Exception as exc:
            # Other optimization errors
            progress_callback.on_error(f"GEPA optimization failed: {exc}")
            logger.error(f"GEPA optimization failed: {exc}", exc_info=True)
            return module

    else:
        # Bootstrap Fallback
        progress_callback.on_progress("Running Bootstrap optimization...")
        trainset = convert_to_dspy_examples(data)

        def routing_metric(example, prediction, trace=None):
            pred_agents = getattr(prediction, "assigned_to", "")
            if isinstance(pred_agents, str):
                pred_agents = [x.strip() for x in pred_agents.split(",")]
            gold_agents = getattr(example, "assigned_to", "")
            if isinstance(gold_agents, str):
                gold_agents = [x.strip() for x in gold_agents.split(",")]

            intersection = len(set(pred_agents) & set(gold_agents))
            union = len(set(pred_agents) | set(gold_agents))
            agent_score = intersection / union if union else 0.0

            mode_match = getattr(prediction, "execution_mode", "") == getattr(
                example, "execution_mode", ""
            )
            return (agent_score * 0.7) + (float(mode_match) * 0.3)

        max_demos = 4
        optimizer_instance = BootstrapFewShot(
            metric=routing_metric,
            max_bootstrapped_demos=max_demos,
            max_labeled_demos=max_demos,
        )
        compiled = optimizer_instance.compile(module, trainset=trainset)
        progress_callback.on_complete("Bootstrap optimization complete")

    if use_cache:
        progress_callback.on_progress(f"Saving to {cache_path}...")
        try:
            compiled.save(cache_path)
            logger.info("✓ Saved compiled module")
        except Exception as exc:
            logger.warning(f"Failed to save module: {exc}")

    return compiled


def compile_answer_quality(
    module: Any = None,
    examples_path: str = "src/agentic_fleet/data/quality_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile quality assessment module (Simplified stub)."""
    if module is None:
        logger.warning("No module provided for answer quality compilation; skipping.")
        if progress_callback:
            progress_callback.on_error("No module provided for answer quality compilation")
        return None
    if progress_callback:
        progress_callback.on_start("Compiling Answer Quality Module")
        progress_callback.on_complete("Skipping detailed compilation for simplified mode")
    return module


def compile_nlu(
    module: Any = None,
    examples_path: str = "src/agentic_fleet/data/nlu_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile NLU module (Simplified stub)."""
    if module is None:
        logger.warning("No module provided for NLU compilation; skipping.")
        if progress_callback:
            progress_callback.on_error("No module provided for NLU compilation")
        return None
    if progress_callback:
        progress_callback.on_start("Compiling NLU Module")
        progress_callback.on_complete("Skipping detailed compilation for simplified mode")
    return module


def clear_cache() -> None:
    """Clear compiled module cache (Helper for API).

    .. deprecated::
        This function is deprecated and now a no-op. With the migration to DSPy native
        saving/loading, cache management should be done through manual file operations
        or by using DSPy's built-in cache clearing mechanisms. Consider removing calls
        to this function and managing compiled artifacts directly via the file system.
    """
    # Since we now rely on dspy native saving/loading or manual file management,
    # this acts as a no-op. For cache clearing, delete files in .var/cache/dspy/
    # or .var/logs/ directories as needed.
    pass


def get_cache_info() -> dict[str, Any]:
    """Get cache statistics (Helper for API)."""
    return {"enabled": True, "size": 0, "items": 0, "location": "native_dspy_cache"}


def load_compiled_module(path: str, module_type: str | None = None) -> Any | None:
    """Load a compiled DSPy module from a JSON path.

    This function loads a module using an explicit module_type when provided,
    falling back to a filename-based heuristic if needed.
    """
    if not os.path.exists(path):
        logger.warning(f"Compiled artifact not found at {path}")
        return None

    filename = os.path.basename(path).lower()

    if module_type is None:
        if "tool_planning" in filename:
            module_type = "tool_planning"
        elif "answer_quality" in filename or "quality" in filename:
            module_type = "answer_quality"
        elif "routing" in filename:
            module_type = "routing"
        elif "reasoner" in filename:
            module_type = "reasoner"
        elif "nlu" in filename:
            module_type = "nlu"

    module_factories: dict[str, Any] = {
        "routing": lambda: __import__(
            "agentic_fleet.dspy_modules.decisions.routing",
            fromlist=["RoutingDecisionModule"],
        ).RoutingDecisionModule(),
        "tool_planning": lambda: __import__(
            "agentic_fleet.dspy_modules.decisions.tool_planning",
            fromlist=["ToolPlanningModule"],
        ).ToolPlanningModule(),
        "answer_quality": lambda: __import__(
            "agentic_fleet.dspy_modules.answer_quality",
            fromlist=["AnswerQualityModule"],
        ).AnswerQualityModule(),
        "reasoner": lambda: __import__(
            "agentic_fleet.dspy_modules.reasoner",
            fromlist=["DSPyReasoner"],
        ).DSPyReasoner(),
        "nlu": lambda: __import__(
            "agentic_fleet.dspy_modules.nlu",
            fromlist=["DSPyNLU"],
        ).DSPyNLU(),
    }

    try:
        if not module_type or module_type not in module_factories:
            logger.error(
                "Unknown module type for path: %s (module_type=%s)",
                path,
                module_type,
            )
            return None

        module = module_factories[module_type]()

        # Use DSPy's native load method - handles both JSON and pickle formats
        try:
            if path.endswith(".pkl"):
                module.load(path, allow_pickle=True)
            else:
                module.load(path)
            return module
        except (TypeError, ValueError, AttributeError) as load_error:
            # Corrupted or incompatible cache file - log and clean up
            logger.warning(
                f"Failed to load compiled module from {path}: {load_error}. "
                "The cache file may be corrupted or incompatible. Removing it."
            )
            try:
                os.remove(path)
                logger.debug(f"Removed corrupted cache file: {path}")
            except OSError as remove_error:
                logger.debug(f"Could not remove corrupted cache file {path}: {remove_error}")
            return None

    except Exception as e:
        logger.error(f"Failed to load compiled module from {path}: {e}", exc_info=True)
        return None
