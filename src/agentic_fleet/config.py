"""Configuration settings for the AgenticFleet application."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""

    # App Settings
    APP_NAME: str = "AgenticFleet"
    APP_VERSION: str = "0.4.3"
    DEBUG: bool = False

    # API Settings
    API_PREFIX: str = "/api"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-fleet")
    AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-2024-11-20")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    # Chainlit Settings
    CHAINLIT_AUTH_SECRET: Optional[str] = os.getenv("CHAINLIT_AUTH_SECRET")
    CHAINLIT_MAX_WORKERS: int = 4

    # Agent Settings
    DEFAULT_MAX_ROUNDS: int = 50
    DEFAULT_MAX_TIME: int = 10  # minutes
    DEFAULT_MAX_STALLS: int = 5
    DEFAULT_START_PAGE: str = "https://bing.com"

    # Workspace Settings
    WORKSPACE_DIR: str = "workspace"

    # CORS Settings
    CORS_ORIGINS: list = ["*"]  # In production, replace with specific origins
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Create settings instance
settings = Settings()
