"""
Memory system configuration and settings.

Manages configuration for the memory system, including OpenMemory integration
settings, memory policies, and agent-specific configurations.
"""

from typing import Any

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings  # type: ignore[no-redef]

from .models import MemoryPriority


class MemoryConfig(BaseSettings):
    """
    Configuration for the AgenticFleet memory system.

    Handles all memory-related settings including OpenMemory integration,
    caching policies, and retention rules.
    """

    # OpenMemory MCP Configuration
    openmemory_enabled: bool = Field(default=True, description="Enable OpenMemory MCP integration")
    openmemory_api_key: str | None = Field(default=None, description="OpenMemory API key")
    openmemory_timeout_seconds: int = Field(
        default=30, description="Timeout for OpenMemory operations"
    )

    # Memory Storage Configuration
    memory_cache_ttl_minutes: int = Field(default=30, description="Cache TTL in minutes")
    max_memories_per_context: int = Field(
        default=10, description="Max memories to include in agent context"
    )
    max_memory_size_mb: int = Field(default=100, description="Maximum memory storage size in MB")

    # Memory Retention Policies
    retention_days_conversations: int = Field(
        default=30, description="Days to retain conversation memories"
    )
    retention_days_learning: int = Field(default=90, description="Days to retain learning memories")
    retention_days_patterns: int = Field(default=180, description="Days to retain pattern memories")
    retention_days_errors: int = Field(default=60, description="Days to retain error memories")

    # Memory Type Preferences
    enable_conversation_memories: bool = Field(
        default=True, description="Store conversation history"
    )
    enable_learning_memories: bool = Field(default=True, description="Store learning insights")
    enable_pattern_memories: bool = Field(default=True, description="Store reusable patterns")
    enable_error_memories: bool = Field(default=True, description="Store error solutions")
    enable_context_memories: bool = Field(default=True, description="Store project context")

    # Memory Search Configuration
    default_search_limit: int = Field(default=10, description="Default number of search results")
    min_relevance_threshold: float = Field(
        default=0.6, description="Minimum relevance score for memories"
    )
    enable_semantic_search: bool = Field(default=True, description="Enable semantic memory search")

    # Performance Configuration
    enable_batch_operations: bool = Field(
        default=True, description="Enable batch memory operations"
    )
    max_batch_size: int = Field(default=50, description="Maximum batch size for memory operations")
    enable_background_sync: bool = Field(
        default=True, description="Enable background memory synchronization"
    )

    # Agent-Specific Configuration
    agent_memory_configs: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Agent-specific memory configurations"
    )

    class Config:
        env_prefix = "AGENTICFLEET_MEMORY_"
        env_file = ".env"
        extra = "ignore"

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """
        Get memory configuration for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent-specific memory configuration
        """
        default_config = {
            "enable_memories": True,
            "memory_types": ["conversation", "learning", "error"],
            "max_memories": 5,
            "store_conversations": True,
            "store_learnings": True,
            "store_errors": True,
        }

        return self.agent_memory_configs.get(agent_name, default_config)

    def set_agent_config(self, agent_name: str, config: dict[str, Any]) -> None:
        """
        Set memory configuration for a specific agent.

        Args:
            agent_name: Name of the agent
            config: Agent-specific configuration
        """
        self.agent_memory_configs[agent_name] = config

    def get_retention_days(self, memory_type: str) -> int:
        """
        Get retention period for a specific memory type.

        Args:
            memory_type: Type of memory

        Returns:
            Retention period in days
        """
        retention_map = {
            "conversation": self.retention_days_conversations,
            "learning": self.retention_days_learning,
            "pattern": self.retention_days_patterns,
            "error": self.retention_days_errors,
            "context": self.retention_days_learning,  # Use learning retention for context
            "preference": self.retention_days_learning,  # Use learning retention for preferences
            "tool_usage": self.retention_days_conversations,  # Use conversation retention for tool usage
            "workflow": self.retention_days_patterns,  # Use pattern retention for workflows
        }

        return retention_map.get(memory_type, self.retention_days_conversations)

    def is_memory_type_enabled(self, memory_type: str) -> bool:
        """
        Check if a specific memory type is enabled.

        Args:
            memory_type: Type of memory

        Returns:
            True if memory type is enabled
        """
        enabled_map = {
            "conversation": self.enable_conversation_memories,
            "learning": self.enable_learning_memories,
            "pattern": self.enable_pattern_memories,
            "error": self.enable_error_memories,
            "context": self.enable_context_memories,
            "preference": self.enable_context_memories,  # Group with context
            "tool_usage": self.enable_conversation_memories,  # Group with conversations
            "workflow": self.enable_pattern_memories,  # Group with patterns
        }

        return enabled_map.get(memory_type, True)

    # Priority mapping for different contexts (used by workflow integration)
    priority_map: dict[str, MemoryPriority] = Field(
        default_factory=lambda: {
            "workflow": MemoryPriority.MEDIUM,
            "conversation": MemoryPriority.MEDIUM,
            "learning": MemoryPriority.MEDIUM,
            "pattern": MemoryPriority.HIGH,
            "error": MemoryPriority.HIGH,
        },
        description="Mapping of context keys to default memory priority",
    )


