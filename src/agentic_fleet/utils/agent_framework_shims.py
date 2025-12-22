"""Runtime shims for optional ``agent_framework`` dependency.

.. deprecated:: 0.8.0
    This module has been split into focused submodules for better maintainability.
    Import from ``agentic_fleet.utils.agent_framework`` instead.
    
    The old import path will be removed in version 1.0.0.

Example:
    Old (deprecated)::
    
        from agentic_fleet.utils.agent_framework_shims import ensure_agent_framework_shims
    
    New (recommended)::
    
        from agentic_fleet.utils.agent_framework import ensure_agent_framework_shims

The new package structure provides better organization:
    - ``agent_framework.utils`` - Module patching utilities
    - ``agent_framework.exceptions`` - Exception hierarchy patches
    - ``agent_framework.core`` - Core type classes
    - ``agent_framework.tools`` - Tool-related types and serialization
    - ``agent_framework.agents`` - Agent classes
    - ``agent_framework.openai`` - OpenAI client shims
"""

from __future__ import annotations

import warnings

# Re-export from new location for backward compatibility
from agentic_fleet.utils.agent_framework import ensure_agent_framework_shims

warnings.warn(
    "Importing from 'agentic_fleet.utils.agent_framework_shims' is deprecated. "
    "Use 'agentic_fleet.utils.agent_framework' instead. "
    "This compatibility shim will be removed in version 1.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ensure_agent_framework_shims"]

