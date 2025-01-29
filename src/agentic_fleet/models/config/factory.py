"""Factory for creating model clients."""

import os
from enum import Enum
from typing import Any, Dict, Optional, cast

from autogen_core.models import ChatCompletionClient
from dotenv import load_dotenv

from agentic_fleet.models.providers import (
    AzureAIFoundryClient,
    AzureOpenAIClient,
    CogCacheClient,
    DeepSeekClient,
    GeminiClient,
    OllamaClient,
    OpenAIClient
)

# Load environment variables from .env file
load_dotenv()


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"
    COGCACHE = "cogcache"


class ModelFactory:
    """Factory for creating model clients."""

    @staticmethod
    def create(provider: ModelProvider, **kwargs: Any) -> ChatCompletionClient:
        """Create a model client based on provider.

        Args:
            provider: The model provider to use
            **kwargs: Provider-specific configuration options

        Returns:
            ChatCompletionClient: Configured model client

        Raises:
            ValueError: If provider is not supported
        """
        if provider == ModelProvider.OPENAI:
            return cast(ChatCompletionClient, OpenAIClient(**kwargs))
        elif provider == ModelProvider.AZURE_OPENAI:
            return cast(ChatCompletionClient, AzureOpenAIClient(**kwargs))
        elif provider == ModelProvider.GEMINI:
            return cast(ChatCompletionClient, GeminiClient(**kwargs))
        elif provider == ModelProvider.OLLAMA:
            return cast(ChatCompletionClient, OllamaClient(**kwargs))
        elif provider == ModelProvider.DEEPSEEK:
            return cast(ChatCompletionClient, DeepSeekClient(**kwargs))
        elif provider == ModelProvider.AZURE_AI_FOUNDRY:
            return cast(ChatCompletionClient, AzureAIFoundryClient(**kwargs))
        elif provider == ModelProvider.COGCACHE:
            return cast(ChatCompletionClient, CogCacheClient(**kwargs))
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def create_default() -> ChatCompletionClient:
        """Create a default model client (Azure OpenAI).

        Returns:
            ChatCompletionClient: Default configured model client

        Raises:
            ValueError: If required environment variables are not set
        """
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")

        return cast(ChatCompletionClient, AzureOpenAIClient(
            deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
            endpoint=endpoint,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        ))
