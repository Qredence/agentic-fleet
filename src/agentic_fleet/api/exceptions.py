"""Centralized domain exception types and FastAPI handlers.

These exceptions provide a consistent JSON error envelope across the API:

{"error": {"code": "workflow_not_found", "message": "..."}}

Routes should raise these exceptions instead of ``HTTPException``. The application
registers handlers via ``register_exception_handlers(app)`` during startup.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agentic_fleet.api.conversations.service import (
    ConversationNotFoundError as _StoreConversationNotFound,
)


class AgenticFleetError(Exception):
    """Base domain exception with default metadata.

    Named with *Error* suffix to satisfy ruff N818 naming convention.
    """

    status_code: int = 400
    error_code: str = "agentic_fleet_error"


class WorkflowNotFoundError(AgenticFleetError):
    status_code = 404
    error_code = "workflow_not_found"

    def __init__(self, workflow_id: str | None = None, message: str | None = None) -> None:
        super().__init__(
            message
            or (f"Workflow '{workflow_id}' not found" if workflow_id else "Workflow not found")
        )
        self.workflow_id = workflow_id


class EntityNotFoundError(AgenticFleetError):
    status_code = 404
    error_code = "entity_not_found"

    def __init__(self, entity_id: str | None = None, message: str | None = None) -> None:
        super().__init__(
            message or (f"Entity '{entity_id}' not found" if entity_id else "Entity not found")
        )
        self.entity_id = entity_id


class ConversationMissingError(AgenticFleetError):
    status_code = 404
    error_code = "conversation_not_found"

    def __init__(self, conversation_id: str | None = None, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                f"Conversation '{conversation_id}' not found"
                if conversation_id
                else "Conversation not found"
            )
        )
        self.conversation_id = conversation_id


class WorkflowExecutionError(AgenticFleetError):
    status_code = 500
    error_code = "workflow_execution_error"


class PersistenceError(AgenticFleetError):
    status_code = 500
    error_code = "persistence_error"


class ConfigurationError(AgenticFleetError):
    status_code = 500
    error_code = "configuration_error"


class AgentInitializationError(AgenticFleetError):
    status_code = 500
    error_code = "agent_initialization_error"

    def __init__(self, name: str, reason: str | None = None) -> None:
        message = reason if reason is not None else f"Failed to initialize agent '{name}'"
        super().__init__(message)
        self.agent_name = name


class ConfigurationValidationError(ConfigurationError):
    status_code = 400
    error_code = "configuration_validation_error"

    def __init__(self, errors: Sequence[str] | str) -> None:
        error_list = [errors] if isinstance(errors, str) else list(errors)
        message_body = "; ".join(error_list) if error_list else "Unknown validation error"
        super().__init__(f"Workflow configuration validation failed: {message_body}")
        self.errors = error_list


class ValidationError(AgenticFleetError):
    status_code = 400
    error_code = "validation_error"


# Backwards compatibility: map existing ConversationNotFoundError from conversation store
_CONVERSATION_ERROR_TYPES = (_StoreConversationNotFound, ConversationMissingError)


def _json_error_response(exc: Exception) -> JSONResponse:
    """Create a JSONResponse for an exception.

    Unknown exceptions fall back to 500 with a generic internal error code.
    """
    status_code = getattr(exc, "status_code", 500)
    error_code = getattr(exc, "error_code", "internal_error")
    return JSONResponse(
        status_code=status_code, content={"error": {"code": error_code, "message": str(exc)}}
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""

    exception_types: tuple[type[Exception], ...] = (
        WorkflowNotFoundError,
        EntityNotFoundError,
        ConversationMissingError,
        WorkflowExecutionError,
        PersistenceError,
        ConfigurationError,
        AgentInitializationError,
        ValidationError,
        *_CONVERSATION_ERROR_TYPES,  # Include legacy store KeyError subclass
    )

    for exc_type in exception_types:

        @app.exception_handler(exc_type)  # type: ignore
        async def handler(
            request: Request, exc: Exception, _exc_type: type[Exception] = exc_type
        ) -> JSONResponse:
            # Use dedicated helper for consistent envelope.
            return _json_error_response(exc)


# Backwards compatibility alias
AgenticFleetException = AgenticFleetError  # pragma: no cover

__all__ = [
    "AgentInitializationError",
    "AgenticFleetError",
    "AgenticFleetException",  # alias
    "ConfigurationError",
    "ConfigurationValidationError",
    "ConversationMissingError",
    "EntityNotFoundError",
    "PersistenceError",
    "ValidationError",
    "WorkflowExecutionError",
    "WorkflowNotFoundError",
    "register_exception_handlers",
]