class MemoryPolicy(BaseModel):
    """
    Memory policy configuration for controlling memory behavior.

    Defines rules and policies for memory creation, storage, retrieval,
    and retention to ensure optimal memory system performance.
    """

    # Storage Policies
    max_memories_per_type: dict[str, int] = Field(
        default_factory=lambda: {
            "conversation": 1000,
            "learning": 500,
            "pattern": 200,
            "error": 300,
            "context": 100,
            "preference": 50,
            "tool_usage": 200,
            "workflow": 100,
        },
        description="Maximum memories per type",
    )

    # Creation Policies
    auto_store_conversations: bool = Field(
        default=True, description="Automatically store conversations"
    )
    auto_store_errors: bool = Field(default=True, description="Automatically store errors")
    auto_store_patterns: bool = Field(
        default=False, description="Automatically detect and store patterns"
    )
    require_user_approval_patterns: bool = Field(
        default=True, description="Require user approval for pattern storage"
    )

    # Retrieval Policies
    prioritize_recent_memories: bool = Field(
        default=True, description="Prioritize recent memories in search"
    )
    prioritize_high_access_count: bool = Field(
        default=True, description="Prioritize frequently accessed memories"
    )
    enable_context_boosting: bool = Field(
        default=True, description="Boost memories relevant to current context"
    )

    # Cleanup Policies
    enable_auto_cleanup: bool = Field(default=True, description="Enable automatic memory cleanup")
    cleanup_interval_hours: int = Field(
        default=24, description="Interval between cleanup operations"
    )
    cleanup_threshold_usage_percent: float = Field(
        default=80.0, description="Storage usage threshold for cleanup"
    )

    def should_store_memory(self, memory_type: str, is_pattern: bool = False) -> bool:
        """
        Determine if a memory should be stored based on policy.

        Args:
            memory_type: Type of memory
            is_pattern: Whether this is a detected pattern

        Returns:
            True if memory should be stored
        """
        if is_pattern and not self.auto_store_patterns:
            return False

        if memory_type == "conversation" and not self.auto_store_conversations:
            return False

        return not (memory_type == "error" and not self.auto_store_errors)

    def requires_approval(self, memory_type: str, is_pattern: bool = False) -> bool:
        """
        Check if storing a memory requires user approval.

        Args:
            memory_type: Type of memory
            is_pattern: Whether this is a detected pattern

        Returns:
            True if approval is required
        """
        return is_pattern and self.require_user_approval_patterns


# Global configuration instance
memory_config = MemoryConfig()
memory_policy = MemoryPolicy()
