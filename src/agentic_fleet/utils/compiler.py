"""
DSPy compilation utilities for optimizing modules.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import inspect
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import dspy

from .gepa_optimizer import (
    convert_to_dspy_examples,
    harvest_history_examples,
    optimize_with_gepa,
    prepare_gepa_datasets,
)
from .progress import NullProgressCallback, ProgressCallback

logger = logging.getLogger(__name__)

# Cache version for invalidation
CACHE_VERSION = 3  # Incremented to include reasoner source hash


def _compute_signature_hash() -> str:
    """
    Compute hash of all DSPy signature classes.

    This ensures cache invalidation when signatures change, following
    DSPy best practices for tracking signature modifications.

    Returns:
        SHA256 hash of signature source code
    """
    try:
        from ..dspy_modules import (
            answer_quality,
            handoff_signatures,  # type: ignore
            signatures,
        )

        # Collect all signature classes
        signature_classes = []

        # Get signatures from signatures.py
        for name, obj in inspect.getmembers(signatures):
            if inspect.isclass(obj) and issubclass(obj, dspy.Signature) and obj != dspy.Signature:
                signature_classes.append((name, inspect.getsource(obj)))

        # Get signatures from handoff_signatures.py
        for name, obj in inspect.getmembers(handoff_signatures):
            if inspect.isclass(obj) and issubclass(obj, dspy.Signature) and obj != dspy.Signature:
                signature_classes.append((name, inspect.getsource(obj)))

        # Get signatures from answer_quality.py
        for name, obj in inspect.getmembers(answer_quality):
            if inspect.isclass(obj) and issubclass(obj, dspy.Signature) and obj != dspy.Signature:
                signature_classes.append((name, inspect.getsource(obj)))

        # Get signatures from nlu_signatures.py
        from ..dspy_modules import nlu_signatures

        for name, obj in inspect.getmembers(nlu_signatures):
            if inspect.isclass(obj) and issubclass(obj, dspy.Signature) and obj != dspy.Signature:
                signature_classes.append((name, inspect.getsource(obj)))

        # Sort for consistent hashing
        signature_classes.sort(key=lambda x: x[0])

        # Compute hash of all signature source code
        combined_source = "\n".join([f"{name}:\n{source}" for name, source in signature_classes])
        return hashlib.sha256(combined_source.encode()).hexdigest()[:16]
    except Exception as e:
        logger.warning(f"Failed to compute signature hash: {e}")
        return "unknown"


def _compute_config_hash(
    dspy_model: str,
    optimizer: str,
    gepa_options: dict[str, Any] | None = None,
    agent_config: dict[str, Any] | None = None,
) -> str:
    """
    Compute hash of configuration that affects compilation.

    Includes DSPy config (model, optimizer settings) and Agent Framework
    agent config (models, tools) since DSPy routing depends on agent capabilities.

    Args:
        dspy_model: DSPy model identifier
        optimizer: Optimization strategy
        gepa_options: GEPA optimizer options
        agent_config: Agent Framework agent configuration

    Returns:
        SHA256 hash of configuration
    """
    try:
        config_data = {
            "dspy_model": dspy_model,
            "optimizer": optimizer,
            "gepa_options": json.dumps(gepa_options or {}, sort_keys=True),
            "agent_config": json.dumps(agent_config or {}, sort_keys=True),
        }

        # Create deterministic JSON string
        config_str = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    except Exception as e:
        logger.warning(f"Failed to compute config hash: {e}")
        return "unknown"


def _get_cache_metadata(cache_path: str) -> dict[str, Any] | None:
    """Get metadata from cache file if it exists.

    Args:
        cache_path: Path to cache file

    Returns:
        Dictionary with cache metadata or None
    """
    metadata_path = cache_path + ".meta"
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path) as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache_metadata(
    cache_path: str,
    examples_path: str,
    version: int = CACHE_VERSION,
    optimizer: str = "bootstrap",
    serializer: str = "pickle",
    signature_hash: str | None = None,
    config_hash: str | None = None,
    reasoner_source_hash: str | None = None,
):
    """Save cache metadata.

    Phase 3: Enhanced with DSPy version tracking for compatibility checks.

    Args:
        cache_path: Path to cache file
        examples_path: Path to examples file used for compilation
        version: Cache version number
        optimizer: Optimization strategy used
        serializer: Serialization method used
        signature_hash: Hash of signature classes (for granular invalidation)
        config_hash: Hash of configuration (for granular invalidation)
        reasoner_source_hash: Hash of reasoner source files
    """
    metadata_path = cache_path + ".meta"

    # Phase 3: Capture DSPy version for compatibility validation
    with contextlib.suppress(Exception):
        dspy_version = getattr(dspy, "__version__", "unknown")

    metadata = {
        "version": version,
        "dspy_version": dspy_version,  # Phase 3: Add DSPy version
        "examples_path": examples_path,
        "examples_mtime": os.path.getmtime(examples_path) if os.path.exists(examples_path) else 0,
        "optimizer": optimizer,
        "serializer": serializer,
        "created_at": datetime.now().isoformat(),
    }

    # Add signature and config hashes for granular invalidation
    if signature_hash:
        metadata["signature_hash"] = signature_hash
    if config_hash:
        metadata["config_hash"] = config_hash
    if reasoner_source_hash:
        metadata["reasoner_source_hash"] = reasoner_source_hash

    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save cache metadata: {e}")


def _is_cache_valid(
    cache_path: str,
    examples_path: str,
    optimizer: str,
    signature_hash: str | None = None,
    config_hash: str | None = None,
    reasoner_source_hash: str | None = None,
) -> bool:
    """Check if cache is valid based on modification times, version, and hashes.

    Args:
        cache_path: Path to cached compiled module
        examples_path: Path to training examples file
        optimizer: Optimization strategy
        signature_hash: Current signature hash (for granular invalidation)
        config_hash: Current config hash (for granular invalidation)

    Returns:
        True if cache exists and is valid, False otherwise
    """
    if not os.path.exists(cache_path) or not os.path.exists(examples_path):
        return False

    # Check cache metadata version (do this first; tests may use tiny placeholder files)
    metadata = _get_cache_metadata(cache_path)
    if metadata:
        if metadata.get("version") != CACHE_VERSION:
            logger.debug(f"Cache version mismatch: {metadata.get('version')} != {CACHE_VERSION}")
            return False
        cached_optimizer = metadata.get("optimizer", "bootstrap")
        if cached_optimizer != optimizer:
            logger.debug("Cache optimizer mismatch: %s != %s", cached_optimizer, optimizer)
            return False
        serializer = metadata.get("serializer", "pickle")
        if serializer == "none":
            logger.debug("Cache marked with serializer 'none' - treating as invalid")
            return False

        recorded_examples_path = metadata.get("examples_path")
        if recorded_examples_path and os.path.abspath(recorded_examples_path) != os.path.abspath(
            examples_path
        ):
            logger.debug(
                "Cache metadata references %s but current workflow expects %s",
                recorded_examples_path,
                examples_path,
            )
            return False

        # Check signature hash if available (granular invalidation)
        if (
            signature_hash
            and "signature_hash" in metadata
            and metadata["signature_hash"] != signature_hash
        ):
            logger.debug("Cache signature hash mismatch: signatures changed, invalidating cache")
            return False

        # Check config hash if available (granular invalidation)
        if config_hash and "config_hash" in metadata and metadata["config_hash"] != config_hash:
            logger.debug("Cache config hash mismatch: configuration changed, invalidating cache")
            return False

        # Check reasoner source hash if available (invalidates when reasoner code changes)
        if (
            reasoner_source_hash
            and "reasoner_source_hash" in metadata
            and metadata["reasoner_source_hash"] != reasoner_source_hash
        ):
            logger.debug("Cache reasoner hash mismatch: code changed, invalidating cache")
            return False

        recorded_examples_mtime = metadata.get("examples_mtime")
        if recorded_examples_mtime is not None:
            try:
                current_examples_mtime = os.path.getmtime(examples_path)
            except OSError:
                return False
            # Allow for minor filesystem precision differences when comparing timestamps
            if current_examples_mtime - recorded_examples_mtime > 1e-6:
                logger.debug(
                    "Examples file modified since cache metadata was written; invalidating"
                )
                return False
        return True

    try:
        cache_mtime = os.path.getmtime(cache_path)
        examples_mtime = os.path.getmtime(examples_path)
        return cache_mtime >= examples_mtime
    except OSError:
        return False


def _validate_example_alignment(records: list[dict[str, Any]]) -> list[str]:
    """
    Validate that training examples match runtime call patterns.

    Checks that examples include required fields that match the forward() method
    signature and runtime usage patterns.

    Args:
        records: List of training example dictionaries

    Returns:
        List of validation warnings (empty if all valid)
    """
    warnings = []
    required_fields = ["task", "assigned_to", "mode"]
    optional_fields = [  # noqa: F841
        "team",
        "team_capabilities",
        "available_tools",
        "context",
        "tool_requirements",
    ]

    for i, record in enumerate(records):
        # Check required fields
        missing_required = [
            field for field in required_fields if field not in record or not record[field]
        ]
        if missing_required:
            warnings.append(f"Example {i}: Missing required fields: {', '.join(missing_required)}")

        # Check that mode is valid
        mode = record.get("mode", record.get("execution_mode", ""))
        if mode and mode not in ["delegated", "sequential", "parallel"]:
            warnings.append(
                f"Example {i}: Invalid execution mode '{mode}' (should be delegated/sequential/parallel)"
            )

        # Check that assigned_to matches team capabilities
        assigned = record.get("assigned_to", "")
        team = record.get("team", record.get("team_capabilities", ""))
        if assigned and team:
            # Basic check: assigned agent should be mentioned in team
            assigned_agents = [a.strip() for a in str(assigned).split(",")]
            for agent in assigned_agents:
                if agent and agent not in team:
                    warnings.append(
                        f"Example {i}: Assigned agent '{agent}' not found in team description"
                    )

    if warnings:
        logger.warning(f"Training example validation found {len(warnings)} issues:")
        for warning in warnings[:10]:  # Limit to first 10 warnings
            logger.warning(f"  - {warning}")
        if len(warnings) > 10:
            logger.warning(f"  ... and {len(warnings) - 10} more issues")

    return warnings


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
    """
    Compile DSPy reasoner module with training examples.

    Args:
        module: DSPy module to compile
        examples_path: Path to training examples JSON
        use_cache: Whether to use cached compiled module if available
        optimizer: Optimization strategy ("bootstrap" or "gepa")
        gepa_options: Additional options when using GEPA optimizer
        dspy_model: DSPy model identifier (for config hash)
        agent_config: Agent Framework agent configuration (for config hash)
        progress_callback: Optional callback for progress reporting
        allow_gepa_optimization: Whether to allow running GEPA optimization if cache is missing

    Returns:
        Compiled DSPy module
    """
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    optimizer = optimizer or "bootstrap"
    cache_path = ".var/logs/compiled_supervisor.pkl"

    progress_callback.on_start(f"Compiling DSPy reasoner with {optimizer} optimizer")

    # Compute hashes for granular cache invalidation
    progress_callback.on_progress("Computing cache hashes...")
    signature_hash = _compute_signature_hash()
    reasoner_source_hash = None
    try:
        from ..dspy_modules.reasoner_utils import get_reasoner_source_hash

        reasoner_source_hash = get_reasoner_source_hash()
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("Failed to compute reasoner source hash: %s", exc)
    config_hash = None
    if dspy_model:
        config_hash = _compute_config_hash(
            dspy_model=dspy_model,
            optimizer=optimizer,
            gepa_options=gepa_options,
            agent_config=agent_config,
        )

    if use_cache:
        progress_callback.on_progress("Checking cache validity...")
        if _is_cache_valid(
            cache_path,
            examples_path,
            optimizer,
            signature_hash=signature_hash,
            config_hash=config_hash,
            reasoner_source_hash=reasoner_source_hash,
        ):
            cached = load_compiled_module(cache_path)
            if cached is not None:
                progress_callback.on_complete(f"Using cached compiled module ({optimizer})")
                logger.info("✓ Using cached compiled module from %s (%s)", cache_path, optimizer)
                return cached
        else:
            if os.path.exists(cache_path):
                progress_callback.on_progress("Cache invalidated, recompiling...")
                logger.info("Cache invalidated for optimizer '%s'; recompiling...", optimizer)
            else:
                progress_callback.on_progress("No cache found, compiling...")
                logger.debug("No cache found for optimizer '%s'; compiling...", optimizer)

    # If GEPA is requested but not allowed (e.g. during normal run), fallback to bootstrap
    if optimizer == "gepa" and not allow_gepa_optimization:
        logger.info("GEPA optimization requested but disabled. Falling back to bootstrap.")
        progress_callback.on_progress("GEPA disabled for this run, falling back to bootstrap...")
        optimizer = "bootstrap"

        # Re-check cache for bootstrap
        if use_cache and _is_cache_valid(
            cache_path,
            examples_path,
            optimizer,
            signature_hash=signature_hash,
            config_hash=config_hash,  # Note: config hash might differ if it includes optimizer
            reasoner_source_hash=reasoner_source_hash,
        ):
            cached = load_compiled_module(cache_path)
            if cached is not None:
                progress_callback.on_complete(f"Using cached compiled module ({optimizer})")
                logger.info("✓ Using cached compiled module from %s (%s)", cache_path, optimizer)
                return cached

    if not os.path.exists(examples_path):
        progress_callback.on_error(f"No training data found at {examples_path}")
        logger.warning(f"No training data found at {examples_path}, using uncompiled module")
        return module

    progress_callback.on_progress(f"Loading training examples from {examples_path}...")
    try:
        with open(examples_path) as f:
            data = json.load(f)
    except Exception as exc:
        progress_callback.on_error("Failed to load training data", exc)
        logger.error(f"Failed to load training data from {examples_path}: {exc}")
        return module

    # Validate example alignment with runtime patterns
    if isinstance(data, list) and data:
        progress_callback.on_progress(f"Validating {len(data)} training examples...")
        validation_warnings = _validate_example_alignment(data)
        if validation_warnings:
            progress_callback.on_progress(f"Found {len(validation_warnings)} validation warnings")
            logger.warning(
                f"Found {len(validation_warnings)} validation issues in training examples. "
                "Some examples may not align with runtime call patterns."
            )

    try:
        if optimizer == "gepa":
            gepa_options = gepa_options or {}
            extra_examples: list[dict[str, Any]] = list(gepa_options.get("extra_examples", []))

            if gepa_options.get("use_history_examples"):
                progress_callback.on_progress("Harvesting history examples...")
                history_examples = harvest_history_examples(
                    min_quality=gepa_options.get("history_min_quality", 8.0),
                    limit=gepa_options.get("history_limit", 200),
                )
                if history_examples:
                    extra_examples.extend(history_examples)
                    progress_callback.on_progress(
                        f"Appended {len(history_examples)} history-derived examples"
                    )
                    logger.info(
                        "Appended %d history-derived examples for GEPA",
                        len(history_examples),
                    )

            progress_callback.on_progress("Preparing GEPA datasets...")
            trainset, valset = prepare_gepa_datasets(
                base_examples_path=examples_path,
                base_records=data,
                extra_examples=extra_examples,
                val_split=gepa_options.get("val_split", 0.2),
                seed=gepa_options.get("seed", 13),
            )

            # Enforce exclusivity at compilation time to avoid silent misconfiguration
            auto_flag = gepa_options.get("auto")
            max_full_flag = gepa_options.get("max_full_evals")
            max_metric_flag = gepa_options.get("max_metric_calls")
            chosen_flags = [c for c in [auto_flag, max_full_flag, max_metric_flag] if c is not None]
            if len(chosen_flags) != 1:
                raise ValueError(
                    "Exactly one of max_metric_calls, max_full_evals, auto must be set. "
                    f"You set max_metric_calls={max_metric_flag}, max_full_evals={max_full_flag}, auto={auto_flag}."
                )

            # Log edge case examples being used for training
            edge_case_count = sum(
                1
                for ex in trainset + (list(valset) if valset else [])
                if hasattr(ex, "context") and "edge case" in str(ex.context).lower()
            )
            if edge_case_count > 0:
                progress_callback.on_progress(f"Found {edge_case_count} edge case examples")
                logger.info(
                    f"GEPA training includes {edge_case_count} edge case examples for better routing"
                )

            progress_callback.on_progress(
                f"Running GEPA optimization ({len(trainset)} train, {len(valset) if valset else 0} val)..."
            )
            compiled = optimize_with_gepa(
                module,
                trainset,
                valset,
                auto=auto_flag,
                max_full_evals=max_full_flag,
                max_metric_calls=max_metric_flag,
                reflection_model=gepa_options.get("reflection_model"),
                perfect_score=gepa_options.get("perfect_score", 1.0),
                log_dir=gepa_options.get("log_dir", ".var/logs/gepa"),
                progress_callback=progress_callback,
            )

            # Log GEPA optimization completion with edge case awareness
            progress_callback.on_complete(
                f"GEPA optimization complete ({len(trainset)} train, {len(valset) if valset else 0} val examples)"
            )
            logger.info(
                f"✓ GEPA optimization complete: {len(trainset)} train, {
                    len(valset) if valset else 0
                } val examples. "
                f"Edge cases captured: {edge_case_count}. Check {
                    gepa_options.get('log_dir', '.var/logs/gepa')
                } for detailed feedback."
            )
        else:
            progress_callback.on_progress("Converting examples to DSPy format...")
            trainset = convert_to_dspy_examples(data)

            def routing_metric(example, prediction, trace=None):
                correct_assignment = example.assigned_to in prediction.assigned_to
                correct_mode = example.execution_mode == prediction.execution_mode
                tool_score = 1.0
                if hasattr(example, "tool_requirements") and example.tool_requirements:
                    tool_score = 1.0
                base_score = float(correct_assignment and correct_mode)
                return base_score * 0.8 + tool_score * 0.2

            from dspy.teleprompt import BootstrapFewShot

            max_demos = gepa_options.get("max_bootstrapped_demos", 4) if gepa_options else 4
            progress_callback.on_progress(
                f"Running BootstrapFewShot optimization ({len(trainset)} examples, max_demos={max_demos})..."
            )
            optimizer_instance = BootstrapFewShot(
                metric=routing_metric,
                max_bootstrapped_demos=max_demos,
                max_labeled_demos=max_demos,
            )

            compiled = optimizer_instance.compile(module, trainset=trainset)
            progress_callback.on_complete(
                f"Bootstrap compilation complete ({len(trainset)} examples)"
            )
            logger.info(f"✓ Module compiled with {len(trainset)} examples (bootstrap)")

        if use_cache:
            progress_callback.on_progress("Saving compiled module to cache...")
            try:
                serializer_used = save_compiled_module(compiled, cache_path)
                _save_cache_metadata(
                    cache_path,
                    examples_path,
                    CACHE_VERSION,
                    optimizer,
                    serializer=serializer_used,
                    signature_hash=signature_hash,
                    config_hash=config_hash,
                    reasoner_source_hash=reasoner_source_hash,
                )
                progress_callback.on_progress("Cache saved successfully")
            except Exception as e:
                # Ensure no partial artifact remains
                try:
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
                        if os.path.exists(cache_path + ".meta"):
                            os.remove(cache_path + ".meta")
                except Exception as cleanup_exc:
                    # Failed to clean up partial cache files; ignoring as this is non-fatal
                    logger.debug(
                        f"Failed to clean up cache files after serialization error: {cleanup_exc}"
                    )
                progress_callback.on_error("Failed to save cache", e)
                logger.warning(
                    "Skipping cache metadata creation due to serialization failure; will compile fresh next run (%s)",
                    e,
                )

        return compiled

    except Exception as e:
        progress_callback.on_error(f"Compilation failed with {optimizer}", e)
        logger.error(f"Failed to compile module with {optimizer}: {e}", exc_info=True)
        return module


def save_compiled_module(module: Any, filepath: str) -> str:
    """Save compiled DSPy module for reuse atomically.

    Writes to a temporary file and renames on success. Returns serializer used.
    Raises if both strategies fail, leaving no artifact behind.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_path = filepath + ".tmp"

    def _attempt_pickle() -> bool:
        try:
            import pickle

            with open(tmp_path, "wb") as f:
                pickle.dump(module, f)
            logger.info(f"Compiled module serialized (pickle) to temp path {tmp_path}")
            return True
        except Exception as e:
            logger.warning(f"Pickle serialization failed: {e}")
            return False

    def _attempt_dill() -> bool:
        try:
            import dill  # type: ignore

            with open(tmp_path, "wb") as f:
                dill.dump(module, f)  # type: ignore
            logger.info(f"Compiled module serialized (dill) to temp path {tmp_path}")
            return True
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed to serialize compiled module with dill: {e}")
            return False

    def _attempt_cloudpickle() -> bool:
        try:
            import cloudpickle  # type: ignore

            with open(tmp_path, "wb") as f:
                cloudpickle.dump(module, f)  # type: ignore
            logger.info(f"Compiled module serialized (cloudpickle) to temp path {tmp_path}")
            return True
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed to serialize compiled module with cloudpickle: {e}")
            return False

    # Remove any stale temp
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except Exception as e:
        # Suppress errors if removing the temp file fails (e.g., permission or locking issues).
        logger.warning(f"Failed to remove existing temp file {tmp_path}: {e}")

    strategies = [
        ("cloudpickle", _attempt_cloudpickle),
        ("pickle", _attempt_pickle),
        ("dill", _attempt_dill),
    ]

    used = "none"
    for name, attempt in strategies:
        if attempt():
            used = name
            break
    if used == "none":
        # Cleanup temp file if present
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            logger.debug(f"Failed to clean up temp file {tmp_path}: {e}")
        raise RuntimeError("Failed to serialize compiled module with cloudpickle, pickle, or dill")

    # Atomic replace
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        os.replace(tmp_path, filepath)
        logger.info(f"Compiled module saved to {filepath} ({used})")
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as cleanup_err:
            logger.debug(f"Failed to clean up temp file {tmp_path}: {cleanup_err}")
        raise RuntimeError(f"Failed to finalize serialization: {e}") from None
    return used


