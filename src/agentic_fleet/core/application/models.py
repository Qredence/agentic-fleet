"""Application settings and configuration models."""

from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings model.

    Attributes:
        app_name: Name of the application
        debug: Debug mode flag
        model_config: LLM model configuration
        agent_config: Agent configuration
        chainlit_config: Chainlit UI configuration
        azure_openai_api_key: Azure OpenAI API key
        azure_openai_endpoint: Azure OpenAI endpoint
        azure_openai_deployment: Azure OpenAI deployment name
        azure_openai_api_version: Azure OpenAI API version
    """

    # Application settings
    app_name: str = "AgenticFleet"
    debug: bool = Field(default=False, env="DEBUG")

    # Azure OpenAI settings
    azure_openai_api_key: str = Field(
        default="azure_openai_api_key", env="AZURE_OPENAI_API_KEY"
    )
    azure_openai_endpoint: str = Field(
        default="AZURE_OPENAI_ENDPOINT", env="AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_deployment: str = Field(
        default="AZURE_OPENAI_DEPLOYMENT", env="AZURE_OPENAI_DEPLOYMENT"
    )
    azure_openai_api_version: str = Field(
        default="AZURE_OPENAI_API_VERSION", env="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_model: str = Field(
        default="AZURE_OPENAI_MODEL", env="AZURE_OPENAI_MODEL"
    )

    # Configuration dictionaries
    model_config: Dict[str, Any] = Field(default_factory=dict)
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    chainlit_config: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",  # Allow extra fields from environment variables
    }
