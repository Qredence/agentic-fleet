"""Runtime shims for optional ``agent_framework`` dependency.

These helpers ensure core ``agent_framework`` modules exist in ``sys.modules``
when the real package is not installed (e.g., in tests or lightweight
workspaces). Only the subset of the API referenced inside AgenticFleet is
implemented, providing just enough surface area for imports to succeed.
"""

from __future__ import annotations

from typing import Any, cast

from .agents import patch_agent_classes
from .core import patch_core_types
from .exceptions import patch_exceptions_module
from .openai import patch_openai_module
from .tools import patch_serialization_module, patch_tool_types
from .utils import _import_or_stub, _reexport_public_api

__all__ = ["ensure_agent_framework_shims"]


def _patch_root_attributes(root: Any) -> None:
    """Patch basic root module attributes."""
    if not hasattr(root, "__version__"):
        # Some installed versions ship an empty `agent_framework/__init__.py`, but
        # internal modules (e.g., `observability`) expect `__version__` to exist.
        root.__version__ = "0.0.0"  # type: ignore[attr-defined]

    # User-Agent string expected by agent_framework_azure_ai package
    if not hasattr(root, "AGENT_FRAMEWORK_USER_AGENT"):
        version = getattr(root, "__version__", "0.0.0")
        root.AGENT_FRAMEWORK_USER_AGENT = f"agentic-fleet/{version}"  # type: ignore[attr-defined]


def _reexport_known_apis(root: Any) -> None:
    """Re-export known public APIs from submodules to root."""
    # Prefer real agent-framework implementations when available
    # Some distributions ship an empty `agent_framework/__init__.py` and rely on consumers
    # importing from internal modules. The workflows package, however, imports many symbols
    # from the root package. Re-exporting known public APIs keeps those imports working.
    _reexport_public_api(root, "agent_framework._types")
    _reexport_public_api(root, "agent_framework._tools")
    _reexport_public_api(root, "agent_framework._memory")
    _reexport_public_api(root, "agent_framework._threads")
    _reexport_public_api(root, "agent_framework._agents")
    _reexport_public_api(root, "agent_framework._workflows")
    _reexport_public_api(root, "agent_framework._clients")  # BaseChatClient
    _reexport_public_api(root, "agent_framework._logging")  # get_logger
    _reexport_public_api(root, "agent_framework._middleware")  # use_chat_middleware


def ensure_agent_framework_shims() -> None:
    """Ensure ``agent_framework`` symbols exist even when dependency is absent.

    This function patches the agent_framework module to ensure all required
    symbols are available, even when the package is not installed. The patching
    is organized into focused helper functions for better maintainability.
    """
    root = cast(Any, _import_or_stub("agent_framework"))

    # Apply patches in logical order
    _patch_root_attributes(root)
    patch_exceptions_module(root)
    _reexport_known_apis(root)
    patch_core_types(root)
    patch_tool_types(root)
    patch_serialization_module()
    patch_agent_classes(root)
    patch_openai_module()