def load_compiled_module(filepath: str) -> Any | None:
    """Load previously compiled DSPy module using recorded serializer."""
    if not os.path.exists(filepath):
        return None
    try:
        if os.path.getsize(filepath) < 64:
            logger.debug("Serialized file too small (<64B); treating as invalid cache")
            return None
    except OSError:
        return None
    serializer = "pickle"
    meta = _get_cache_metadata(filepath)
    if meta:
        serializer = meta.get("serializer", "pickle")

    def _pickle_loader():
        import pickle

        with open(filepath, "rb") as f:
            # Loading internally-generated DSPy compiled modules (trusted source)
            return pickle.load(f)  # nosec B301

    def _dill_loader():
        import dill  # type: ignore

        with open(filepath, "rb") as f:
            # Loading internally-generated DSPy compiled modules (trusted source)
            return dill.load(f)  # type: ignore  # nosec B301

    def _cloudpickle_loader():
        import cloudpickle  # type: ignore

        with open(filepath, "rb") as f:
            # Loading internally-generated DSPy compiled modules (trusted source)
            return cloudpickle.load(f)  # type: ignore  # nosec B301

    strategies: dict[str, Callable[[], Any]] = {
        "pickle": _pickle_loader,
        "dill": _dill_loader,
        "cloudpickle": _cloudpickle_loader,
    }
    order = [serializer] + [s for s in strategies if s != serializer]
    for strat in order:
        try:
            mod = strategies[strat]()
            logger.info(f"Compiled module loaded from {filepath} ({strat})")
            return mod
        except Exception as e:
            logger.warning(f"Failed to load with {strat}: {e}")
            continue
    logger.error("All deserialization strategies failed for %s", filepath)
    return None


