"""
Core application module for AgenticFleet.

This module provides the main application management functionality,
including initialization and lifecycle management.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

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
    """
    Manages the lifecycle and configuration of the AgenticFleet application.

    This class is responsible for initializing, starting, and shutting down
    the application components, including model clients, agents, and services.

    Attributes:
        config: The application configuration
        model_client: The Azure OpenAI client for chat completions
        _initialized: Flag indicating whether the application has been initialized
    """

    def __init__(self, config: ApplicationConfig):
        """
        Initialize a new ApplicationManager instance.

        Args:
            config: The application configuration
        """
        self.config = config
        self._initialized = False
        # Use AZURE_OPENAI_DEPLOYMENT environment variable if available, otherwise fall back to a default
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

        try:
            self.model_client = AzureOpenAIChatCompletionClient(
                model="gpt-4o-mini-2024-07-18",
                deployment=deployment_name,
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_base=os.getenv("AZURE_OPENAI_API_BASE"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                streaming=True,
            )
        except Exception as e:
            if "DeploymentNotFound" in str(e):
                error_msg = (
                    f"Azure OpenAI deployment '{deployment_name}' not found. "
                    f"Please check that the deployment exists in your Azure OpenAI resource. "
                    f"If you created the deployment recently, please wait a few minutes and try again. "
                    f"You can also set the AZURE_OPENAI_DEPLOYMENT environment variable to specify a different deployment."
                )
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            raise

    async def initialize(self):
        """
        Initialize the application manager.

        This method sets up all required components and services for the application.
        If the application is already initialized, this method returns without doing anything.
        """
        if self._initialized:
            return

        # Initialize core components
        self._initialized = True

    async def start(self):
        """
        Start the application manager.

        This method initializes all components if not already initialized and
        starts the main application loop. It handles the startup sequence for
        all application components.
        """
        if not self._initialized:
            await self.initialize()

        # Start application components
        logger.info("Starting application components")

    async def shutdown(self):
        """
        Shutdown the application manager.

        This method gracefully stops all application components and services.
        If the application is not initialized, this method returns without doing anything.
        """
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
