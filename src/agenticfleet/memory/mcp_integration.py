"""
OpenMemory MCP Server Integration

Provides the actual integration layer with the OpenMemory MCP server for persistent
memory storage and retrieval operations.
"""

import logging
from typing import Any

from .models import Memory, MemoryQuery, MemorySearchResult

logger = logging.getLogger(__name__)


class OpenMemoryMCPIntegration:
    """
    Integration layer for OpenMemory MCP server.

    Handles the actual communication with the OpenMemory MCP server for
    storing, retrieving, and managing persistent memories.
    """

    def __init__(self, mcp_client: Any):
        """
        Initialize the OpenMemory integration.

        Args:
            mcp_client: MCP client instance for OpenMemory communication
        """
        self.mcp_client = mcp_client
        self._connected = False

    async def initialize(self) -> bool:
        """
        Initialize the OpenMemory connection.

        Returns:
            True if connection successful
        """
        try:
            # Test connection by listing available memories
            await self._list_memories(limit=1)
            self._connected = True
            logger.info("OpenMemory MCP integration initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenMemory MCP integration: {e}")
            self._connected = False
            return False

    async def store_memory(self, memory: Memory) -> str:
        """
        Store a memory in OpenMemory.

        Args:
            memory: Memory object to store

        Returns:
            Memory ID from OpenMemory
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            # Convert memory to OpenMemory format
            openmemory_data = {
                "title": memory.title,
                "content": memory.content,
                "tags": memory.context_keywords,
                "metadata": {
                    "type": memory.type.value,
                    "priority": memory.priority.value,
                    "source_agent": memory.metadata.source_agent,
                    "conversation_id": memory.metadata.conversation_id,
                    "workflow_id": memory.metadata.workflow_id,
                    "created_at": memory.metadata.created_at.isoformat(),
                    "access_count": memory.metadata.access_count,
                    "relevance_score": memory.metadata.relevance_score,
                },
            }

            # Store using OpenMemory MCP
            call_result = await self._call_openmemory("store_memory", openmemory_data)

            if call_result is not None and "memory_id" in call_result:
                memory_id_value = call_result["memory_id"]
                if isinstance(memory_id_value, str):
                    logger.debug(f"Stored memory {memory.id} in OpenMemory as {memory_id_value}")
                    return memory_id_value
                else:
                    raise ValueError("Invalid memory_id type from OpenMemory store_memory")
            else:
                raise ValueError("Invalid response from OpenMemory store_memory")

        except Exception as e:
            logger.error(f"Failed to store memory in OpenMemory: {e}")
            raise

    async def search_memories(self, query: MemoryQuery) -> MemorySearchResult:
        """
        Search for memories in OpenMemory.

        Args:
            query: Search query parameters

        Returns:
            Search results from OpenMemory
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            import time

            start_time = time.time()

            # Convert query to OpenMemory format
            filters: dict[str, Any] = {}
            search_params = {
                "query": query.query,
                "limit": query.limit,
                "tags": query.context_keywords,
                "filters": filters,
            }

            # Add optional filters
            if query.memory_types:
                filters["type"] = [t.value for t in query.memory_types]

            if query.priority_filter:
                filters["priority"] = query.priority_filter.value

            if query.conversation_id:
                filters["conversation_id"] = query.conversation_id

            if query.agent_filter:
                filters["source_agent"] = query.agent_filter

            # Prepare candidate queries (try specific -> general) to improve matching
            raw_q = (query.query or "").strip()
            tokens = [t for t in raw_q.split() if t.isalnum()]
            candidates = [raw_q]
            if len(tokens) >= 2:
                candidates.append(" ".join(tokens[:2]))
            if tokens:
                candidates.append(tokens[0])

            result: dict[str, Any] = {"memories": [], "total_found": 0}
            for qstr in candidates:
                search_params["query"] = qstr
                call_result = await self._call_openmemory("search_memories", search_params)
                if call_result is not None and isinstance(call_result, dict):
                    result = call_result
                    if result.get("memories"):
                        break

            query_time = (time.time() - start_time) * 1000

            if result and "memories" in result:
                # Convert OpenMemory results back to our format
                memories = []
                memories_list = result["memories"]
                if isinstance(memories_list, list):
                    for mem_data in memories_list:
                        if isinstance(mem_data, dict):
                            memory = self._convert_from_openmemory(mem_data)
                            memories.append(memory)

                total_found = result.get("total_found", len(memories))
                if not isinstance(total_found, int):
                    total_found = len(memories)

                return MemorySearchResult(
                    memories=memories,
                    total_found=total_found,
                    query_time_ms=query_time,
                    relevance_threshold=query.min_relevance_score,
                )
            else:
                logger.warning("No memories found in OpenMemory search")
                return MemorySearchResult(
                    memories=[],
                    total_found=0,
                    query_time_ms=query_time,
                    relevance_threshold=query.min_relevance_score,
                )

        except Exception as e:
            logger.error(f"Failed to search memories in OpenMemory: {e}")
            # Return empty results rather than raising
            return MemorySearchResult(
                memories=[],
                total_found=0,
                query_time_ms=0,
                relevance_threshold=0.5,
            )

    async def update_memory(self, memory: Memory) -> bool:
        """
        Update a memory in OpenMemory.

        Args:
            memory: Updated memory object

        Returns:
            True if updated successfully
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            # Convert memory to OpenMemory format
            update_data = {
                "memory_id": memory.id,
                "title": memory.title,
                "content": memory.content,
                "tags": memory.context_keywords,
                "metadata": {
                    "type": memory.type.value,
                    "priority": memory.priority.value,
                    "updated_at": (
                        memory.metadata.updated_at.isoformat()
                        if memory.metadata.updated_at
                        else None
                    ),
                    "access_count": memory.metadata.access_count,
                    "last_accessed": (
                        memory.metadata.last_accessed.isoformat()
                        if memory.metadata.last_accessed
                        else None
                    ),
                    "relevance_score": memory.metadata.relevance_score,
                },
            }

            # Update using OpenMemory MCP
            call_result = await self._call_openmemory("update_memory", update_data)

            if call_result is not None and "success" in call_result:
                success_value = call_result["success"]
                if isinstance(success_value, bool):
                    logger.debug(f"Updated memory {memory.id} in OpenMemory")
                    return success_value
                else:
                    raise ValueError("Invalid success value type from OpenMemory update_memory")
            else:
                raise ValueError("Invalid response from OpenMemory update_memory")

        except Exception as e:
            logger.error(f"Failed to update memory in OpenMemory: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from OpenMemory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            # Delete using OpenMemory MCP
            call_result = await self._call_openmemory("delete_memory", {"memory_id": memory_id})

            if call_result is not None and "success" in call_result:
                success_value = call_result["success"]
                if isinstance(success_value, bool):
                    logger.debug(f"Deleted memory {memory_id} from OpenMemory")
                    return success_value
                else:
                    raise ValueError("Invalid success value type from OpenMemory delete_memory")
            else:
                raise ValueError("Invalid response from OpenMemory delete_memory")

        except Exception as e:
            logger.error(f"Failed to delete memory from OpenMemory: {e}")
            return False

    async def list_memories(self, limit: int = 50, offset: int = 0) -> list[Memory]:
        """
        List memories from OpenMemory.

        Args:
            limit: Maximum number of memories to return
            offset: Number of memories to skip

        Returns:
            List of memories
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            # List using OpenMemory MCP
            call_result = await self._call_openmemory(
                "list_memories",
                {
                    "limit": limit,
                    "offset": offset,
                },
            )

            if call_result is not None and "memories" in call_result:
                memories_list = call_result["memories"]
                if isinstance(memories_list, list):
                    memories = []
                    for mem_data in memories_list:
                        if isinstance(mem_data, dict):
                            memory = self._convert_from_openmemory(mem_data)
                            memories.append(memory)
                    return memories
                else:
                    return []
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to list memories from OpenMemory: {e}")
            return []

    async def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory statistics from OpenMemory.

        Returns:
            Memory statistics
        """
        if not self._connected:
            raise RuntimeError("OpenMemory MCP not connected")

        try:
            # Get stats using OpenMemory MCP
            call_result = await self._call_openmemory("get_stats", {})

            if call_result is not None and isinstance(call_result, dict):
                return call_result
            else:
                return {}

        except Exception as e:
            logger.error(f"Failed to get memory stats from OpenMemory: {e}")
            return {}

    # Private helper methods

    async def _call_openmemory(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """
        Call OpenMemory MCP server method.

        Args:
            method: Method name to call
            params: Parameters for the method

        Returns:
            Response from OpenMemory
        """
        try:
            # This depends on the actual MCP client interface
            # The implementation will vary based on how the MCP client works

            # Example implementation (adjust based on actual MCP client):
            if hasattr(self.mcp_client, "call_tool"):
                result: dict[str, Any] = await self.mcp_client.call_tool(method, params)
                return result
            elif hasattr(self.mcp_client, "request"):
                # Alternative interface
                result = await self.mcp_client.request(method, params)
                return result
            else:
                # Fallback - you'll need to implement this based on your MCP client
                logger.warning(f"Unknown MCP client interface for method: {method}")
                return None

        except Exception as e:
            logger.error(f"OpenMemory MCP call failed for {method}: {e}")
            raise

    async def _list_memories(self, limit: int = 1) -> dict[str, Any] | None:
        """
        Helper method to test connection by listing a few memories.

        Args:
            limit: Number of memories to list

        Returns:
            List result from OpenMemory
        """
        return await self._call_openmemory("list_memories", {"limit": limit})

    def _convert_from_openmemory(self, mem_data: dict[str, Any]) -> Memory:
        """
        Convert OpenMemory format to our Memory model.

        Args:
            mem_data: Memory data from OpenMemory

        Returns:
            Memory object
        """
        from datetime import datetime

        from .models import MemoryMetadata, MemoryPriority, MemoryType

        # Extract metadata
        metadata_dict = mem_data.get("metadata", {})

        # Parse dates
        created_at = datetime.fromisoformat(
            metadata_dict.get("created_at", datetime.utcnow().isoformat())
        )
        updated_at = None
        if metadata_dict.get("updated_at"):
            updated_at = datetime.fromisoformat(metadata_dict["updated_at"])
        last_accessed = None
        if metadata_dict.get("last_accessed"):
            last_accessed = datetime.fromisoformat(metadata_dict["last_accessed"])

        # Create metadata object
        metadata = MemoryMetadata(
            created_at=created_at,
            updated_at=updated_at,
            access_count=metadata_dict.get("access_count", 0),
            last_accessed=last_accessed,
            tags=mem_data.get("tags", []),
            source_agent=metadata_dict.get("source_agent"),
            conversation_id=metadata_dict.get("conversation_id"),
            workflow_id=metadata_dict.get("workflow_id"),
            relevance_score=metadata_dict.get("relevance_score", 1.0),
        )

        # Convert type and priority
        memory_type = MemoryType(metadata_dict.get("type", "conversation"))
        priority = MemoryPriority(metadata_dict.get("priority", "medium"))

        # Create and return memory
        return Memory(
            id=mem_data.get("memory_id", ""),
            type=memory_type,
            title=mem_data.get("title", ""),
            content=mem_data.get("content", ""),
            metadata=metadata,
            priority=priority,
            context_keywords=mem_data.get("tags", []),
            related_memories=mem_data.get("related_memories", []),
        )

    def _convert_to_openmemory(self, memory: Memory) -> dict[str, Any]:
        """
        Convert our Memory model to OpenMemory format.

        Args:
            memory: Memory object to convert

        Returns:
            OpenMemory format data
        """
        return {
            "memory_id": memory.id,
            "title": memory.title,
            "content": memory.content,
            "tags": memory.context_keywords,
            "metadata": {
                "type": memory.type.value,
                "priority": memory.priority.value,
                "source_agent": memory.metadata.source_agent,
                "conversation_id": memory.metadata.conversation_id,
                "workflow_id": memory.metadata.workflow_id,
                "created_at": memory.metadata.created_at.isoformat(),
                "updated_at": (
                    memory.metadata.updated_at.isoformat() if memory.metadata.updated_at else None
                ),
                "access_count": memory.metadata.access_count,
                "last_accessed": (
                    memory.metadata.last_accessed.isoformat()
                    if memory.metadata.last_accessed
                    else None
                ),
                "relevance_score": memory.metadata.relevance_score,
            },
            "related_memories": memory.related_memories,
        }
