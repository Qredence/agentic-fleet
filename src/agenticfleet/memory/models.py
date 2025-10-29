"""
Memory system data models for AgenticFleet.

Defines the core data structures for storing, retrieving, and managing memories
using the OpenMemory MCP server integration.
"""

from datetime import datetime
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memories that can be stored in the system."""

    CONVERSATION = "conversation"  # Conversation history and context
    LEARNING = "learning"  # Lessons learned and insights
    PATTERN = "pattern"  # Reusable patterns and workflows
    PREFERENCE = "preference"  # User preferences and configurations
    CONTEXT = "context"  # Project-specific context and knowledge
    ERROR = "error"  # Error patterns and solutions
    TOOL_USAGE = "tool_usage"  # Tool usage patterns and best practices
    WORKFLOW = "workflow"  # Workflow optimization learnings


class MemoryPriority(str, Enum):
    """Priority levels for memories to determine retrieval importance."""

    CRITICAL = "critical"  # Must be retrieved immediately
    HIGH = "high"  # Important for most contexts
    MEDIUM = "medium"  # Moderately important
    LOW = "low"  # Nice to have if relevant
    ARCHIVE = "archive"  # Historical, rarely needed


class MemoryMetadata(BaseModel):
    """Metadata for stored memories."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    access_count: int = Field(default=0)
    last_accessed: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    source_agent: str | None = None
    conversation_id: str | None = None
    workflow_id: str | None = None
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)


class Memory(BaseModel):
    """Core memory model for storing information in OpenMemory."""

    id: str
    type: MemoryType
    title: str
    content: str
    metadata: MemoryMetadata
    priority: MemoryPriority = MemoryPriority.MEDIUM
    context_keywords: list[str] = Field(default_factory=list)
    related_memories: list[str] = Field(default_factory=list)

    class Config:
        json_encoders: ClassVar = {datetime: lambda v: v.isoformat() if v else None}


class MemoryQuery(BaseModel):
    """Query model for retrieving relevant memories."""

    query: str
    memory_types: list[MemoryType] = Field(default_factory=list)
    priority_filter: MemoryPriority | None = None
    context_keywords: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    agent_filter: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
    min_relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemorySearchResult(BaseModel):
    """Result from memory search operations."""

    memories: list[Memory]
    total_found: int
    query_time_ms: float
    relevance_threshold: float


class MemoryBatch(BaseModel):
    """Batch memory operations for efficient processing."""

    memories: list[Memory]
    operation: str  # 'store', 'update', 'delete'
    batch_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryStats(BaseModel):
    """Statistics about memory usage and performance."""

    total_memories: int
    memories_by_type: dict[MemoryType, int]
    memories_by_priority: dict[MemoryPriority, int]
    average_access_count: float
    most_accessed_memories: list[str]
    recently_created: list[str]
    storage_usage_mb: float
