"""Exception hierarchy patches for agent_framework."""

from __future__ import annotations

from typing import Any, cast

from .utils import _ensure_submodule

__all__ = ["patch_exceptions_module"]


def patch_exceptions_module(root: Any) -> type[Exception]:
    """Patch exceptions module and return base exception class."""
    exceptions = cast(Any, _ensure_submodule("agent_framework.exceptions"))
    root.exceptions = exceptions  # type: ignore[attr-defined]

    if not hasattr(exceptions, "AgentFrameworkException"):

        class AgentFrameworkException(Exception):  # noqa: N818
            """Compatibility shim for agent-framework base exception."""

        exceptions.AgentFrameworkException = AgentFrameworkException

    base_exception = cast(type[Exception], exceptions.AgentFrameworkException)

    if not hasattr(exceptions, "ToolException"):
        exceptions.ToolException = type(
            "ToolException",
            (base_exception,),
            {"__doc__": "Fallback tool exception shim."},
        )

    if not hasattr(exceptions, "ToolExecutionException"):
        exceptions.ToolExecutionException = type(
            "ToolExecutionException",
            (base_exception,),
            {"__doc__": "Fallback tool execution exception shim."},
        )

    return base_exception