def clear_cache(cache_path: str = ".var/logs/compiled_supervisor.pkl"):
    """Clear compiled module cache.

    Args:
        cache_path: Path to cache file to clear
    """
    from .cfg import DEFAULT_ANSWER_QUALITY_CACHE_PATH

    # Clear the specified cache
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
            logger.info(f"Cache file removed: {cache_path}")

        metadata_path = cache_path + ".meta"
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            logger.info(f"Cache metadata removed: {metadata_path}")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")

    # Also clear AnswerQualityModule cache
    aq_cache = DEFAULT_ANSWER_QUALITY_CACHE_PATH
    try:
        if os.path.exists(aq_cache):
            os.remove(aq_cache)
            logger.info(f"AnswerQuality cache file removed: {aq_cache}")

        aq_meta = aq_cache + ".meta"
        if os.path.exists(aq_meta):
            os.remove(aq_meta)
            logger.info(f"AnswerQuality cache metadata removed: {aq_meta}")
    except Exception as e:
        logger.error(f"Failed to clear AnswerQuality cache: {e}")


def get_cache_info(
    cache_path: str = ".var/logs/compiled_supervisor.pkl",
) -> dict[str, Any] | None:
    """Get information about cached module.

    Args:
        cache_path: Path to cache file

    Returns:
        Dictionary with cache information or None
    """
    if not os.path.exists(cache_path):
        return None

    metadata = _get_cache_metadata(cache_path)
    cache_mtime = os.path.getmtime(cache_path)
    cache_size = os.path.getsize(cache_path)

    info = {
        "cache_path": cache_path,
        "cache_size_bytes": cache_size,
        "cache_mtime": datetime.fromtimestamp(cache_mtime).isoformat(),
    }

    if metadata:
        info.update(metadata)

    return info


