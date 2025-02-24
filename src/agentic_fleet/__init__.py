"""
AgenticFleet - A multi-agent system for adaptive AI reasoning and automation.

This package provides a powerful framework for building and deploying multi-agent systems
that can adapt and reason about complex tasks. It integrates with FastAPI for the backend
and provides a modern web interface for interaction.
"""

from agentic_fleet.core.application import (
    ApplicationManager,
    create_application,
)

__version__ = "0.4.9"
__author__ = "Qredence"
__email__ = "contact@qredence.ai"
__license__ = "Apache 2.0"
__copyright__ = "Copyright 2025 Qredence"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-fleet")
except PackageNotFoundError:
    # Package is not installed
    pass

# Initialize configuration
from agentic_fleet.config import config_manager

config_manager.load_all()

__all__ = [
    # Core components
    "ApplicationManager",
    "create_application",
    # Configuration
    "config_manager",
]

# This file is intentionally left empty to mark the agentic_fleet directory as a package.
