"""
Memory Manager - Core interface for AgenticFleet memory system.

Provides high-level operations for storing, retrieving, and managing memories
through the OpenMemory MCP server integration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from ..memory.models import (
    Memory,
    MemoryBatch,
    MemoryMetadata,
    MemoryPriority,
    MemoryQuery,
    MemorySearchResult,
    MemoryStats,
    MemoryType,
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Main memory management interface for AgenticFleet.

    Integrates with OpenMemory MCP server to provide persistent storage
    and intelligent retrieval of agent memories.
    """

    def __init__(self, mcp_client: Any | None = None):
        """
        Initialize the Memory Manager.

        Args:
            mcp_client: MCP client instance for OpenMemory communication
        """
        self.mcp_client = mcp_client
        self._memory_cache: dict[str, Memory] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._stats = {"stores": 0, "retrievals": 0, "cache_hits": 0, "cache_misses": 0}

    async def initialize(self) -> None:
        """Initialize memory manager and test OpenMemory connection."""
        if not self.mcp_client:
            logger.warning("No MCP client provided - memory operations will be local only")
            return

        try:
            # Test OpenMemory connection
            await self._test_connection()
            logger.info("Memory manager initialized successfully with OpenMemory")
        except Exception as e:
            logger.error(f"Failed to initialize OpenMemory: {e}")
            # Continue with local-only mode

    async def store_memory(
        self,
        title: str,
        content: str,
        memory_type: MemoryType,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        context_keywords: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        source_agent: str | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """
        Store a new memory in the system.

        Args:
            title: Brief descriptive title
            content: Memory content/details
            memory_type: Type of memory being stored
            priority: Importance level for retrieval
            context_keywords: Keywords for context matching
            metadata: Additional metadata
            source_agent: Agent that created this memory
            conversation_id: Related conversation ID

        Returns:
            Memory ID for the stored memory
        """
        memory_id = f"mem_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000:04d}"

        # Create metadata - avoid passing duplicate keys from metadata dict
        safe_meta = dict(metadata or {})
        for k in [
            "created_at",
            "updated_at",
            "access_count",
            "last_accessed",
            "tags",
            "source_agent",
            "conversation_id",
            "workflow_id",
            "relevance_score",
        ]:
            safe_meta.pop(k, None)

        memory_metadata = MemoryMetadata(
            created_at=datetime.utcnow(),
            tags=context_keywords or [],
            source_agent=source_agent,
            conversation_id=conversation_id,
            relevance_score=1.0,
            **safe_meta,
        )

        # Create memory object
        memory = Memory(
            id=memory_id,
            type=memory_type,
            title=title,
            content=content,
            metadata=memory_metadata,
            priority=priority,
            context_keywords=context_keywords or [],
        )

        # Store in cache
        self._memory_cache[memory_id] = memory

        # Store in OpenMemory if available
        if self.mcp_client:
            try:
                await self._store_to_openmemory(memory)
                self._stats["stores"] += 1
                logger.debug(f"Stored memory {memory_id} to OpenMemory")
            except Exception as e:
                logger.error(f"Failed to store memory {memory_id} to OpenMemory: {e}")

        logger.info(f"Stored memory: {title} ({memory_type})")
        return memory_id

    async def retrieve_memories(
        self,
        query: str | MemoryQuery,
        memory_types: list[MemoryType] | None = None,
        limit: int = 10,
        conversation_id: str | None = None,
    ) -> MemorySearchResult:
        """
        Retrieve memories relevant to the query.

        Args:
            query: Search query or structured query object
            memory_types: Filter by memory types
            limit: Maximum number of results
            conversation_id: Filter by conversation

        Returns:
            Search results with relevant memories
        """
        start_time = datetime.utcnow()

        # Normalize query
        if isinstance(query, str):
            query_obj = MemoryQuery(
                query=query,
                memory_types=memory_types or [],
                limit=limit,
                conversation_id=conversation_id,
            )
        else:
            query_obj = query

        # Check cache first
        cached_results = self._search_cache(query_obj)
        if cached_results:
            self._stats["cache_hits"] += 1
            query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return MemorySearchResult(
                memories=cached_results,
                total_found=len(cached_results),
                query_time_ms=query_time_ms,
                relevance_threshold=0.5,
            )

        self._stats["cache_misses"] += 1

        # Search in OpenMemory if available
        if self.mcp_client:
            try:
                results = await self._search_openmemory(query_obj)
                self._stats["retrievals"] += 1

                # Update cache with results
                for memory in results.memories:
                    self._memory_cache[memory.id] = memory

                query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                return results
            except Exception as e:
                logger.error(f"Failed to search OpenMemory: {e}")

        # Fallback to local cache search
        local_results = self._search_local_cache(query_obj)
        query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return MemorySearchResult(
            memories=local_results,
            total_found=len(local_results),
            query_time_ms=query_time_ms,
            relevance_threshold=0.5,
        )

    async def update_memory(
        self,
        memory_id: str,
        title: str | None = None,
        content: str | None = None,
        priority: MemoryPriority | None = None,
        context_keywords: list[str] | None = None,
    ) -> bool:
        """
        Update an existing memory.

        Args:
            memory_id: ID of memory to update
            title: New title (optional)
            content: New content (optional)
            priority: New priority (optional)
            context_keywords: New keywords (optional)

        Returns:
            True if updated successfully
        """
        # Get existing memory
        memory = self._memory_cache.get(memory_id)
        if not memory:
            logger.warning(f"Memory {memory_id} not found for update")
            return False

        # Update fields
        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if priority is not None:
            memory.priority = priority
        if context_keywords is not None:
            memory.context_keywords = context_keywords

        # Update metadata
        memory.metadata.updated_at = datetime.utcnow()
        memory.metadata.access_count += 1
        memory.metadata.last_accessed = datetime.utcnow()

        # Update in OpenMemory if available
        if self.mcp_client:
            try:
                await self._update_in_openmemory(memory)
                logger.debug(f"Updated memory {memory_id} in OpenMemory")
            except Exception as e:
                logger.error(f"Failed to update memory {memory_id} in OpenMemory: {e}")

        logger.info(f"Updated memory: {memory.title}")
        return True

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the system.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        # Remove from cache
        if memory_id in self._memory_cache:
            del self._memory_cache[memory_id]

        # Delete from OpenMemory if available
        if self.mcp_client:
            try:
                await self._delete_from_openmemory(memory_id)
                logger.debug(f"Deleted memory {memory_id} from OpenMemory")
            except Exception as e:
                logger.error(f"Failed to delete memory {memory_id} from OpenMemory: {e}")

        logger.info(f"Deleted memory: {memory_id}")
        return True

    async def get_memory_stats(self) -> MemoryStats:
        """
        Get statistics about memory usage.

        Returns:
            Memory statistics
        """
        memories = list(self._memory_cache.values())

        # Count by type
        memories_by_type = {}
        for memory_type in MemoryType:
            memories_by_type[memory_type] = len([m for m in memories if m.type == memory_type])

        # Count by priority
        memories_by_priority = {}
        for priority in MemoryPriority:
            memories_by_priority[priority] = len([m for m in memories if m.priority == priority])

        # Calculate average access count
        avg_access = (
            sum(m.metadata.access_count for m in memories) / len(memories) if memories else 0
        )

        # Most accessed memories
        most_accessed = sorted(memories, key=lambda m: m.metadata.access_count, reverse=True)[:10]
        most_accessed_ids = [m.id for m in most_accessed]

        # Recently created (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(days=1)
        recently_created = [m.id for m in memories if m.metadata.created_at > recent_cutoff]

        # Estimate storage usage
        storage_usage = sum(len(json.dumps(m.dict(), default=str)) for m in memories) / (
            1024 * 1024
        )

        return MemoryStats(
            total_memories=len(memories),
            memories_by_type=memories_by_type,
            memories_by_priority=memories_by_priority,
            average_access_count=avg_access,
            most_accessed_memories=most_accessed_ids,
            recently_created=recently_created,
            storage_usage_mb=storage_usage,
        )

    async def batch_operations(self, batch: MemoryBatch) -> list[str]:
        """
        Perform batch memory operations.

        Args:
            batch: Batch operation details

        Returns:
            List of memory IDs affected
        """
        results = []

        if batch.operation == "store":
            for memory in batch.memories:
                memory_id = await self.store_memory(
                    title=memory.title,
                    content=memory.content,
                    memory_type=memory.type,
                    priority=memory.priority,
                    context_keywords=memory.context_keywords,
                    metadata=memory.metadata.dict(),
                    source_agent=memory.metadata.source_agent,
                    conversation_id=memory.metadata.conversation_id,
                )
                results.append(memory_id)

        elif batch.operation == "update":
            for memory in batch.memories:
                success = await self.update_memory(
                    memory_id=memory.id,
                    title=memory.title,
                    content=memory.content,
                    priority=memory.priority,
                    context_keywords=memory.context_keywords,
                )
                if success:
                    results.append(memory.id)

        elif batch.operation == "delete":
            for memory in batch.memories:
                success = await self.delete_memory(memory.id)
                if success:
                    results.append(memory.id)

        logger.info(f"Batch {batch.operation} completed: {len(results)} memories processed")
        return results

    # Private methods for OpenMemory integration

    async def _test_connection(self) -> None:
        """Test connection to OpenMemory MCP server."""
        if not self.mcp_client:
            raise RuntimeError("No MCP client available")

        # Implementation depends on MCP client interface
        # This would typically call a test or ping method
        # Try a lightweight call to ensure client works
        try:
            if hasattr(self.mcp_client, "call_tool"):
                await self.mcp_client.call_tool("get_stats", {})
            else:
                # No canonical test method available; assume connected
                return
        except Exception as e:
            logger.error(f"OpenMemory test connection failed: {e}")
            raise

    async def _store_to_openmemory(self, memory: Memory) -> None:
        """Store memory using OpenMemory MCP server."""
        if not self.mcp_client:
            return

        # Implementation depends on OpenMemory MCP interface
        # This would convert the memory to the expected format and store it
        # Convert memory to dict expected by MockMCPClient.call_tool
        payload = {
            "memory_id": memory.id,
            "title": memory.title,
            "content": memory.content,
            "type": memory.type.value,
            "priority": memory.priority.value,
            "metadata": memory.metadata.dict(),
            "context_keywords": memory.context_keywords,
        }

        if hasattr(self.mcp_client, "call_tool"):
            await self.mcp_client.call_tool("store_memory", payload)
        else:
            # If client uses direct methods, try store_memory
            store = getattr(self.mcp_client, "store_memory", None)
            if callable(store):
                await store(payload)

    async def _search_openmemory(self, query: MemoryQuery) -> MemorySearchResult:
        """Search memories using OpenMemory MCP server."""
        if not self.mcp_client:
            return MemorySearchResult(
                memories=[], total_found=0, query_time_ms=0, relevance_threshold=0.5
            )

        # Implementation depends on OpenMemory MCP interface
        # This would perform semantic search and return results
        # Build params in the shape expected by MockMCPClient
        base_params = {
            "limit": query.limit,
            "memory_types": [t.value for t in query.memory_types] if query.memory_types else [],
            "conversation_id": query.conversation_id,
        }

        # Prepare candidate queries (try more specific to more general)
        raw = (query.query or "").strip()
        tokens = [t for t in raw.split() if t.isalnum()]
        candidates = [raw]
        if len(tokens) >= 2:
            candidates.append(" ".join(tokens[:2]))
        if tokens:
            candidates.append(tokens[0])
        # Also try significant tokens (longer keywords) to increase match chance
        significant = [t for t in tokens if len(t) > 3]
        for t in significant:
            if t not in candidates:
                candidates.append(t)

        resp: dict[str, Any] = {"memories": [], "total_found": 0}
        # Call the MCP client with several candidate query strings to increase match chance
        for qstr in candidates:
            params = {**base_params, "query": qstr}
            if hasattr(self.mcp_client, "call_tool"):
                try:
                    call_result = await self.mcp_client.call_tool("search_memories", params)
                    if isinstance(call_result, dict):
                        resp = call_result
                except Exception:
                    resp = {"memories": [], "total_found": 0}
            else:
                search = getattr(self.mcp_client, "search_memories", None)
                if callable(search):
                    try:
                        call_result = await search(params)
                        if isinstance(call_result, dict):
                            resp = call_result
                    except Exception:
                        resp = {"memories": [], "total_found": 0}
                else:
                    resp = {"memories": [], "total_found": 0}

            if resp.get("memories"):
                break

        memories = []
        memories_list = resp.get("memories", [])
        if isinstance(memories_list, list):
            for item in memories_list:
                if isinstance(item, dict):
                    # Normalize fields from mock
                    mem_id = item.get("memory_id") or item.get("id") or item.get("id")
                    # Build metadata safely
                    meta = item.get("metadata") or {}
                    # Avoid passing duplicate conversation_id in both metadata and as kwarg
                    mm = MemoryMetadata(
                        created_at=datetime.utcnow(),
                        tags=meta.get("tags", []),
                        source_agent=meta.get("source_agent"),
                        conversation_id=meta.get("conversation_id") or item.get("conversation_id"),
                        relevance_score=float(meta.get("relevance_score", 1.0)),
                    )

                    m = Memory(
                        id=mem_id or f"mem_{hash(item.get('content', '')) % 10000}",
                        type=MemoryType(
                            item.get("type") if item.get("type") else MemoryType.LEARNING.value
                        ),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        metadata=mm,
                        priority=MemoryPriority(
                            item.get("priority")
                            if item.get("priority")
                            else MemoryPriority.MEDIUM.value
                        ),
                        context_keywords=item.get("context_keywords", []) or item.get("tags", []),
                    )
                    memories.append(m)

        total = resp.get("total_found", len(memories))
        if not isinstance(total, int):
            total = len(memories)
        # Rough query time placeholder
        return MemorySearchResult(
            memories=memories, total_found=total, query_time_ms=10.0, relevance_threshold=0.5
        )

    async def _update_in_openmemory(self, memory: Memory) -> None:
        """Update memory using OpenMemory MCP server."""
        if not self.mcp_client:
            return

        # Implementation depends on OpenMemory MCP interface
        payload = {
            "memory_id": memory.id,
            "title": memory.title,
            "content": memory.content,
            "metadata": memory.metadata.dict(),
        }

        if hasattr(self.mcp_client, "call_tool"):
            await self.mcp_client.call_tool("update_memory", payload)
        else:
            upd = getattr(self.mcp_client, "update_memory", None)
            if callable(upd):
                await upd(payload)

    async def _delete_from_openmemory(self, memory_id: str) -> None:
        """Delete memory using OpenMemory MCP server."""
        if not self.mcp_client:
            return

        # Implementation depends on OpenMemory MCP interface
        params = {"memory_id": memory_id}
        if hasattr(self.mcp_client, "call_tool"):
            await self.mcp_client.call_tool("delete_memory", params)
        else:
            delete = getattr(self.mcp_client, "delete_memory", None)
            if callable(delete):
                await delete(params)

    # Private methods for local cache management

    def _search_cache(self, query: MemoryQuery) -> list[Memory] | None:
        """Search local memory cache."""
        memories = list(self._memory_cache.values())

        # Filter by memory types
        if query.memory_types:
            memories = [m for m in memories if m.type in query.memory_types]

        # Filter by priority
        if query.priority_filter:
            memories = [m for m in memories if m.priority == query.priority_filter]

        # Filter by conversation
        if query.conversation_id:
            memories = [m for m in memories if m.metadata.conversation_id == query.conversation_id]

        # Simple keyword matching (in real implementation, use semantic search)
        query_lower = query.query.lower()
        relevant_memories = []

        for memory in memories:
            # Search in title, content, and keywords
            searchable_text = (
                f"{memory.title} {memory.content} {' '.join(memory.context_keywords)}".lower()
            )
            if query_lower in searchable_text:
                relevant_memories.append(memory)

        # Sort by priority and relevance
        priority_order = {
            MemoryPriority.CRITICAL: 0,
            MemoryPriority.HIGH: 1,
            MemoryPriority.MEDIUM: 2,
            MemoryPriority.LOW: 3,
            MemoryPriority.ARCHIVE: 4,
        }
        relevant_memories.sort(
            key=lambda m: (priority_order[m.priority], -m.metadata.relevance_score)
        )

        return relevant_memories[: query.limit]

    def _search_local_cache(self, query: MemoryQuery) -> list[Memory]:
        """Search local cache when OpenMemory is unavailable."""
        return self._search_cache(query) or []

    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        cutoff = datetime.utcnow() - self._cache_ttl
        expired_ids = [
            memory_id
            for memory_id, memory in self._memory_cache.items()
            if memory.metadata.created_at < cutoff
        ]

        for memory_id in expired_ids:
            del self._memory_cache[memory_id]

        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired cache entries")
