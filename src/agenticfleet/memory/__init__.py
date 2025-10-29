"""
AgenticFleet Memory System

Core memory management functionality using OpenMemory MCP server integration.
"""

from .config import MemoryConfig, MemoryPolicy, memory_config, memory_policy
from .context_provider import MemoryContextProvider
from .manager import MemoryManager
from .mcp_integration import OpenMemoryMCPIntegration
from .models import (
    Memory,
    MemoryBatch,
    MemoryMetadata,
    MemoryPriority,
    MemoryQuery,
    MemorySearchResult,
    MemoryStats,
    MemoryType,
)
from .workflow_integration import (
    MemoryWorkflowIntegration,
    get_workflow_integration,
    set_workflow_integration,
)

__all__ = [
    "Memory",
    "MemoryBatch",
    "MemoryConfig",
    "MemoryContextProvider",
    "MemoryManager",
    "MemoryMetadata",
    "MemoryPolicy",
    "MemoryPriority",
    "MemoryQuery",
    "MemorySearchResult",
    "MemoryStats",
    "MemoryType",
    "MemoryWorkflowIntegration",
    "OpenMemoryMCPIntegration",
    "get_workflow_integration",
    "memory_config",
    "memory_policy",
    "set_workflow_integration",
]
