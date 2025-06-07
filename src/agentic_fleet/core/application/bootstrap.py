"""Core application bootstrap module."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv

from agentic_fleet.config import config_manager
from agentic_fleet.core.application.manager import ApplicationConfig, ApplicationManager


def initialize_app() -> ApplicationManager:
    """Initialize the core application components.

    Returns:
        ApplicationManager: Initialized application manager
    """
    # Load environment variables - this is now handled by config_manager import
    # load_dotenv() # Removed

    # Initialize configuration
    # config_manager.load_all() is called when config_manager is imported.
    # Re-calling it here might be redundant unless specifically needed to pick up
    # very late environment changes not present at initial import time.
    # For centralization, relying on the import-time load is preferred.
    # If load_all() is idempotent and cheap, it might be okay, but let's assume
    # it's not strictly necessary here if config_manager is already imported and loaded.
    # However, to be safe and ensure it reflects any .env loaded by its own settings loader:
    config_manager.load_all() # Explicitly ensure it's loaded if not already.
    app_settings = config_manager.get_app_settings()

    # Create application config
    config = ApplicationConfig(
        project_root=Path(os.getcwd()),
        config_path=Path("config"),
        debug=app_settings.get("debug", False),
        log_level=app_settings.get("log_level", "INFO"),
    )

    # Initialize application manager
    # ApplicationManager will now be responsible for creating a default client if one is not provided.
    return ApplicationManager(config=config)

# Removed _create_model_client as it's no longer used.
# LLM client creation is now centralized in services.client_factory.py
# and ApplicationManager will use it if it needs a default client.
