"""Environment variable validation and centralized access utilities.

This module provides centralized access to environment variables with type safety,
validation, and consistent defaults. Use these utilities instead of direct os.getenv
calls throughout the codebase.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..workflows.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# Boolean truthy values recognized by get_env_bool
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def get_env_var(name: str, default: str | None = None, required: bool = False) -> str:
    """
    Get environment variable with optional validation.

    Args:
        name: Environment variable name
        default: Default value if not set
        required: Whether the variable is required

    Returns:
        Environment variable value

    Raises:
        ConfigurationError: If required and not set
    """
    value = os.getenv(name, default)

    if required and (not value or not value.strip()):
        error_msg = f"Required environment variable {name} is not set"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")

    return value or ""


def get_env_bool(name: str, default: bool = False) -> bool:
    """
    Get environment variable as a boolean.

    Recognizes "1", "true", "yes", "on" (case-insensitive) as True.

    Args:
        name: Environment variable name
        default: Default value if not set or empty

    Returns:
        Boolean value
    """
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in _TRUTHY_VALUES


def get_env_int(name: str, default: int = 0) -> int:
    """
    Get environment variable as an integer.

    Args:
        name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value
    """
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {name}: '{value}', using default {default}")
        return default


def get_env_float(name: str, default: float = 0.0) -> float:
    """
    Get environment variable as a float.

    Args:
        name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Float value
    """
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for {name}: '{value}', using default {default}")
        return default


class EnvConfig:
    """Centralized, type-safe access to AgenticFleet environment variables.

    This class provides cached access to commonly used environment variables
    with proper typing and defaults. Use this instead of scattered os.getenv calls.

    Example:
        >>> config = EnvConfig()
        >>> api_key = config.openai_api_key
        >>> if config.use_cosmos:
        ...     endpoint = config.cosmos_endpoint
    """

    def __init__(self) -> None:
        """Initialize the environment config with an empty cache."""
        self._cache: dict[str, Any] = {}

    def _get_cached(self, key: str, loader: Any) -> Any:
        """Get a cached value or compute and cache it.

        Args:
            key: Cache key for the value
            loader: Callable that returns the value if not cached

        Returns:
            The cached or freshly computed value
        """
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    @property
    def openai_api_key(self) -> str:
        """OpenAI API key (OPENAI_API_KEY)."""
        return self._get_cached("openai_api_key", lambda: get_env_var("OPENAI_API_KEY", ""))

    @property
    def openai_base_url(self) -> str | None:
        """OpenAI base URL override (OPENAI_BASE_URL)."""

        def _load() -> str | None:
            value = get_env_var("OPENAI_BASE_URL", "")
            return value if value else None

        return self._get_cached("openai_base_url", _load)

    @property
    def tavily_api_key(self) -> str:
        """Tavily API key for web search (TAVILY_API_KEY)."""
        return self._get_cached("tavily_api_key", lambda: get_env_var("TAVILY_API_KEY", ""))

    @property
    def log_format(self) -> str:
        """Logging format: 'text' or 'json' (LOG_FORMAT)."""
        return self._get_cached("log_format", lambda: get_env_var("LOG_FORMAT", "text").lower())

    @property
    def enable_dspy_agents(self) -> bool:
        """Whether DSPy agents are enabled (ENABLE_DSPY_AGENTS, default: true)."""
        return self._get_cached(
            "enable_dspy_agents", lambda: get_env_bool("ENABLE_DSPY_AGENTS", default=True)
        )

    @property
    def mlflow_dspy_autolog(self) -> bool:
        """Whether MLflow DSPy autologging is enabled (MLFLOW_DSPY_AUTOLOG)."""
        return self._get_cached(
            "mlflow_dspy_autolog", lambda: get_env_bool("MLFLOW_DSPY_AUTOLOG", default=False)
        )

    # --- Cosmos DB Settings ---

    @property
    def use_cosmos(self) -> bool:
        """Whether Cosmos DB integration is enabled (AGENTICFLEET_USE_COSMOS)."""
        return self._get_cached(
            "use_cosmos", lambda: get_env_bool("AGENTICFLEET_USE_COSMOS", default=False)
        )

    @property
    def cosmos_endpoint(self) -> str:
        """Azure Cosmos DB endpoint (AZURE_COSMOS_ENDPOINT)."""
        return self._get_cached("cosmos_endpoint", lambda: get_env_var("AZURE_COSMOS_ENDPOINT", ""))

    @property
    def cosmos_key(self) -> str:
        """Azure Cosmos DB key (AZURE_COSMOS_KEY)."""
        return self._get_cached("cosmos_key", lambda: get_env_var("AZURE_COSMOS_KEY", ""))

    @property
    def cosmos_database(self) -> str:
        """Azure Cosmos DB database name (AZURE_COSMOS_DATABASE)."""
        return self._get_cached(
            "cosmos_database", lambda: get_env_var("AZURE_COSMOS_DATABASE", "agentic-fleet")
        )

    @property
    def cosmos_use_managed_identity(self) -> bool:
        """Whether to use managed identity for Cosmos DB (AZURE_COSMOS_USE_MANAGED_IDENTITY)."""
        return self._get_cached(
            "cosmos_use_managed_identity",
            lambda: get_env_bool("AZURE_COSMOS_USE_MANAGED_IDENTITY", default=False),
        )

    # --- Telemetry Settings ---

    @property
    def otel_exporter_endpoint(self) -> str | None:
        """OpenTelemetry exporter endpoint (OTEL_EXPORTER_OTLP_ENDPOINT)."""

        def _load() -> str | None:
            value = get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT", "")
            return value if value else None

        return self._get_cached("otel_exporter_endpoint", _load)

    # --- Server Settings ---

    @property
    def host(self) -> str:
        """Server host (HOST, default: 0.0.0.0)."""
        return self._get_cached("host", lambda: get_env_var("HOST", "0.0.0.0"))

    @property
    def port(self) -> int:
        """Server port (PORT, default: 8000)."""
        return self._get_cached("port", lambda: get_env_int("PORT", default=8000))

    @property
    def environment(self) -> str:
        """Environment name (ENVIRONMENT, default: development)."""
        return self._get_cached("environment", lambda: get_env_var("ENVIRONMENT", "development"))

    def clear_cache(self) -> None:
        """Clear all cached environment values.

        Call this if environment variables change at runtime.
        """
        self._cache.clear()


# Singleton instance for easy access
env_config = EnvConfig()


def validate_required_env_vars(
    required_vars: list[str], optional_vars: list[str] | None = None
) -> None:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names
        optional_vars: List of optional environment variable names (for informational logging)

    Raises:
        ConfigurationError: If any required environment variable is missing
    """
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or not value.strip():
            missing.append(var)

    if missing:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please set these variables in your environment or .env file."
        )
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")

    # Log optional variables status
    if optional_vars:
        for var in optional_vars:
            value = os.getenv(var)
            if not value or not value.strip():
                logger.debug(f"Optional environment variable {var} is not set")
            else:
                logger.debug(f"Optional environment variable {var} is set")


