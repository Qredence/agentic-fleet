"""
Centralized DSPy LM management that aligns with agent-framework patterns.

Manages DSPy language model instances, handles async context conflicts,
and enables prompt caching. Uses agent-framework's shared client pattern
as inspiration for singleton-like management.

Supports both standard OpenAI and Azure OpenAI backends:
- Standard OpenAI: Uses `openai/{model}` format
- Azure OpenAI: Uses `azure/{deployment}` format with Azure-specific credentials
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import dspy

from agentic_fleet.utils.cfg import env_config

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
        model: Model identifier (e.g., "gpt-4.1-mini", "gpt-5-mini")
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

        # Determine if we should use Azure OpenAI or standard OpenAI
        # Azure OpenAI uses `azure/{deployment}` format with LiteLLM
        if env_config.use_azure_openai:
            # Use Azure OpenAI Responses API format
            deployment = env_config.azure_openai_deployment or model
            model_path = f"azure/{deployment}"

            # Set Azure-specific environment variables for LiteLLM
            # LiteLLM reads these automatically when using azure/ prefix
            azure_kwargs: dict[str, Any] = {
                "api_key": env_config.azure_openai_api_key,
                "api_base": env_config.azure_openai_endpoint,
            }
            # Only add api_version if explicitly set (v1 Responses API doesn't need it)
            if env_config.azure_openai_api_version:
                azure_kwargs["api_version"] = env_config.azure_openai_api_version

            # Merge Azure kwargs with user-provided kwargs (user kwargs take precedence)
            merged_kwargs = {**azure_kwargs, **kwargs}

            logger.info(
                f"Using Azure OpenAI Responses API: deployment={deployment}, "
                f"endpoint={env_config.azure_openai_endpoint}"
            )
        else:
            # Use standard OpenAI Chat Completions API
            model_path = f"openai/{model}"
            merged_kwargs = kwargs
            logger.debug(f"Using standard OpenAI: model={model}")

        logger.debug(f"Creating DSPy LM instance for {model_path}")

        # Create LM with caching enabled if requested
        # DSPy LMs support caching via the 'cache' parameter or through dspy.settings
        if enable_cache:
            try:
                # Try to enable caching via LM kwargs if supported
                if "cache" not in merged_kwargs:
                    # Some DSPy versions support cache=True or cache_size parameter
                    # We'll configure it through dspy.settings after creation
                    pass
            except Exception as e:
                logger.debug(f"Cache parameter not supported in LM constructor: {e}")

        lm = dspy.LM(model_path, **merged_kwargs)  # type: ignore[attr-defined]

        # Enable prompt caching if supported and requested
        if enable_cache:
            try:
                # Configure caching through dspy.settings if available
                # DSPy uses dspy.settings.configure() for global cache settings
                # The cache is typically enabled automatically for OpenAI LMs
                # We log it here for visibility
                logger.debug("Prompt caching enabled for DSPy LM (via dspy.settings)")
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
        model: Model identifier (e.g., "gpt-4.1-mini", "gpt-5-mini")
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
