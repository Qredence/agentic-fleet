"""Dependency injection functions for the Agentic Fleet API."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Request

from ..utils.logger import setup_logger
from ..workflows.config import WorkflowConfig


def get_request_id(request: Request) -> str:
    """Get the request ID from the request state.

    Args:
        request: The FastAPI request object

    Returns:
        The request ID
    """
    return getattr(request.state, "request_id", "unknown")


def get_logger(request: Request) -> logging.LoggerAdapter:
    """Get a logger with request context.

    Args:
        request: The FastAPI request object

    Returns:
        Logger adapter with request ID context
    """
    logger = setup_logger(__name__)
    request_id = get_request_id(request)

    # Return a logger adapter that includes request_id in all log messages
    return logging.LoggerAdapter(logger, {"request_id": request_id})


def get_workflow_config(config_dict: dict | None = None) -> WorkflowConfig:
    """Get or create a workflow configuration.

    Args:
        config_dict: Optional configuration dictionary

    Returns:
        WorkflowConfig instance
    """
    return WorkflowConfig(**(config_dict or {}))


# Type aliases for dependency injection
RequestID = Annotated[str, Depends(get_request_id)]
Logger = Annotated[logging.LoggerAdapter, Depends(get_logger)]