# --- Async Compilation Utilities ---


class AsyncCompiler:
    """Manages async compilation of DSPy modules.

    This class provides background compilation capabilities to avoid
    blocking workflow initialization. It wraps the synchronous compile_reasoner
    function and runs it in a thread pool executor.

    Example:
        compiler = AsyncCompiler()
        await compiler.compile_in_background(module)
        # ... do other work ...
        compiled = await compiler.wait_for_compilation(timeout=60)
    """

    def __init__(self) -> None:
        """Initialize async compiler."""
        self._compilation_task: asyncio.Future[Any] | None = None
        self._compiled_module: Any | None = None
        self._compilation_error: Exception | None = None
        self._store_result_task: asyncio.Task[Any] | None = None

    async def compile_in_background(
        self,
        module: Any,
        examples_path: str = "src/agentic_fleet/data/supervisor_examples.json",
        use_cache: bool = True,
        optimizer: str = "bootstrap",
        gepa_options: dict[str, Any] | None = None,
        dspy_model: str | None = None,
        agent_config: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Start compilation in background.

        Args:
            module: DSPy module to compile
            examples_path: Path to training examples
            use_cache: Whether to use cache
            optimizer: Optimization strategy
            gepa_options: GEPA optimizer options
            dspy_model: DSPy model identifier
            agent_config: Agent configuration
            progress_callback: Progress callback
        """
        if self._compilation_task and not self._compilation_task.done():
            logger.warning("Compilation already in progress")
            return

        self._compiled_module = None
        self._compilation_error = None

        def _compile() -> Any:
            """Run compilation in thread pool."""
            try:
                return compile_reasoner(
                    module=module,
                    examples_path=examples_path,
                    use_cache=use_cache,
                    optimizer=optimizer,
                    gepa_options=gepa_options,
                    dspy_model=dspy_model,
                    agent_config=agent_config,
                    progress_callback=progress_callback or NullProgressCallback(),
                )
            except Exception as e:
                logger.error(f"Background compilation failed: {e}")
                raise

        loop = asyncio.get_event_loop()
        self._compilation_task = loop.run_in_executor(None, _compile)

        # Store result when done
        async def _store_result() -> None:
            try:
                if self._compilation_task is not None:
                    self._compiled_module = await self._compilation_task
                    logger.info("Background compilation completed successfully")
            except Exception as e:
                self._compilation_error = e
                logger.error(f"Background compilation error: {e}")

        self._store_result_task = asyncio.create_task(_store_result())

    async def wait_for_compilation(self, timeout: float | None = None) -> Any:
        """Wait for compilation to complete.

        Args:
            timeout: Maximum time to wait (None for no timeout)

        Returns:
            Compiled module

        Raises:
            TimeoutError: If compilation doesn't complete in time
            Exception: If compilation failed
        """
        if not self._compilation_task:
            raise RuntimeError("No compilation task started")

        try:
            if timeout:
                self._compiled_module = await asyncio.wait_for(
                    self._compilation_task, timeout=timeout
                )
            else:
                self._compiled_module = await self._compilation_task

            if self._compilation_error:
                raise self._compilation_error

            return self._compiled_module
        except TimeoutError as err:
            raise TimeoutError(f"Compilation did not complete within {timeout}s") from err

    def get_compiled_module(self) -> Any | None:
        """Get compiled module if available.

        Returns:
            Compiled module or None if not ready
        """
        return self._compiled_module

    def is_compiling(self) -> bool:
        """Check if compilation is in progress.

        Returns:
            True if compilation is active
        """
        return self._compilation_task is not None and not self._compilation_task.done()

    def is_ready(self) -> bool:
        """Check if compilation is complete and ready.

        Returns:
            True if compiled module is available
        """
        return self._compiled_module is not None and self._compilation_error is None


def compile_answer_quality(
    use_cache: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile AnswerQualityModule for offline use.

    This function compiles the AnswerQualityModule using BootstrapFewShot
    with quality scoring examples. The compiled module is cached to
    DEFAULT_ANSWER_QUALITY_CACHE_PATH.

    Args:
        use_cache: Whether to use cached module if available
        progress_callback: Optional progress callback

    Returns:
        Compiled AnswerQualityModule
    """
    from .cfg import DEFAULT_ANSWER_QUALITY_CACHE_PATH

    if progress_callback is None:
        progress_callback = NullProgressCallback()

    cache_path = DEFAULT_ANSWER_QUALITY_CACHE_PATH
    progress_callback.on_start("Compiling AnswerQualityModule")

    # Check cache
    if use_cache and os.path.exists(cache_path):
        try:
            cached = load_compiled_module(cache_path)
            if cached is not None:
                progress_callback.on_complete("Using cached AnswerQualityModule")
                logger.info("✓ Using cached AnswerQualityModule from %s", cache_path)
                return cached
        except Exception as e:
            logger.warning("Failed to load cached AnswerQualityModule: %s", e)

    # Import module
    try:
        from ..dspy_modules.answer_quality import get_uncompiled_module

        module = get_uncompiled_module()
        if module is None:
            progress_callback.on_error("DSPy not available for AnswerQualityModule", None)
            logger.warning("DSPy not available, cannot compile AnswerQualityModule")
            return None
    except Exception as e:
        progress_callback.on_error("Failed to import AnswerQualityModule", e)
        logger.error("Failed to import AnswerQualityModule: %s", e)
        return None

    # Create synthetic training examples for quality scoring
    # These examples demonstrate the expected scoring behavior
    progress_callback.on_progress("Creating training examples...")
    training_examples = [
        dspy.Example(
            question="What is the capital of France?",
            answer="Paris is the capital of France. It is located in north-central France.",
            groundness="0.95",
            relevance="1.0",
            coherence="0.9",
        ).with_inputs("question", "answer"),
        dspy.Example(
            question="Explain quantum computing",
            answer="Quantum computing uses quantum mechanics principles like superposition and entanglement to process information. Unlike classical bits, qubits can exist in multiple states simultaneously.",
            groundness="0.9",
            relevance="0.95",
            coherence="0.85",
        ).with_inputs("question", "answer"),
        dspy.Example(
            question="How do I bake a cake?",
            answer="I don't know how to help with that.",
            groundness="0.1",
            relevance="0.1",
            coherence="0.5",
        ).with_inputs("question", "answer"),
        dspy.Example(
            question="What is Python used for?",
            answer="Python is a versatile programming language used for web development, data science, machine learning, automation, and scripting. Its readable syntax makes it popular for beginners.",
            groundness="0.85",
            relevance="0.9",
            coherence="0.9",
        ).with_inputs("question", "answer"),
        dspy.Example(
            question="Summarize the meeting notes",
            answer="",
            groundness="0.0",
            relevance="0.0",
            coherence="0.0",
        ).with_inputs("question", "answer"),
    ]

    def quality_metric(example, prediction, trace=None):
        """Metric for answer quality scoring accuracy."""
        try:
            # Compare predicted scores to expected scores
            pred_g = float(prediction.groundness)
            pred_r = float(prediction.relevance)
            pred_c = float(prediction.coherence)

            exp_g = float(example.groundness)
            exp_r = float(example.relevance)
            exp_c = float(example.coherence)

            # Score based on how close predictions are to expected values
            g_score = 1.0 - min(abs(pred_g - exp_g), 1.0)
            r_score = 1.0 - min(abs(pred_r - exp_r), 1.0)
            c_score = 1.0 - min(abs(pred_c - exp_c), 1.0)

            return (g_score + r_score + c_score) / 3
        except Exception:
            return 0.0

    progress_callback.on_progress("Running BootstrapFewShot optimization...")
    try:
        from dspy.teleprompt import BootstrapFewShot

        optimizer = BootstrapFewShot(
            metric=quality_metric,
            max_bootstrapped_demos=3,
            max_labeled_demos=3,
        )
        compiled = optimizer.compile(module, trainset=training_examples)
        progress_callback.on_complete("AnswerQualityModule compilation complete")
        logger.info("✓ AnswerQualityModule compiled with %d examples", len(training_examples))
    except Exception as e:
        progress_callback.on_error("Compilation failed", e)
        logger.error("Failed to compile AnswerQualityModule: %s", e)
        return module

    # Save to cache
    if use_cache:
        progress_callback.on_progress("Saving to cache...")
        try:
            serializer_used = save_compiled_module(compiled, cache_path)
            _save_cache_metadata(
                cache_path,
                examples_path="synthetic",
                version=CACHE_VERSION,
                optimizer="bootstrap",
                serializer=serializer_used,
            )
            logger.info("AnswerQualityModule cached to %s", cache_path)
        except Exception as e:
            logger.warning("Failed to cache AnswerQualityModule: %s", e)

    return compiled


def compile_nlu(
    use_cache: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile DSPyNLU module for offline use.

    Args:
        use_cache: Whether to use cached module if available
        progress_callback: Optional progress callback

    Returns:
        Compiled DSPyNLU module
    """
    from .cfg import DEFAULT_NLU_CACHE_PATH

    if progress_callback is None:
        progress_callback = NullProgressCallback()

    cache_path = DEFAULT_NLU_CACHE_PATH
    progress_callback.on_start("Compiling DSPyNLU")

    # Check cache
    if use_cache and os.path.exists(cache_path):
        try:
            cached = load_compiled_module(cache_path)
            if cached is not None:
                progress_callback.on_complete("Using cached DSPyNLU")
                logger.info("✓ Using cached DSPyNLU from %s", cache_path)
                return cached
        except Exception as e:
            logger.warning("Failed to load cached DSPyNLU: %s", e)

    # Import module
    try:
        from ..dspy_modules.nlu import DSPyNLU

        module = DSPyNLU()
        # Ensure predictors are initialized
        module._ensure_modules_initialized()
    except Exception as e:
        progress_callback.on_error("Failed to import DSPyNLU", e)
        logger.error("Failed to import DSPyNLU: %s", e)
        return None

    # Synthetic training examples
    progress_callback.on_progress("Creating training examples for NLU...")

    # Intent Classification examples
    ic_examples = [
        dspy.Example(
            text="I need to book a flight to London.",
            possible_intents="book_flight, cancel_flight, check_status",
            intent="book_flight",
            confidence=0.95,
        ).with_inputs("text", "possible_intents"),
        dspy.Example(
            text="What is the weather like today?",
            possible_intents="get_weather, set_alarm, play_music",
            intent="get_weather",
            confidence=0.98,
        ).with_inputs("text", "possible_intents"),
    ]

    # Entity Extraction examples
    ee_examples = [
        dspy.Example(
            text="Meeting with John at 5 PM in Room A.",
            entity_types="Person, Time, Location",
            entities=[
                {"text": "John", "type": "Person", "confidence": "0.9"},
                {"text": "5 PM", "type": "Time", "confidence": "0.95"},
                {"text": "Room A", "type": "Location", "confidence": "0.8"},
            ],
        ).with_inputs("text", "entity_types"),
    ]

    from dspy.teleprompt import BootstrapFewShot

    # 1. Compile Intent Classifier
    def ic_metric(example, prediction, trace=None):
        return float(example.intent == prediction.intent)

    try:
        progress_callback.on_progress("Compiling Intent Classifier...")
        ic_optimizer = BootstrapFewShot(
            metric=ic_metric, max_bootstrapped_demos=2, max_labeled_demos=2
        )
        compiled_ic = ic_optimizer.compile(module.intent_classifier, trainset=ic_examples)
        module.intent_classifier = compiled_ic
    except Exception as e:
        logger.warning(f"Failed to compile Intent Classifier: {e}")

    # 2. Compile Entity Extractor
    def ee_metric(example, prediction, trace=None):
        # Simple overlap metric
        pred_texts = {e["text"] for e in prediction.entities}
        exp_texts = {e["text"] for e in example.entities}
        if not exp_texts:
            return 1.0 if not pred_texts else 0.0
        return len(pred_texts & exp_texts) / len(exp_texts)

    try:
        progress_callback.on_progress("Compiling Entity Extractor...")
        ee_optimizer = BootstrapFewShot(
            metric=ee_metric, max_bootstrapped_demos=1, max_labeled_demos=1
        )
        compiled_ee = ee_optimizer.compile(module.entity_extractor, trainset=ee_examples)
        module.entity_extractor = compiled_ee
    except Exception as e:
        logger.warning(f"Failed to compile Entity Extractor: {e}")

    progress_callback.on_complete("DSPyNLU compilation complete")
    logger.info("✓ DSPyNLU compiled")

    # Save to cache
    if use_cache:
        progress_callback.on_progress("Saving to cache...")
        try:
            serializer_used = save_compiled_module(module, cache_path)
            _save_cache_metadata(
                cache_path,
                examples_path="synthetic",
                version=CACHE_VERSION,
                optimizer="bootstrap-multi",
                serializer=serializer_used,
            )
            logger.info("DSPyNLU cached to %s", cache_path)
        except Exception as e:
            logger.warning("Failed to cache DSPyNLU: %s", e)

    return module
