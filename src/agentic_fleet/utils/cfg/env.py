"""Environment variable utilities for AgenticFleet.

This module provides:
- Type-safe environment variable access functions
- EnvConfig class for centralized, cached env var access
- Validation utilities for required/optional env vars
"""

# ruff: noqa: D102

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Helper Constants
# =============================================================================
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


# =============================================================================
# Basic Environment Functions
# =============================================================================


def get_env_var(name: str, default: str | None = None, required: bool = False) -> str:
    """Get environment variable with optional validation.

    Args:
        name: Environment variable name
        default: Default value if not set
        required: If True, raises ConfigurationError when not set

    Returns:
        The environment variable value or default

    Raises:
        ConfigurationError: If required=True and variable is not set
    """
    from ...workflows.exceptions import ConfigurationError

    value = os.getenv(name, default)
    if required and (not value or not value.strip()):
        error_msg = f"Required environment variable {name} is not set"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")
    return value or ""


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get environment variable as boolean.

    Truthy values: "1", "true", "yes", "on" (case-insensitive)

    Args:
        name: Environment variable name
        default: Default value if not set

    Returns:
        Boolean interpretation of the environment variable
    """
    value = os.getenv(name, "").strip().lower()
    return value in _TRUTHY_VALUES if value else default


def get_env_int(name: str, default: int = 0) -> int:
    """Get environment variable as integer.

    Args:
        name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value or default if parsing fails
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
    """Get environment variable as float.

    Args:
        name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Float value or default if parsing fails
    """
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for {name}: '{value}', using default {default}")
        return default


# =============================================================================
# EnvConfig Class
# =============================================================================


class EnvConfig:
    """Centralized, type-safe access to AgenticFleet environment variables.

    Property accessors expose individual env vars with caching. Each property
    name corresponds to its environment variable counterpart (snake_case).
    Docstrings are intentionally omitted on trivial getters.

    Example:
        >>> config = EnvConfig()
        >>> config.openai_api_key  # Returns OPENAI_API_KEY
        >>> config.use_cosmos  # Returns AGENTICFLEET_USE_COSMOS as bool
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def _get_cached(self, key: str, loader: Any) -> Any:
        """Get a cached value, computing it if not present."""
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    # -------------------------------------------------------------------------
    # OpenAI Configuration
    # -------------------------------------------------------------------------

    @property
    def openai_api_key(self) -> str:
        return self._get_cached("openai_api_key", lambda: get_env_var("OPENAI_API_KEY", ""))

    @property
    def openai_base_url(self) -> str | None:
        def _load() -> str | None:
            value = get_env_var("OPENAI_BASE_URL", "")
            return value if value else None

        return self._get_cached("openai_base_url", _load)

    # -------------------------------------------------------------------------
    # External Service Keys
    # -------------------------------------------------------------------------

    @property
    def tavily_api_key(self) -> str:
        return self._get_cached("tavily_api_key", lambda: get_env_var("TAVILY_API_KEY", ""))

    # -------------------------------------------------------------------------
    # Logging Configuration
    # -------------------------------------------------------------------------

    @property
    def log_format(self) -> str:
        return self._get_cached("log_format", lambda: get_env_var("LOG_FORMAT", "text").lower())

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------

    @property
    def enable_dspy_agents(self) -> bool:
        return self._get_cached(
            "enable_dspy_agents", lambda: get_env_bool("ENABLE_DSPY_AGENTS", default=True)
        )

    @property
    def mlflow_dspy_autolog(self) -> bool:
        return self._get_cached(
            "mlflow_dspy_autolog", lambda: get_env_bool("MLFLOW_DSPY_AUTOLOG", default=False)
        )

    # -------------------------------------------------------------------------
    # Cosmos DB Configuration
    # -------------------------------------------------------------------------

    @property
    def use_cosmos(self) -> bool:
        return self._get_cached(
            "use_cosmos", lambda: get_env_bool("AGENTICFLEET_USE_COSMOS", default=False)
        )

    @property
    def cosmos_endpoint(self) -> str:
        return self._get_cached("cosmos_endpoint", lambda: get_env_var("AZURE_COSMOS_ENDPOINT", ""))

    @property
    def cosmos_key(self) -> str:
        return self._get_cached("cosmos_key", lambda: get_env_var("AZURE_COSMOS_KEY", ""))

    @property
    def cosmos_database(self) -> str:
        return self._get_cached(
            "cosmos_database", lambda: get_env_var("AZURE_COSMOS_DATABASE", "agentic-fleet")
        )

    @property
    def cosmos_use_managed_identity(self) -> bool:
        return self._get_cached(
            "cosmos_use_managed_identity",
            lambda: get_env_bool("AZURE_COSMOS_USE_MANAGED_IDENTITY", default=False),
        )

    # -------------------------------------------------------------------------
    # Azure OpenAI Configuration
    # -------------------------------------------------------------------------

    @property
    def azure_openai_api_key(self) -> str:
        """Azure OpenAI API key (AZURE_OPENAI_API_KEY or AZURE_API_KEY)."""
        return self._get_cached(
            "azure_openai_api_key",
            lambda: get_env_var("AZURE_OPENAI_API_KEY", "") or get_env_var("AZURE_API_KEY", ""),
        )

    @property
    def azure_openai_endpoint(self) -> str:
        """Azure OpenAI endpoint (AZURE_OPENAI_ENDPOINT or AZURE_API_BASE)."""
        return self._get_cached(
            "azure_openai_endpoint",
            lambda: get_env_var("AZURE_OPENAI_ENDPOINT", "") or get_env_var("AZURE_API_BASE", ""),
        )

    @property
    def azure_openai_api_version(self) -> str:
        """Azure OpenAI API version (empty for v1 Responses API)."""
        return self._get_cached(
            "azure_openai_api_version",
            lambda: get_env_var("AZURE_OPENAI_API_VERSION", ""),
        )

    @staticmethod
    def _is_valid_azure_openai_endpoint(endpoint: str) -> bool:
        """Check if endpoint is a valid Azure OpenAI/AI Foundry endpoint.

        Supports:
        - Azure OpenAI: *.openai.azure.com
        - Azure AI Models: *.models.ai.azure.com
        - Azure AI Foundry Services: *.services.ai.azure.com (per MS docs 2025)
        """
        endpoint_lc = endpoint.strip().lower()
        return any(
            marker in endpoint_lc
            for marker in (".openai.azure.com", ".models.ai.azure.com", ".services.ai.azure.com")
        )

    @property
    def azure_openai_deployment(self) -> str:
        """Azure OpenAI deployment name (AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME)."""
        return self._get_cached(
            "azure_openai_deployment",
            lambda: get_env_var("AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME", ""),
        )

    @property
    def use_azure_openai(self) -> bool:
        """Check if Azure OpenAI should be used (endpoint and key both set)."""

        def _load() -> bool:
            endpoint = self.azure_openai_endpoint
            api_key = self.azure_openai_api_key

            if not (endpoint and api_key):
                return False

            if not self._is_valid_azure_openai_endpoint(endpoint):
                logger.warning(
                    "AZURE_OPENAI_ENDPOINT does not appear to be an Azure OpenAI host "
                    "(.openai.azure.com or .models.ai.azure.com); skipping Azure OpenAI path and "
                    "falling back to standard OpenAI/Foundry configuration."
                )
                return False

            return True

        return self._get_cached("use_azure_openai", _load)

    # -------------------------------------------------------------------------
    # Observability Configuration
    # -------------------------------------------------------------------------

    @property
    def otel_exporter_endpoint(self) -> str | None:
        def _load() -> str | None:
            value = get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT", "")
            return value if value else None

        return self._get_cached("otel_exporter_endpoint", _load)

    # -------------------------------------------------------------------------
    # Server Configuration
    # -------------------------------------------------------------------------

    @property
    def host(self) -> str:
        # Binding to 0.0.0.0 is intentional for container/server deployments
        return self._get_cached("host", lambda: get_env_var("HOST", "0.0.0.0"))  # nosec B104

    @property
    def port(self) -> int:
        return self._get_cached("port", lambda: get_env_int("PORT", default=8000))

    @property
    def environment(self) -> str:
        return self._get_cached("environment", lambda: get_env_var("ENVIRONMENT", "development"))

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear all cached environment values.

        Call this when environment variables may have changed at runtime.
        """
        self._cache.clear()


