"""Module for client creation and management services.

This module provides functions for creating and managing LLM clients.
It is the preferred implementation that replaces the deprecated
agentic_fleet.models.client_factory module.
"""

# Standard library imports
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

# Third-party imports
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Local imports
from agentic_fleet.config.llm_config_manager import llm_config_manager

# Initialize logging
logger = logging.getLogger(__name__)


def create_client(
    model_name: str,
    streaming: bool = True,
    vision: bool = True,
    connection_pool_size: int = 10,
    request_timeout: int = 30,
    model_config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> AzureOpenAIChatCompletionClient:
    """Create and return an Azure OpenAI client with the specified configuration.

    Args:
        model_name: The name of the model to use
        streaming: Whether to enable streaming responses
        vision: Whether to enable vision capabilities
        connection_pool_size: Connection pool size for the client
        request_timeout: Request timeout in seconds
        model_config: Optional model configuration from llm_config.yaml
        **kwargs: Additional parameters to pass to the client

    Returns:
        An instance of AzureOpenAIChatCompletionClient

    Raises:
        ValueError: If required environment variables are missing
    """
    # Validate required environment variables
    required_env_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required Azure OpenAI environment variables: {', '.join(missing_vars)}")

    # Use model configuration if provided, otherwise use parameters
    if model_config:
        # Override parameters with config values
        model_name = model_config.get("name", model_name)
        streaming = model_config.get("streaming", streaming)
        vision = model_config.get("vision", vision)
        connection_pool_size = model_config.get("connection_pool_size", connection_pool_size)
        request_timeout = model_config.get("request_timeout", request_timeout)

    # Determine model family
    model_family = "gpt-4o" if "gpt-4o" in model_name else "azure"

    # Create model_info dictionary
    model_info = {
        "vision": vision,
        "function_calling": True,
        "json_output": True,
        "family": model_family,
        "architecture": model_name,
    }

    # Create and return client
    # Use AZURE_OPENAI_DEPLOYMENT environment variable if available, otherwise fall back to model_name
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", model_name)

    try:
        client = AzureOpenAIChatCompletionClient(
            model=model_name,
            deployment=deployment_name,
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            model_streaming=streaming,
            model_info=model_info,
            streaming=streaming,
            connection_pool_size=connection_pool_size,
            request_timeout=request_timeout,
            **kwargs,
        )
    except Exception as e:
        if "DeploymentNotFound" in str(e):
            error_msg = (
                f"Azure OpenAI deployment '{deployment_name}' not found. "
                f"Please check that the deployment exists in your Azure OpenAI resource. "
                f"If you created the deployment recently, please wait a few minutes and try again. "
                f"You can also set the AZURE_OPENAI_DEPLOYMENT environment variable to specify a different deployment."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        raise

    logger.info(f"Created client for model {model_name} with streaming={streaming}, vision={vision}")
    return client


@lru_cache(maxsize=10)
def get_cached_client(
    model_name: str,
    streaming: bool = True,
    vision: bool = True,
    connection_pool_size: int = 10,
    request_timeout: int = 30,
    use_config: bool = True,
    model_config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> AzureOpenAIChatCompletionClient:
    """Get a cached client instance or create a new one if not in cache.

    This function caches clients based on their configuration parameters to avoid
    creating multiple clients with the same settings.

    Args:
        model_name: The name of the model to use
        streaming: Whether to enable streaming responses
        vision: Whether to enable vision capabilities
        connection_pool_size: Connection pool size for the client
        request_timeout: Request timeout in seconds
        use_config: Whether to use the configuration from llm_config.yaml
        **kwargs: Additional parameters to pass to the client

    Returns:
        An instance of AzureOpenAIChatCompletionClient from cache or newly created

    Raises:
        ValueError: If required environment variables are missing
    """
    # Remove lru_cache as it doesn't work with dict parameters
    # Get model configuration if requested and not already provided
    if model_config is None and use_config:
        try:
            # Try to get model config from the manager
            model_config = llm_config_manager.get_model_config(model_name)
        except ValueError:
            # If model not found in config, use the provided parameters
            logger.warning(f"Model {model_name} not found in configuration, using provided parameters")

    # Create and return a new client
    return create_client(
        model_name=model_name,
        streaming=streaming,
        vision=vision,
        connection_pool_size=connection_pool_size,
        request_timeout=request_timeout,
        model_config=model_config,
        **kwargs,
    )


# Remove @lru_cache decorator since it doesn't work with dict parameters
def get_client_for_profile(profile_name: str, **kwargs: Any) -> AzureOpenAIChatCompletionClient:
    """Get a client for a specific profile.

    Args:
        profile_name: The name of the profile to get the client for
        **kwargs: Additional parameters to pass to the client

    Returns:
        An instance of AzureOpenAIChatCompletionClient for the profile

    Raises:
        ValueError: If the profile or model is not found in the configuration
    """
    try:
        # Get the model configuration for the profile
        # Get the model configuration for the profile
        model_config = llm_config_manager.get_model_for_profile(profile_name)
        # Extract model name safely with a fallback
        model_name = model_config.get("name", "gpt-4o-mini-2024-07-18")

        # Create client directly without using the cache
        # to avoid unhashable dict error
        return create_client(
            model_name=model_name,
            streaming=True,
            vision=True,
            connection_pool_size=10,
            request_timeout=30,
            model_config=model_config,
            **kwargs,
        )
    except ValueError as e:
        logger.error(f"Error getting client for profile {profile_name}: {e}")
        raise
