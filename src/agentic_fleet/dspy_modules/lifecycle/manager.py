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
import os
import threading
from typing import Any

import dspy

from agentic_fleet.utils.cfg import env_config

logger = logging.getLogger(__name__)

# Langfuse integration for tracing
try:
    from langfuse import get_client
    from openinference.instrumentation.dspy import DSPyInstrumentor

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False


class DSPyManager:
    """
    Singleton manager for DSPy configuration and LM instances.
    Ensures thread-safe initialization and consistent global state.
    """

    _instance: DSPyManager | None = None
    _lock = threading.RLock()

    def __new__(cls) -> DSPyManager:
        """Create a new instance of DSPyManager if it doesn't exist."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return
            self._lm: dspy.LM | None = None
            self._model_name: str | None = None
            self._configured = False
            self._langfuse_initialized = False
            self._dspy_instrumented = False
            self._initialized = True

    def initialize_langfuse(self) -> None:
        """Initialize Langfuse tracing if credentials are available."""
        if not _LANGFUSE_AVAILABLE:
            logger.debug("Langfuse packages not installed - tracing disabled")
            return

        with self._lock:
            if self._langfuse_initialized:
                return

            try:
                public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
                secret_key = os.getenv("LANGFUSE_SECRET_KEY")

                if not public_key or not secret_key:
                    logger.debug("Langfuse credentials not found - tracing disabled")
                    return

                # Initialize Langfuse SDK client
                langfuse_client = get_client()
                if not langfuse_client.auth_check():
                    logger.warning("Langfuse authentication failed - tracing disabled")
                    return

                logger.info("Langfuse client initialized successfully")
                self._langfuse_initialized = True

                # Instrument DSPy
                if not self._dspy_instrumented:
                    self._setup_opentelemetry()
                    DSPyInstrumentor().instrument()
                    self._dspy_instrumented = True
                    logger.info("DSPy instrumentation enabled for Langfuse tracing")

            except Exception as e:
                logger.debug(f"Langfuse initialization skipped: {e}")

    def _setup_opentelemetry(self) -> None:
        """Configure OpenTelemetry environment variables for Langfuse."""
        os.environ.setdefault("OTEL_SERVICE_NAME", "agentic-fleet-dspy")
        os.environ.setdefault("OTEL_RESOURCE_ATTRIBUTES", "framework=dspy,component=dspy-reasoner")

        base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
        otlp_endpoint = f"{base_url}/api/public/otel"
        os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otlp_endpoint)

        logger.info(f"OpenTelemetry environment configured for Langfuse: endpoint={otlp_endpoint}")

    def get_lm(self, model: str, enable_cache: bool = True, **kwargs: Any) -> dspy.LM:
        """Get or create the shared DSPy LM instance."""
        with self._lock:
            # Return existing if model matches
            if self._lm is not None and self._model_name == model:
                return self._lm

            if model == "test-model":
                raise ValueError(
                    "'test-model' was a dummy placeholder. Please configure a real model."
                )

            lm = self._create_lm_instance(model, enable_cache, **kwargs)

            self._lm = lm
            self._model_name = model
            return lm

    def _create_lm_instance(self, model: str, enable_cache: bool, **kwargs: Any) -> dspy.LM:
        """Internal method to create a new LM instance."""
        if env_config.use_azure_openai:
            return self._create_azure_lm(model, **kwargs)
        elif "/" in model:
            return self._create_provider_lm(model, **kwargs)
        else:
            return self._create_openai_lm(model, **kwargs)

    def _create_azure_lm(self, model: str, **kwargs: Any) -> dspy.LM:
        deployment = env_config.azure_openai_deployment or model
        model_path = f"azure/{deployment}"

        azure_kwargs = {
            "api_key": env_config.azure_openai_api_key,
            "api_base": env_config.azure_openai_endpoint,
        }
        if env_config.azure_openai_api_version:
            azure_kwargs["api_version"] = env_config.azure_openai_api_version

        merged_kwargs = {**azure_kwargs, **kwargs}
        logger.info(f"Using Azure OpenAI: deployment={deployment}")
        return dspy.LM(model_path, **merged_kwargs)  # type: ignore

    def _create_provider_lm(self, model: str, **kwargs: Any) -> dspy.LM:
        logger.debug(f"Using provider-prefixed model: {model}")
        return dspy.LM(model, **kwargs)  # type: ignore

    def _create_openai_lm(self, model: str, **kwargs: Any) -> dspy.LM:
        model_path = f"openai/{model}"
        logger.debug(f"Using standard OpenAI: model={model}")
        return dspy.LM(model_path, **kwargs)  # type: ignore

    def configure(
        self,
        model: str,
        enable_cache: bool = True,
        force_reconfigure: bool = False,
        **kwargs: Any,
    ) -> bool:
        """Configure global DSPy settings."""
        with self._lock:
            if self._configured and not force_reconfigure:
                logger.debug("DSPy settings already configured, skipping")
                return False

            self.initialize_langfuse()

            try:
                lm = self.get_lm(model, enable_cache, **kwargs)
                dspy.settings.configure(lm=lm)
                self._configured = True
                logger.info(f"DSPy settings configured with model: {model}")
                return True
            except RuntimeError as e:
                if "can only be called from the same async task" in str(e):
                    logger.debug("DSPy already configured in this async context")
                    self._configured = True
                    return False
                raise
            except Exception as e:
                logger.error(f"Unexpected error configuring DSPy settings: {e}")
                raise

    def reset(self) -> None:
        """Reset manager state."""
        with self._lock:
            self._lm = None
            self._model_name = None
            self._configured = False
            self._langfuse_initialized = False
            self._dspy_instrumented = False
            logger.debug("DSPy manager reset")

    @property
    def current_lm(self) -> dspy.LM | None:
        """Get the current LM instance."""
        return self._lm


# Public API wrappers
def initialize_langfuse() -> None:
    """Initialize Langfuse tracing."""
    DSPyManager().initialize_langfuse()


def get_dspy_lm(model: str, enable_cache: bool = True, **kwargs: Any) -> dspy.LM:
    """Get a DSPy LM instance."""
    return DSPyManager().get_lm(model, enable_cache, **kwargs)


def configure_dspy_settings(
    model: str,
    enable_cache: bool = True,
    force_reconfigure: bool = False,
    **kwargs: Any,
) -> bool:
    """Configure global DSPy settings."""
    return DSPyManager().configure(model, enable_cache, force_reconfigure, **kwargs)


def get_reflection_lm(model: str | None = None) -> dspy.LM | None:
    """Get a reflection LM instance."""
    if model is None:
        return None
    return DSPyManager().get_lm(model, enable_cache=True)


def reset_dspy_manager() -> None:
    """Reset the DSPy manager."""
    DSPyManager().reset()


def get_current_lm() -> dspy.LM | None:
    """Get the current LM instance."""
    return DSPyManager().current_lm
