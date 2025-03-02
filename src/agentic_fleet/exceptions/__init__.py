"""
Exceptions module for Agentic Fleet.

This module defines custom exceptions used throughout the application.
"""

from agentic_fleet.exceptions.api import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from agentic_fleet.exceptions.base import (
    AgenticFleetAPIError,
    AgenticFleetConfigError,
    AgenticFleetDatabaseError,
    AgenticFleetError,
)
from agentic_fleet.exceptions.database import (
    DatabaseConnectionError,
    DatabaseIntegrityError,
    DatabaseQueryError,
)

__all__ = [
    # Base exceptions
    "AgenticFleetError",
    "AgenticFleetAPIError",
    "AgenticFleetDatabaseError",
    "AgenticFleetConfigError",

    # API exceptions
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",

    # Database exceptions
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseIntegrityError",
]
