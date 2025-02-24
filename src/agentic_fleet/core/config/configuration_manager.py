"""
Configuration Manager for AgenticFleet.

This module provides centralized configuration management with validation
and logging capabilities. It follows the singleton pattern to ensure
consistent configuration state across the application.
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages configuration settings for the AgenticFleet project.

    This class follows the singleton pattern to ensure only one instance
    exists throughout the application lifecycle. It provides project root
    validation and logging capabilities.

    Attributes:
        _instance: Singleton instance of ConfigurationManager
        _project_root: Cached project root path
    """

    _instance: Optional['ConfigurationManager'] = None
    _project_root: Optional[Path] = None

    def __new__(cls) -> 'ConfigurationManager':
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the configuration manager with validation."""
        self._project_root = self.get_project_root()
        self._validate_root()
        logger.info(f"ConfigurationManager initialized at {self._project_root}")

    def _validate_root(self) -> None:
        """
        Validate project root structure.

        Raises:
            FileNotFoundError: If required directories are missing
        """
        required_dirs: List[Path] = [
            self._project_root / "src" / "agentic_fleet",
            self._project_root / "tests"
        ]

        missing = [d for d in required_dirs if not d.exists()]
        if missing:
            error_msg = f"Missing critical directories: {[str(d) for d in missing]}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.debug("Project root structure validated successfully")

    def get_project_root(self) -> Path:
        """
        Get the root directory of the project.

        Returns:
            Path: The project root directory

        Note:
            This method caches the project root path after first calculation
        """
        if self._project_root is None:
            # Start from the current file's directory
            current_dir = Path(__file__).resolve().parent

            # Keep going up until we find the project root (where src/ is)
            while current_dir.name != "AgenticFleet" and current_dir.parent != current_dir:
                current_dir = current_dir.parent

            if current_dir.name != "AgenticFleet":
                raise FileNotFoundError("Could not find project root directory")

            self._project_root = current_dir
            logger.debug(f"Project root calculated: {self._project_root}")

        return self._project_root
