"""
AgenticFleet - A multi-agent system for adaptive AI reasoning and automation.

This package provides a powerful framework for building and deploying multi-agent systems
that can adapt and reason about complex tasks. It integrates with Chainlit for the frontend
and FastAPI for the backend, providing a seamless development experience.
"""

__version__ = "0.4.80"
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

# Core application imports
from agentic_fleet.core.application import (
    TEAM_CONFIGURATIONS,
    create_chat_profile,
    create_chat_profile_with_code_execution,
    stream_text,
)

# Expose key components
__all__ = [
    'create_chat_profile',
    'create_chat_profile_with_code_execution',
    'stream_text',
    'TEAM_CONFIGURATIONS'
]
