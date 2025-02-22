"""
LLM Factory Module.

This module provides a factory for creating and configuring LLM instances.
It currently supports Azure OpenAI configuration only.

For example, to initialize an Azure OpenAI client for the "o3-mini" model on Azure, use:

    from openai import AzureOpenAIChatCompletionClient

    model_client = AzureOpenAIChatCompletionClient(
        model="o3-mini-2025-01-31",
        base_url="https://ai-aiagenthub470987418747.openai.azure.com/openai/deployments/o3-mini/chat/completions?api-version=2024-12-01-preview",
        api_key="AZURE_OPENAI_API_KEY",
        model_info={
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
        },
    )
"""

from openai import AzureOpenAIChatCompletionClient


def get_llm(provider: str, **kwargs):
    """
    Factory method to create an LLM instance based on the specified provider.

    Parameters:
        provider (str): The name of the LLM provider. Currently, only "azure" is supported.
        **kwargs: Additional configuration parameters for the LLM instance.
            For the "azure" provider, expected keys are:
                - model:       The model name (e.g., "o3-mini-2025-01-31")
                - base_url:    The endpoint URL for the Azure OpenAI service.
                - api_key:     Your Azure OpenAI API key.
                - model_info:  A dict with additional options such as:
                               * vision (bool)
                               * function_calling (bool)
                               * json_output (bool)
                               * family (str)

    Returns:
        An instance of AzureOpenAIChatCompletionClient configured with the provided parameters.

    Raises:
        ValueError: If the provider is unsupported or required configuration parameters are missing.
    """
    provider = provider.lower()
    if provider == "azure":
        required_keys = ["model", "base_url", "api_key", "model_info"]
        for key in required_keys:
            if key not in kwargs:
                raise ValueError(f"Missing required azure configuration parameter: {key}")
        return AzureOpenAIChatCompletionClient(
            model=kwargs["model"],
            base_url=kwargs["base_url"],
            api_key=kwargs["api_key"],
            model_info=kwargs["model_info"],
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
