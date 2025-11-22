"""Custom exception classes for the Agentic Fleet API."""

from __future__ import annotations


class AgenticFleetAPIError(Exception):
    """Base exception for all Agentic Fleet API errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class WorkflowExecutionError(AgenticFleetAPIError):
    """Raised when workflow execution fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, status_code=500)
        self.details = details or {}


class InvalidConfigurationError(AgenticFleetAPIError):
    """Raised when workflow configuration is invalid."""

    def __init__(self, message: str, config_errors: list[str] | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            config_errors: List of configuration validation errors
        """
        super().__init__(message, status_code=422)
        self.config_errors = config_errors or []


class ResourceNotFoundError(AgenticFleetAPIError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize the exception.

        Args:
            resource_type: Type of resource (e.g., "workflow", "agent")
            resource_id: ID of the resource
        """
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id
