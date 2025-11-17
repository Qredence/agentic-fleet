"""Fleet workflow decorators.

This module provides local wrappers around agent-framework decorators.

The primary purpose is to resolve deferred type annotations (e.g. from
``from __future__ import annotations`` or PEP 649 lazy annotations)
before delegating to the underlying agent-framework decorators. This
ensures that WorkflowContext annotations are concrete types when
agent-framework validates handler signatures.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, get_type_hints

from agent_framework import handler as _framework_handler


def handler(func: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[override]
    """Wrapper around :func:`agent_framework.handler`.

    This decorator resolves type annotations for the wrapped function
    using :func:`typing.get_type_hints` before delegating to the real
    agent-framework ``handler`` decorator. This is primarily to ensure
    that ``WorkflowContext`` annotations are concrete types (rather than
    ``ForwardRef`` or other unevaluated forms) so that
    ``validate_workflow_context_annotation`` can correctly recognize and
    validate them.
    """

    try:
        # Evaluate annotations in the function's global namespace so that
        # Deferred annotations like ``WorkflowContext[MessageType]`` are
        # resolved to concrete generic aliases.
        hints = get_type_hints(func, globalns=func.__globals__, localns=None)
    except Exception:
        # If we cannot resolve type hints for any reason, fall back to the
        # underlying decorator without modification. This maintains
        # compatibility even in edge cases.
        return _framework_handler(func)  # type: ignore[return-value]

    # Start from existing annotations (which may still contain unevaluated
    # expressions) and overwrite with any successfully resolved hints.
    annotations = dict(getattr(func, "__annotations__", {}))
    annotations.update(hints)
    func.__annotations__ = annotations

    # Delegate to the real agent-framework handler decorator.
    return _framework_handler(func)  # type: ignore[return-value]
