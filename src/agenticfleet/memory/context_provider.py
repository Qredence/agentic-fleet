"""
Memory Context Provider - Integrates memories into agent conversations.

Provides contextual memory retrieval and injection for Microsoft Agent Framework
agents, ensuring relevant memories are available during reasoning and execution.
"""

import logging
from typing import Any

from .manager import MemoryManager
from .models import Memory, MemoryPriority, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)

# Try to import ContextProvider from agent framework, fallback to Any
try:
    from agent_framework_core import ContextProvider  # type: ignore[import-not-found]
except ImportError:
    ContextProvider = Any


class MemoryContextProvider(ContextProvider):  # type: ignore[misc]
    """
    Context provider that injects relevant memories into agent conversations.

    Retrieves and formats memories based on current conversation context,
    ensuring agents have access to relevant historical information.
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        max_memories_per_context: int = 10,
        memory_types: list[MemoryType] | None = None,
        enable_learning_memories: bool = True,
        enable_context_memories: bool = True,
        enable_error_memories: bool = True,
    ):
        """
        Initialize the memory context provider.

        Args:
            memory_manager: Memory manager instance
            max_memories_per_context: Maximum memories to include in context
            memory_types: Types of memories to include (None = all)
            enable_learning_memories: Include learning/pattern memories
            enable_context_memories: Include project context memories
            enable_error_memories: Include error/solution memories
        """
        self.memory_manager = memory_manager
        self.max_memories_per_context = max_memories_per_context
        self.memory_types = memory_types
        self.enable_learning_memories = enable_learning_memories
        self.enable_context_memories = enable_context_memories
        self.enable_error_memories = enable_error_memories

    async def get_context(
        self,
        conversation_id: str | None = None,
        agent_name: str | None = None,
        current_message: str | None = None,
        workflow_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get contextual memories for the current conversation.

        Args:
            conversation_id: Current conversation ID
            agent_name: Name of the current agent
            current_message: Current message/content for relevance matching
            workflow_state: Current workflow state for context

        Returns:
            Dictionary containing contextual memories
        """
        try:
            # Build memory query
            memory_types = self._determine_memory_types(agent_name, workflow_state)

            query = MemoryQuery(
                query=current_message or "current conversation context",
                memory_types=memory_types,
                conversation_id=conversation_id,
                agent_filter=agent_name,
                limit=self.max_memories_per_context,
                min_relevance_score=0.6,
            )

            # Retrieve relevant memories
            search_result = await self.memory_manager.retrieve_memories(query)

            # Format memories for context
            context_data = {
                "memories": self._format_memories_for_context(search_result.memories),
                "memory_count": len(search_result.memories),
                "query_time_ms": search_result.query_time_ms,
                "conversation_id": conversation_id,
                "agent_name": agent_name,
            }

            logger.debug(f"Provided {len(search_result.memories)} memories for context")
            return context_data

        except Exception as e:
            logger.error(f"Failed to get memory context: {e}")
            return {
                "memories": [],
                "memory_count": 0,
                "error": str(e),
                "conversation_id": conversation_id,
                "agent_name": agent_name,
            }

    async def store_conversation_memory(
        self,
        conversation_id: str,
        agent_name: str,
        message: str,
        response: str,
        context_type: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Store conversation interaction as memory.

        Args:
            conversation_id: Conversation identifier
            agent_name: Agent that generated the response
            message: User message
            response: Agent response
            context_type: Type of context/memory
            metadata: Additional metadata

        Returns:
            Memory ID if stored successfully
        """
        try:
            # Create memory content
            content = f"User: {message}\n\nAgent ({agent_name}): {response}"

            # Determine memory type
            memory_type = MemoryType.CONVERSATION
            if "error" in message.lower() or "error" in response.lower():
                memory_type = MemoryType.ERROR
            elif "learning" in message.lower() or "learned" in response.lower():
                memory_type = MemoryType.LEARNING

            # Extract keywords from message
            keywords = self._extract_keywords(message + " " + response)

            # Store memory
            memory_id = await self.memory_manager.store_memory(
                title=f"Conversation - {agent_name} - {context_type}",
                content=content,
                memory_type=memory_type,
                context_keywords=keywords,
                metadata={
                    "conversation_id": conversation_id,
                    "agent_name": agent_name,
                    "context_type": context_type,
                    "message_length": len(message),
                    "response_length": len(response),
                    **(metadata or {}),
                },
                source_agent=agent_name,
                conversation_id=conversation_id,
            )

            logger.debug(f"Stored conversation memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store conversation memory: {e}")
            return None

    async def store_learning_memory(
        self,
        agent_name: str,
        learning: str,
        context: str | None = None,
        importance_level: str = "medium",
        tags: list[str] | None = None,
    ) -> str | None:
        """
        Store a learning insight as memory.

        Args:
            agent_name: Agent that had this learning
            learning: The learning insight
            context: Context where learning occurred
            importance_level: Importance of this learning
            tags: Tags for categorization

        Returns:
            Memory ID if stored successfully
        """
        try:
            # Map importance to priority
            priority_map = {
                "critical": MemoryPriority.CRITICAL,
                "high": MemoryPriority.HIGH,
                "medium": MemoryPriority.MEDIUM,
                "low": MemoryPriority.LOW,
            }
            priority = priority_map.get(importance_level.lower(), MemoryPriority.MEDIUM)

            # Create content
            content = learning
            if context:
                content = f"Context: {context}\n\nLearning: {learning}"

            # Extract keywords
            keywords = self._extract_keywords(learning + " " + (context or ""))

            # Store memory
            memory_id = await self.memory_manager.store_memory(
                title=f"Learning - {agent_name}",
                content=content,
                memory_type=MemoryType.LEARNING,
                priority=priority,
                context_keywords=keywords + (tags or []),
                metadata={
                    "agent_name": agent_name,
                    "importance_level": importance_level,
                    "has_context": context is not None,
                },
                source_agent=agent_name,
            )

            logger.info(f"Stored learning memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store learning memory: {e}")
            return None

    async def store_pattern_memory(
        self,
        agent_name: str,
        pattern_name: str,
        pattern_description: str,
        usage_example: str | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        """
        Store a reusable pattern as memory.

        Args:
            agent_name: Agent documenting this pattern
            pattern_name: Name of the pattern
            pattern_description: Description of how to apply the pattern
            usage_example: Example of pattern usage
            tags: Tags for pattern categorization

        Returns:
            Memory ID if stored successfully
        """
        try:
            # Create content
            content = f"Pattern: {pattern_name}\n\nDescription: {pattern_description}"
            if usage_example:
                content += f"\n\nExample:\n{usage_example}"

            # Extract keywords
            keywords = self._extract_keywords(pattern_name + " " + pattern_description)
            keywords.extend(["pattern", "reusable", "workflow"])
            if tags:
                keywords.extend(tags)

            # Store memory
            memory_id = await self.memory_manager.store_memory(
                title=f"Pattern - {pattern_name}",
                content=content,
                memory_type=MemoryType.PATTERN,
                priority=MemoryPriority.HIGH,  # Patterns are usually valuable
                context_keywords=keywords,
                metadata={
                    "agent_name": agent_name,
                    "pattern_name": pattern_name,
                    "has_example": usage_example is not None,
                },
                source_agent=agent_name,
            )

            logger.info(f"Stored pattern memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store pattern memory: {e}")
            return None

    async def store_error_memory(
        self,
        agent_name: str,
        error_description: str,
        solution: str,
        error_type: str | None = None,
        context: str | None = None,
    ) -> str | None:
        """
        Store error and solution as memory for future reference.

        Args:
            agent_name: Agent that encountered/resolved the error
            error_description: Description of the error
            solution: How the error was resolved
            error_type: Type/category of error
            context: Context where error occurred

        Returns:
            Memory ID if stored successfully
        """
        try:
            # Create content
            content = f"Error: {error_description}\n\nSolution: {solution}"
            if context:
                content = f"Context: {context}\n\n{content}"
            if error_type:
                content = f"Error Type: {error_type}\n\n{content}"

            # Extract keywords
            keywords = self._extract_keywords(error_description + " " + solution)
            keywords.extend(["error", "solution", "troubleshooting"])

            # Store memory
            memory_id = await self.memory_manager.store_memory(
                title=f"Error Solution - {error_type or 'Unknown'}",
                content=content,
                memory_type=MemoryType.ERROR,
                priority=MemoryPriority.HIGH,  # Error solutions are valuable
                context_keywords=keywords,
                metadata={
                    "agent_name": agent_name,
                    "error_type": error_type,
                    "has_context": context is not None,
                },
                source_agent=agent_name,
            )

            logger.info(f"Stored error memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store error memory: {e}")
            return None

    # Private helper methods

    def _determine_memory_types(
        self,
        agent_name: str | None,
        workflow_state: dict[str, Any] | None,
    ) -> list[MemoryType]:
        """Determine which memory types to include based on context."""
        if self.memory_types:
            return self.memory_types

        memory_types = [MemoryType.CONVERSATION]  # Always include conversations

        if self.enable_learning_memories:
            memory_types.extend([MemoryType.LEARNING, MemoryType.PATTERN])

        if self.enable_context_memories:
            memory_types.append(MemoryType.CONTEXT)

        if self.enable_error_memories:
            memory_types.append(MemoryType.ERROR)

        return memory_types

    def _format_memories_for_context(self, memories: list[Memory]) -> list[dict[str, Any]]:
        """Format memories for inclusion in agent context."""
        formatted = []

        for memory in memories:
            formatted_memory = {
                "id": memory.id,
                "type": memory.type.value,
                "title": memory.title,
                "content": memory.content,
                "priority": memory.priority.value,
                "keywords": memory.context_keywords,
                "created_at": memory.metadata.created_at.isoformat(),
                "access_count": memory.metadata.access_count,
                "source_agent": memory.metadata.source_agent,
            }

            formatted.append(formatted_memory)

        return formatted

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text."""
        # Simple keyword extraction - in production, use more sophisticated NLP
        import re

        # Remove common words and extract meaningful terms
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

        # Extract words and clean them
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Filter out common words and deduplicate
        keywords = list(set(word for word in words if word not in common_words))

        # Return top keywords (limit for practicality)
        return keywords[:10]
