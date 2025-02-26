"""Module for client creation logic."""

# Standard library imports
import os
import logging
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

# Third-party imports
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Initialize logging
logger = logging.getLogger(__name__)


def create_client(
    model_name: str,
    streaming: bool = True,
    vision: bool = False,
    connection_pool_size: int = 10,
    request_timeout: int = 30,
    **kwargs: Any,
) -> AzureOpenAIChatCompletionClient:
    """Create and return an Azure OpenAI client with the specified configuration.
    
    Args:
        model_name: The name of the model to use
        streaming: Whether to enable streaming responses
        vision: Whether to enable vision capabilities
        connection_pool_size: Connection pool size for the client
        request_timeout: Request timeout in seconds
        **kwargs: Additional parameters to pass to the client
        
    Returns:
        An instance of AzureOpenAIChatCompletionClient
    """
    # Added validation
    if not all([os.getenv("AZURE_OPENAI_ENDPOINT"), 
               os.getenv("AZURE_OPENAI_API_KEY"),
               os.getenv("AZURE_OPENAI_API_VERSION")]):
        raise ValueError("Missing required Azure OpenAI environment variables")
    
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
    client = AzureOpenAIChatCompletionClient(
        model=model_name,
        deployment=model_name,
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
    
    logger.info(f"Created client for model {model_name} with streaming={streaming}, vision={vision}")
    return client


@lru_cache(maxsize=10)
def get_cached_client(
    model_name: str,
    streaming: bool = True,
    vision: bool = False,
    connection_pool_size: int = 10,
    request_timeout: int = 30,
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
        **kwargs: Additional parameters to pass to the client
        
    Returns:
        An instance of AzureOpenAIChatCompletionClient from cache or newly created
    """
    # Convert kwargs to a hashable representation for caching
    kwargs_items = tuple(sorted(kwargs.items()))
    
    # Create and return a new client
    return create_client(
        model_name=model_name,
        streaming=streaming,
        vision=vision,
        connection_pool_size=connection_pool_size,
        request_timeout=request_timeout,
        **kwargs,
    ) 