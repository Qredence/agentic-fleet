"""
Core application module for AgenticFleet.

This module provides the main application management functionality,
including initialization and lifecycle management.
"""

# Standard library imports
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Third-party imports
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

logger = logging.getLogger(__name__)


@dataclass
class ApplicationConfig:
    """Configuration for the AgenticFleet application."""

    project_root: Path
    config_path: Optional[Path] = None
    debug: bool = False
    log_level: str = "INFO"
    host: str = "localhost"
    port: int = 8000

    @property
    def settings(self) -> Dict[str, Any]:
        """Get application settings.

        Returns:
            Dict[str, Any]: Application settings
        """
        return {
            "debug": self.debug,
            "log_level": self.log_level,
            "host": self.host,
            "port": self.port,
        }


class ApplicationManager:
    """Manages the lifecycle and configuration of the AgenticFleet application."""

    def __init__(self, config: ApplicationConfig):
        self.config = config
        self._initialized = False
        self.model_client = AzureOpenAIChatCompletionClient(
            model="gpt-4o-mini-2024-07-18",
            deployment="gpt-4o-mini",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_base=os.getenv("AZURE_OPENAI_API_BASE"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            streaming=True,
        )

    async def initialize(self):
        """Initialize the application manager."""
        if self._initialized:
            return

        # Initialize core components
        self._initialized = True

    async def start(self):
        """Start the application manager.

        Initializes all components and starts the main application loop.
        """
        if not self._initialized:
            await self.initialize()

        # Start application components
        logger.info("Starting application components")

    async def shutdown(self):
        """Shutdown the application manager."""
        if not self._initialized:
            return

        self._initialized = False


def create_application(config: Optional[Dict[str, Any]] = None) -> ApplicationManager:
    """
    Create and initialize a new application instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        ApplicationManager: Initialized application manager
    """
    if config is None:
        config = {}

    app_config = ApplicationConfig(
        project_root=Path(__file__).parent.parent.parent, **config
    )

    return ApplicationManager(app_config)
