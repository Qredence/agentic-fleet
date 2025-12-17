"""Shared helpers for workflow executors."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from ...utils.logger import setup_logger

logger = setup_logger(__name__)


def handler(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle type hints for executors.

    Ensures type hints are properly resolved and available at runtime
    for the agent framework's handler registration mechanism.

    Args:
        func: The handler function to decorate.

    Returns:
        The decorated function with resolved type annotations.
    """
    from typing import get_type_hints

    from agent_framework._workflows import handler as _framework_handler

    try:
        func_obj = cast(Any, func)
        globalns = getattr(func_obj, "__globals__", {})
        hints = get_type_hints(func, globalns=globalns, localns=None)

        annotations = dict(getattr(func_obj, "__annotations__", {}))
        annotations.update(hints)
        func_obj.__annotations__ = annotations
    except Exception as exc:
        # Gracefully handle type hint resolution errors; log them for visibility
        func_name = getattr(cast(Any, func), "__name__", repr(func))
        logger.warning("Failed to resolve type hints for %s: %s", func_name, exc)
    return _framework_handler(func)
