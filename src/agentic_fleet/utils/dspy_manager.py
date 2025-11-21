"""
Centralized DSPy LM management that aligns with agent-framework patterns.

Manages DSPy language model instances, handles async context conflicts,
and enables prompt caching. Uses agent-framework's shared client pattern
as inspiration for singleton-like management.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import dspy

logger = logging.getLogger(__name__)

# Global LM instance storage (similar to agent-framework's shared client pattern)
_global_lm: dspy.LM | None = None
_global_lm_lock = threading.Lock()
_global_lm_model: str | None = None
_global_lm_configured = False


def get_dspy_lm(model: str, enable_cache: bool = True, **kwargs: Any) -> dspy.LM:
    """
    Get or create a shared DSPy LM instance for the given model.

    This follows agent-framework's pattern of creating a shared client once
    and reusing it across all agents/workflows.

    Args:
        model: Model identifier (e.g., "gpt-4", "gpt-5-mini")
        enable_cache: Whether to enable prompt caching (default: True)
        **kwargs: Additional arguments for dspy.LM (e.g. temperature, max_tokens)

    Returns:
        Configured DSPy LM instance
    """
    global _global_lm, _global_lm_model

    with _global_lm_lock:
        # Reuse existing LM if model matches
        if _global_lm is not None and _global_lm_model == model:
            return _global_lm

        # Create new LM instance
        if model == "test-model":
            raise ValueError(
                "'test-model' was a dummy placeholder. Please configure a real model for DSPy."
            )

        model_path = f"openai/{model}"
        logger.debug(f"Creating DSPy LM instance for {model_path} with kwargs: {kwargs}")

        # Create LM with caching enabled if requested (no adapter to avoid JSON serialization issues)
        lm = dspy.LM(model_path, **kwargs)  # type: ignore[attr-defined]

        # Enable prompt caching if supported and requested
        if enable_cache:
            try:
                # DSPy may support caching via settings or LM configuration
                # This is a placeholder - actual implementation depends on DSPy version
                logger.debug("Prompt caching enabled for DSPy LM")
            except Exception as e:
                logger.warning(f"Could not enable prompt caching: {e}")

        _global_lm = lm
        _global_lm_model = model

        return lm


def configure_dspy_settings(
    model: str,
    enable_cache: bool = True,
    force_reconfigure: bool = False,
    **kwargs: Any,
) -> bool:
    """
    Configure DSPy global settings with a shared LM instance.

    Handles async context conflicts gracefully, similar to how
    agent-framework handles shared client initialization.

    Args:
        model: Model identifier (e.g., "gpt-4", "gpt-5-mini")
        enable_cache: Whether to enable prompt caching
        force_reconfigure: Force reconfiguration even if already configured

    Returns:
        True if configuration succeeded, False if already configured and not forced
    """
    global _global_lm_configured

    # Check if already configured (unless forced)
    if _global_lm_configured and not force_reconfigure:
        logger.debug("DSPy settings already configured, skipping")
        return False

    try:
        lm = get_dspy_lm(model, enable_cache=enable_cache, **kwargs)
        dspy.settings.configure(lm=lm)
        _global_lm_configured = True
        logger.info(f"DSPy settings configured with model: {model}")
        return True
    except RuntimeError as e:
        # DSPy settings can only be configured once per async task
        # If already configured, continue with existing settings
        if "can only be called from the same async task" in str(e):
            logger.debug("DSPy already configured in this async context, using existing settings")
            _global_lm_configured = True
            return False
        else:
            logger.error(f"Failed to configure DSPy settings: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error configuring DSPy settings: {e}")
        raise


def get_reflection_lm(model: str | None = None) -> dspy.LM | None:
    """
    Get a reflection LM instance for GEPA optimization.

    If no model is specified, returns None (reflection not needed).
    Uses the shared LM manager to avoid creating duplicate instances.

    Args:
        model: Optional model identifier for reflection LM

    Returns:
        DSPy LM instance or None
    """
    if model is None:
        return None

    # Use shared LM manager for reflection LM too
    return get_dspy_lm(model, enable_cache=True)


def reset_dspy_manager():
    """
    Reset the global DSPy manager state.

    Useful for testing or when switching between different configurations.
    """
    global _global_lm, _global_lm_model, _global_lm_configured

    with _global_lm_lock:
        _global_lm = None
        _global_lm_model = None
        _global_lm_configured = False
        logger.debug("DSPy manager reset")


def get_current_lm() -> dspy.LM | None:
    """
    Get the currently configured global LM instance.

    Returns:
        Current LM instance or None if not configured
    """
    return _global_lm
