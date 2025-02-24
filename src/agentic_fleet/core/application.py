"""
Core application module for AgenticFleet.

This module provides the main application management functionality,
including initialization and lifecycle management.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ApplicationConfig:
    """Configuration for the AgenticFleet application."""

    project_root: Path
    config_path: Optional[Path] = None
    debug: bool = False
    log_level: str = "INFO"


class ApplicationManager:
    """Manages the lifecycle and configuration of the AgenticFleet application."""

    def __init__(self, config: ApplicationConfig):
        self.config = config
        self._initialized = False

    async def initialize(self):
        """Initialize the application manager."""
        if self._initialized:
            return

        # Initialize core components
        self._initialized = True

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
