"""Configuration settings for the AgenticFleet application."""

import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
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
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o3-mini")
    AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "o3-mini-2025-01-31")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    # Chainlit Settings
    CHAINLIT_SERVER_URL: str = os.getenv("CHAINLIT_SERVER_URL", "http://localhost:8000")
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
    CORS_ORIGINS: str = "*"
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_HEADERS: str = "Content-Type,Authorization"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra fields
    )

    @field_validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v: str) -> List[str]:
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("CORS_METHODS")
    def validate_cors_methods(cls, v: str) -> List[str]:
        return [method.strip() for method in v.split(",") if method.strip()]

    @field_validator("CORS_HEADERS")
    def validate_cors_headers(cls, v: str) -> List[str]:
        return [header.strip() for header in v.split(",") if header.strip()]

# Create settings instance
settings = Settings()
