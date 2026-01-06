"""Global application settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Info
    APP_NAME: str = "agentic-fleet"
    APP_VERSION: str = "0.7.1"
    DEBUG: bool = False

    # Aliases for easier access
    app_name: str = "agentic-fleet"
    app_version: str = "0.7.1"

    # Concurrency
    max_concurrent_workflows: int = 10

    # CORS
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
    ]
    ws_allow_localhost: bool = False

    # Azure AI Foundry
    AZURE_AI_PROJECT_CONNECTION_STRING: str | None = None
    AZURE_AI_MODEL_DEPLOYMENT_NAME: str = "gpt-4.1-mini"

    # Deep Research
    TAVILY_API_KEY: str | None = None

    # Storage
    COSMOS_DB_CONNECTION_STRING: str | None = None
    COSMOS_DB_DATABASE: str = "agentic-fleet"
    conversations_path: str = ".var/data/conversations.json"

    # Tracing
    OTEL_SERVICE_NAME: str = "agentic-fleet"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # Logging
    log_level: str = "INFO"
    log_json: bool = True
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()
