"""Environment variable validation utilities."""

from __future__ import annotations

import logging
import os

from ..workflows.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


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

    # Conditional Cosmos DB validation
    use_cosmos = os.getenv("AGENTICFLEET_USE_COSMOS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if use_cosmos:
        cosmos_required = ["AZURE_COSMOS_ENDPOINT", "AZURE_COSMOS_DATABASE"]

        use_managed_identity = os.getenv(
            "AZURE_COSMOS_USE_MANAGED_IDENTITY", ""
        ).strip().lower() in {"1", "true", "yes", "on"}

        # When managed identity is disabled (default), require a key for local/dev use.
        if not use_managed_identity:
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
            os.getenv("AZURE_COSMOS_DATABASE", "<unset>"),
        )

    logger.info("Environment variable validation passed")


__all__ = ["get_env_var", "validate_agentic_fleet_env", "validate_required_env_vars"]