# Global singleton instance
env_config = EnvConfig()


# =============================================================================
# Validation Functions
# =============================================================================


def validate_required_env_vars(
    required_vars: list[str], optional_vars: list[str] | None = None
) -> None:
    """Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names
        optional_vars: List of optional variable names (logged if missing)

    Raises:
        ConfigurationError: If any required variables are missing
    """
    from ...workflows.exceptions import ConfigurationError

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or not value.strip():
            missing.append(var)

    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")

    if optional_vars:
        for var in optional_vars:
            value = os.getenv(var)
            if not value:
                logger.debug(f"Optional environment variable {var} is not set")


def validate_agentic_fleet_env() -> None:
    """Validate environment variables required for AgenticFleet.

    Checks:
    - Required: OPENAI_API_KEY
    - Optional: TAVILY_API_KEY, OPENAI_BASE_URL, HOST, PORT, ENVIRONMENT
    - Cosmos DB vars if AGENTICFLEET_USE_COSMOS is enabled

    Raises:
        ConfigurationError: If required variables are missing
    """
    required = ["OPENAI_API_KEY"]
    optional = ["TAVILY_API_KEY", "OPENAI_BASE_URL", "HOST", "PORT", "ENVIRONMENT"]
    validate_required_env_vars(required, optional)

    if env_config.use_cosmos:
        cosmos_required = ["AZURE_COSMOS_ENDPOINT", "AZURE_COSMOS_DATABASE"]
        if not env_config.cosmos_use_managed_identity:
            cosmos_required.append("AZURE_COSMOS_KEY")
        validate_required_env_vars(cosmos_required, [])
        logger.info("Cosmos DB integration enabled for database '%s'", env_config.cosmos_database)

    logger.info("Environment variable validation passed")
