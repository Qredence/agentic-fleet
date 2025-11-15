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
    """
    required = ["OPENAI_API_KEY"]
    optional = ["TAVILY_API_KEY", "OPENAI_BASE_URL", "HOST", "PORT", "ENVIRONMENT"]

    validate_required_env_vars(required, optional)
    logger.info("Environment variable validation passed")


__all__ = ["get_env_var", "validate_agentic_fleet_env", "validate_required_env_vars"]
