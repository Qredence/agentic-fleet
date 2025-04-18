"""Module for client creation logic.

DEPRECATED: This module is deprecated and will be removed in a future version.
Use agentic_fleet.services.client_factory instead.
"""

# Standard library imports
import logging
import sys
import warnings
from importlib import import_module

# Initialize logging
logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "The agentic_fleet.models.client_factory module is deprecated and will be removed in a future version. "
    "Use agentic_fleet.services.client_factory instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all symbols from services.client_factory
try:
    # Import the services.client_factory module
    client_factory = import_module("agentic_fleet.services.client_factory")

    # Import all symbols from services.client_factory
    from agentic_fleet.services.client_factory import (
        create_client,
        get_cached_client,
        get_client_for_profile
    )

    logger.info("Successfully imported services.client_factory")
except ImportError as e:
    logger.error(f"Error importing services.client_factory: {e}")
    sys.exit(1)
