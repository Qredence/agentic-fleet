"""Azure OpenAI API client implementation.

This module provides a client for interacting with Azure OpenAI models through their API.
It supports both streaming and non-streaming responses, with proper error handling,
retry mechanisms, and token management.
"""

import logging
import json
import time
from typing import Any, AsyncGenerator, Dict, Optional, Union
from urllib.parse import urljoin

import aiohttp
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from tenacity import retry, stop_after_attempt, wait_exponential

from agentic_fleet.models.providers.base import BaseProvider

logger = logging.getLogger(__name__)

class AzureOpenAIError(Exception):
    """Base exception for Azure OpenAI client errors."""
    pass

class AzureOpenAIClient(BaseProvider):
    """Client for Azure OpenAI API.
    
    This client provides access to Azure-hosted OpenAI models through their API endpoint.
    It supports:
    - Multiple deployment configurations
    - Streaming responses
    - Automatic retries with exponential backoff
    - Token usage tracking
    - Proper error handling
    """

    def __init__(
        self,
        azure_deployment: str,
        model: str,
        api_version: str,
        azure_endpoint: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 30.0,
        model_info: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Azure OpenAI client.
        
        Args:
            azure_deployment: Azure deployment name
            model: Model identifier
            api_version: Azure OpenAI API version
            azure_endpoint: Azure endpoint URL
            api_key: Optional API key (falls back to DefaultAzureCredential)
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            model_info: Model capabilities information
        """
        self.deployment = azure_deployment
        self.model = model
        self.api_version = api_version
        self.endpoint = azure_endpoint.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        
        self.model_info = model_info or {
            "vision": "gpt-4-vision" in model.lower(),
            "function_calling": True,
            "json_output": True,
            "family": "azure",
        }
        
        # Initialize Azure credentials if no API key provided
        self.credentials = DefaultAzureCredential() if not api_key else None
        
        # Token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.
        
        Returns:
            Dict of headers including authentication
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        
        if not self.api_key and self.credentials:
            token = self.credentials.get_token("https://cognitiveservices.azure.com/.default")
            headers["Authorization"] = f"Bearer {token.token}"
            
        return headers

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Complete URL with base, deployment, and version
        """
        base = f"{self.endpoint}/openai/deployments/{self.deployment}"
        return f"{base}/{endpoint}?api-version={self.api_version}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the model.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters for the API call
            
        Returns:
            Generated response text
            
        Raises:
            AzureOpenAIError: For API-related errors
            Exception: For other errors
        """
        messages = [{"role": "user", "content": prompt}]
        data = {
            "messages": messages,
            "model": self.model,
            "stream": False,
            **kwargs,
        }

        try:
            async with aiohttp.ClientSession(headers=self._get_headers(), timeout=self.timeout) as session:
                async with session.post(self._build_url("chat/completions"), json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise AzureOpenAIError(f"Azure OpenAI API error: {error_text}")
                    
                    result = await response.json()
                    
                    # Update token usage
                    usage = result.get("usage", {})
                    self.total_prompt_tokens += usage.get("prompt_tokens", 0)
                    self.total_completion_tokens += usage.get("completion_tokens", 0)
                    
                    return result["choices"][0]["message"]["content"]
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Azure OpenAI: {e}")
            raise AzureOpenAIError(f"Connection error: {e}")
        except AzureError as e:
            logger.error(f"Azure authentication error: {e}")
            raise AzureOpenAIError(f"Authentication error: {e}")
        except Exception as e:
            logger.error(f"Error during Azure OpenAI API call: {e}")
            raise

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Stream responses from the model.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters for the API call
            
        Yields:
            Generated response text chunks
            
        Raises:
            AzureOpenAIError: For API-related errors
            Exception: For other errors
        """
        messages = [{"role": "user", "content": prompt}]
        data = {
            "messages": messages,
            "model": self.model,
            "stream": True,
            **kwargs,
        }

        try:
            async with aiohttp.ClientSession(headers=self._get_headers(), timeout=self.timeout) as session:
                async with session.post(self._build_url("chat/completions"), json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise AzureOpenAIError(f"Azure OpenAI API error: {error_text}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                if line.startswith(b"data: "):
                                    line = line[6:]  # Remove "data: " prefix
                                result = json.loads(line)
                                if result.get("choices"):
                                    content = result["choices"][0].get("delta", {}).get("content")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming response: {line}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Azure OpenAI: {e}")
            raise AzureOpenAIError(f"Connection error: {e}")
        except AzureError as e:
            logger.error(f"Azure authentication error: {e}")
            raise AzureOpenAIError(f"Authentication error: {e}")
        except Exception as e:
            logger.error(f"Error during Azure OpenAI API streaming: {e}")
            raise

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage statistics.
        
        Returns:
            Dict containing prompt and completion token counts
        """
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }
