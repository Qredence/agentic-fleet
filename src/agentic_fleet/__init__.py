"""
AgenticFleet - A multi-agent system for adaptive AI reasoning and automation.

This package provides a powerful framework for building and deploying multi-agent systems
that can adapt and reason about complex tasks. It integrates with Chainlit for the frontend
and FastAPI for the backend, providing a seamless development experience.
"""

__version__ = "0.4.50"
__author__ = "Zochory"
__email__ = "zochory@qredence.com"
__license__ = "MIT"
__copyright__ = "Copyright 2025 Zochory"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-fleet")
except PackageNotFoundError:
    # Package is not installed
    pass

# Expose key components at package level
from .app import handle_message, initialize_session, update_settings  # noqa: F401
from .cli import cli  # noqa: F401
