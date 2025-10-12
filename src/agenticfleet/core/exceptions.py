"""Custom exceptions for AgenticFleet."""


class AgenticFleetError(Exception):
    """Base exception for all AgenticFleet errors."""

    pass


class AgentConfigurationError(AgenticFleetError):
    """Raised when agent configuration is invalid."""

    pass


class WorkflowError(AgenticFleetError):
    """Raised when workflow execution fails."""

    pass


class ToolExecutionError(AgenticFleetError):
    """Raised when a tool execution fails."""

    pass


class ContextProviderError(AgenticFleetError):
    """Raised when context provider operations fail."""

    pass