def validate_agentic_fleet_env() -> None:
    """
    Validate environment variables required for AgenticFleet.

    This function checks for:
    - OPENAI_API_KEY (required)
    - TAVILY_API_KEY (optional, but recommended for Researcher agent)
    - Cosmos DB settings when AGENTICFLEET_USE_COSMOS is enabled
    """
    required = ["OPENAI_API_KEY"]
    optional = ["TAVILY_API_KEY", "OPENAI_BASE_URL", "HOST", "PORT", "ENVIRONMENT"]

    # Base validation (models + optional telemetry / host settings)
    validate_required_env_vars(required, optional)

    # Conditional Cosmos DB validation using EnvConfig
    if env_config.use_cosmos:
        cosmos_required = ["AZURE_COSMOS_ENDPOINT", "AZURE_COSMOS_DATABASE"]

        # When managed identity is disabled (default), require a key for local/dev use.
        if not env_config.cosmos_use_managed_identity:
            cosmos_required.append("AZURE_COSMOS_KEY")

        cosmos_optional = [
            "AZURE_COSMOS_CONSISTENCY_LEVEL",
            "AZURE_COSMOS_MAX_RETRY_ATTEMPTS",
            "AZURE_COSMOS_MAX_RETRY_WAIT_SECONDS",
            "AZURE_COSMOS_AUTO_PROVISION",
            "AZURE_COSMOS_WORKFLOW_RUNS_CONTAINER",
            "AZURE_COSMOS_AGENT_MEMORY_CONTAINER",
            "AZURE_COSMOS_DSPY_EXAMPLES_CONTAINER",
            "AZURE_COSMOS_DSPY_OPTIMIZATION_RUNS_CONTAINER",
            "AZURE_COSMOS_CACHE_CONTAINER",
        ]

        validate_required_env_vars(cosmos_required, cosmos_optional)
        logger.info(
            "Cosmos DB integration enabled for database '%s'",
            env_config.cosmos_database,
        )

    logger.info("Environment variable validation passed")


__all__ = [
    "EnvConfig",
    "env_config",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    "get_env_var",
    "validate_agentic_fleet_env",
    "validate_required_env_vars",
]
