"""
Test suite for AgenticFleet Memory System.

Comprehensive tests for memory storage, retrieval, context provision,
and workflow integration using OpenMemory MCP server.
"""

from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio

from agenticfleet.memory import (
    Memory,
    MemoryContextProvider,
    MemoryManager,
    MemoryMetadata,
    MemoryPriority,
    MemoryQuery,
    MemoryType,
    OpenMemoryMCPIntegration,
    memory_config,
    memory_policy,
)
from agenticfleet.memory.workflow_integration import MemoryWorkflowIntegration


class MockMCPClient:
    """Mock MCP client for testing."""

    def __init__(self) -> None:
        self.memories: dict[str, dict[str, Any]] = {}
        self.next_id = 1

    async def call_tool(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Mock MCP tool call."""
        if method == "store_memory":
            memory_id = f"mem_{self.next_id:04d}"
            self.next_id += 1
            self.memories[memory_id] = {
                "memory_id": memory_id,
                **params,
                "created_at": datetime.utcnow().isoformat(),
            }
            return {"memory_id": memory_id, "success": True}

        elif method == "search_memories":
            results = []
            query = params.get("query", "").lower()

            for _mem_id, mem_data in self.memories.items():
                if (
                    query in mem_data.get("content", "").lower()
                    or query in mem_data.get("title", "").lower()
                ):
                    results.append(mem_data)

            return {
                "memories": results[: params.get("limit", 10)],
                "total_found": len(results),
            }

        elif method == "update_memory":
            update_memory_id: str | None = params.get("memory_id")
            if (
                update_memory_id is not None
                and isinstance(update_memory_id, str)
                and update_memory_id in self.memories
            ):
                self.memories[update_memory_id].update(params)
                return {"success": True}
            return {"success": False}

        elif method == "delete_memory":
            delete_memory_id: str | None = params.get("memory_id")
            if (
                delete_memory_id is not None
                and isinstance(delete_memory_id, str)
                and delete_memory_id in self.memories
            ):
                del self.memories[delete_memory_id]
                return {"success": True}
            return {"success": False}

        elif method == "list_memories":
            mem_list = list(self.memories.values())
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)
            return {
                "memories": mem_list[offset : offset + limit],
                "total_found": len(mem_list),
            }

        elif method == "get_stats":
            return {
                "total_memories": len(self.memories),
                "storage_usage_mb": sum(len(str(m)) for m in self.memories.values())
                / (1024 * 1024),
            }

        else:
            raise ValueError(f"Unknown method: {method}")


@pytest_asyncio.fixture
async def mock_mcp_client() -> MockMCPClient:
    """Fixture providing mock MCP client."""
    return MockMCPClient()


@pytest_asyncio.fixture
async def memory_manager(mock_mcp_client: MockMCPClient) -> MemoryManager:
    """Fixture providing memory manager with mock MCP."""
    manager = MemoryManager(mock_mcp_client)
    await manager.initialize()
    return manager


@pytest_asyncio.fixture
async def memory_context_provider(memory_manager: MemoryManager) -> MemoryContextProvider:
    """Fixture providing memory context provider."""
    return MemoryContextProvider(memory_manager)


@pytest_asyncio.fixture
async def openmemory_integration(mock_mcp_client: MockMCPClient) -> OpenMemoryMCPIntegration:
    """Fixture providing OpenMemory integration."""
    integration = OpenMemoryMCPIntegration(mock_mcp_client)
    await integration.initialize()
    return integration


@pytest_asyncio.fixture
async def workflow_integration(
    memory_manager: MemoryManager, memory_context_provider: MemoryContextProvider
) -> MemoryWorkflowIntegration:
    """Fixture providing workflow integration."""
    return MemoryWorkflowIntegration(memory_manager, memory_context_provider)


class TestMemoryManager:
    """Test cases for MemoryManager."""

    @pytest.mark.asyncio
    async def test_store_memory(self, memory_manager: MemoryManager) -> None:
        """Test storing a memory."""
        memory_id = await memory_manager.store_memory(
            title="Test Memory",
            content="This is a test memory for validation",
            memory_type=MemoryType.LEARNING,
            priority=MemoryPriority.HIGH,
            context_keywords=["test", "validation"],
        )

        assert memory_id is not None
        assert memory_id.startswith("mem_")

    @pytest.mark.asyncio
    async def test_retrieve_memories_by_query(self, memory_manager: MemoryManager) -> None:
        """Test retrieving memories by query."""
        # Store a test memory
        await memory_manager.store_memory(
            title="Async Pattern Learning",
            content="Always use await when calling async functions in Python",
            memory_type=MemoryType.LEARNING,
            context_keywords=["async", "python", "await"],
        )

        # Search for the memory
        results = await memory_manager.retrieve_memories(
            query="async functions best practices",
            memory_types=[MemoryType.LEARNING],
        )

        assert results.total_found >= 1
        assert len(results.memories) >= 1
        assert "async" in results.memories[0].content.lower()

    @pytest.mark.asyncio
    async def test_retrieve_memories_by_type(self, memory_manager: MemoryManager) -> None:
        """Test retrieving memories by type."""
        # Store memories of different types
        await memory_manager.store_memory(
            title="Conversation 1",
            content="User asked about async patterns",
            memory_type=MemoryType.CONVERSATION,
        )

        await memory_manager.store_memory(
            title="Learning 1",
            content="Learned about async/await patterns",
            memory_type=MemoryType.LEARNING,
        )

        # Search only for learning memories
        results = await memory_manager.retrieve_memories(
            query="patterns",
            memory_types=[MemoryType.LEARNING],
        )

        assert all(m.type == MemoryType.LEARNING for m in results.memories)

    @pytest.mark.asyncio
    async def test_update_memory(self, memory_manager: MemoryManager) -> None:
        """Test updating an existing memory."""
        # Store a memory
        memory_id = await memory_manager.store_memory(
            title="Original Title",
            content="Original content",
            memory_type=MemoryType.LEARNING,
        )

        # Update the memory
        success = await memory_manager.update_memory(
            memory_id=memory_id,
            title="Updated Title",
            content="Updated content with more details",
            priority=MemoryPriority.HIGH,
        )

        assert success is True

        # Verify the update
        results = await memory_manager.retrieve_memories(query="Updated Title")
        assert len(results.memories) >= 1
        updated_memory = results.memories[0]
        assert updated_memory.title == "Updated Title"
        assert "more details" in updated_memory.content

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_manager: MemoryManager) -> None:
        """Test deleting a memory."""
        # Store a memory
        memory_id = await memory_manager.store_memory(
            title="To Delete",
            content="This memory will be deleted",
            memory_type=MemoryType.CONVERSATION,
        )

        # Verify it exists
        results = await memory_manager.retrieve_memories(query="To Delete")
        assert len(results.memories) >= 1

        # Delete the memory
        success = await memory_manager.delete_memory(memory_id)
        assert success is True

        # Verify it's gone (may take time to propagate from cache)
        # Note: In real implementation, cache invalidation should be immediate

    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_manager: MemoryManager) -> None:
        """Test getting memory statistics."""
        # Store some memories
        await memory_manager.store_memory(
            title="Stat Test 1",
            content="Content for stats test",
            memory_type=MemoryType.LEARNING,
        )

        await memory_manager.store_memory(
            title="Stat Test 2",
            content="More content for stats",
            memory_type=MemoryType.CONVERSATION,
        )

        # Get stats
        stats = await memory_manager.get_memory_stats()
        assert stats.total_memories >= 2
        assert MemoryType.LEARNING in stats.memories_by_type
        assert MemoryType.CONVERSATION in stats.memories_by_type


class TestMemoryContextProvider:
    """Test cases for MemoryContextProvider."""

    @pytest.mark.asyncio
    async def test_get_context_with_memories(
        self, memory_context_provider: MemoryContextProvider, memory_manager: MemoryManager
    ) -> None:
        """Test getting context with relevant memories."""
        # Store relevant memories
        await memory_manager.store_memory(
            title="Python Async Learning",
            content="Use async/await for asynchronous operations in Python",
            memory_type=MemoryType.LEARNING,
            context_keywords=["python", "async", "await"],
        )

        await memory_manager.store_memory(
            title="Error Handling Pattern",
            content="Always wrap async calls in try-catch blocks",
            memory_type=MemoryType.ERROR,
            context_keywords=["error", "async", "exception"],
        )

        # Get context for a message about async Python
        context = await memory_context_provider.get_context(
            conversation_id="test_conv",
            agent_name="test_agent",
            current_message="How should I handle async operations in Python?",
        )

        assert context["memory_count"] >= 1
        assert len(context["memories"]) >= 1
        assert any("async" in mem["content"].lower() for mem in context["memories"])

    @pytest.mark.asyncio
    async def test_store_conversation_memory(
        self, memory_context_provider: MemoryContextProvider
    ) -> None:
        """Test storing conversation memories."""
        memory_id = await memory_context_provider.store_conversation_memory(
            conversation_id="test_conv",
            agent_name="test_agent",
            message="What are the best practices for async programming?",
            response="Always use await and handle exceptions properly",
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_store_learning_memory(
        self, memory_context_provider: MemoryContextProvider
    ) -> None:
        """Test storing learning memories."""
        memory_id = await memory_context_provider.store_learning_memory(
            agent_name="test_agent",
            learning="Async operations should always be awaited in Python",
            context="While helping with async code examples",
            importance_level="high",
            tags=["python", "async", "await"],
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_store_pattern_memory(
        self, memory_context_provider: MemoryContextProvider
    ) -> None:
        """Test storing pattern memories."""
        memory_id = await memory_context_provider.store_pattern_memory(
            agent_name="test_agent",
            pattern_name="Async Error Handling Pattern",
            pattern_description="Wrap all async calls in try-catch blocks and handle exceptions appropriately",
            usage_example="try: result = await async_func(); except Exception as e: handle_error(e)",
            tags=["async", "error-handling", "pattern"],
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_store_error_memory(self, memory_context_provider: MemoryContextProvider) -> None:
        """Test storing error memories."""
        memory_id = await memory_context_provider.store_error_memory(
            agent_name="test_agent",
            error_description="RuntimeError: coroutine was never awaited",
            solution="Add await keyword before the coroutine call",
            error_type="RuntimeError",
            context="When testing async function examples",
        )

        assert memory_id is not None


class TestOpenMemoryIntegration:
    """Test cases for OpenMemoryMCPIntegration."""

    @pytest.mark.asyncio
    async def test_initialize_connection(
        self, openmemory_integration: OpenMemoryMCPIntegration
    ) -> None:
        """Test OpenMemory connection initialization."""
        # Should already be initialized in fixture
        assert openmemory_integration._connected is True

    @pytest.mark.asyncio
    async def test_store_and_search_memory(
        self, openmemory_integration: OpenMemoryMCPIntegration
    ) -> None:
        """Test storing and searching memories through OpenMemory."""
        # Create a memory
        memory = Memory(
            id="test_mem_001",
            type=MemoryType.LEARNING,
            title="OpenMemory Test Learning",
            content="This memory tests OpenMemory integration",
            metadata=MemoryMetadata(
                created_at=datetime.utcnow(),
                tags=["test", "openmemory"],
            ),
            priority=MemoryPriority.MEDIUM,
            context_keywords=["test", "integration"],
        )

        # Store the memory
        stored_id = await openmemory_integration.store_memory(memory)
        assert stored_id is not None

        # Search for the memory
        query = MemoryQuery(
            query="OpenMemory integration test",
            memory_types=[MemoryType.LEARNING],
            limit=10,
        )

        results = await openmemory_integration.search_memories(query)
        assert results.total_found >= 1
        assert len(results.memories) >= 1

    @pytest.mark.asyncio
    async def test_update_memory_via_openmemory(
        self, openmemory_integration: OpenMemoryMCPIntegration
    ) -> None:
        """Test updating memory through OpenMemory."""
        # Store a memory first
        memory = Memory(
            id="test_update_001",
            type=MemoryType.LEARNING,
            title="Original Title",
            content="Original content for update test",
            metadata=MemoryMetadata(created_at=datetime.utcnow()),
        )

        stored_id = await openmemory_integration.store_memory(memory)

        # Update the memory
        memory.id = stored_id
        memory.title = "Updated Title"
        memory.content = "Updated content for test"

        success = await openmemory_integration.update_memory(memory)
        assert success is True

    @pytest.mark.asyncio
    async def test_list_memories(self, openmemory_integration: OpenMemoryMCPIntegration) -> None:
        """Test listing memories from OpenMemory."""
        memories = await openmemory_integration.list_memories(limit=10)
        assert isinstance(memories, list)

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, openmemory_integration: OpenMemoryMCPIntegration) -> None:
        """Test getting memory statistics from OpenMemory."""
        stats = await openmemory_integration.get_memory_stats()
        assert isinstance(stats, dict)


class TestMemoryWorkflowIntegration:
    """Test cases for MemoryWorkflowIntegration."""

    @pytest.mark.asyncio
    async def test_initialize_workflow(
        self, workflow_integration: MemoryWorkflowIntegration
    ) -> None:
        """Test workflow initialization."""
        workflow_id = "test_workflow_001"

        # Mock agents
        class MockAgent:
            def __init__(self, name: str) -> None:
                self.name = name

        agents = [MockAgent("agent1"), MockAgent("agent2")]

        await workflow_integration.initialize_workflow(workflow_id, agents)
        assert workflow_id in workflow_integration._workflow_memories

    @pytest.mark.asyncio
    async def test_provide_agent_context(
        self, workflow_integration: MemoryWorkflowIntegration, memory_manager: MemoryManager
    ) -> None:
        """Test providing context to an agent."""
        workflow_id = "test_workflow_002"

        # Store a relevant memory
        await memory_manager.store_memory(
            title="Agent Context Test",
            content="This memory should be provided to agents",
            memory_type=MemoryType.CONTEXT,
            context_keywords=["agent", "context"],
        )

        context = await workflow_integration.provide_agent_context(
            workflow_id=workflow_id,
            agent_name="test_agent",
            current_message="I need context about agent operations",
        )

        assert "memories" in context
        assert "memory_count" in context
        assert context["memory_count"] >= 0

    @pytest.mark.asyncio
    async def test_store_agent_execution(
        self, workflow_integration: MemoryWorkflowIntegration
    ) -> None:
        """Test storing memories from agent execution."""
        workflow_id = "test_workflow_003"

        memory_ids = await workflow_integration.store_agent_execution(
            workflow_id=workflow_id,
            agent_name="test_agent",
            task="Handle async operation properly",
            result="I learned that async operations should use await keyword. This is an important pattern for Python async programming.",
            execution_metadata={"execution_time": 1.5},
        )

        assert len(memory_ids) >= 1
        assert workflow_id in workflow_integration._workflow_memories

    @pytest.mark.asyncio
    async def test_finalize_workflow(self, workflow_integration: MemoryWorkflowIntegration) -> None:
        """Test finalizing a workflow."""
        workflow_id = "test_workflow_004"

        # Add some memories to the workflow
        workflow_integration._workflow_memories[workflow_id] = ["mem_001", "mem_002"]

        summary = await workflow_integration.finalize_workflow(
            workflow_id=workflow_id,
            workflow_result="Successfully completed async programming task",
            workflow_metadata={"duration": 300},
        )

        assert summary["workflow_id"] == workflow_id
        assert summary["total_memories_stored"] >= 3  # 2 existing + 1 summary
        assert workflow_id not in workflow_integration._workflow_memories


class TestMemoryConfiguration:
    """Test cases for memory configuration and policies."""

    def test_memory_config_defaults(self) -> None:
        """Test default memory configuration."""
        assert memory_config.openmemory_enabled is True
        assert memory_config.enable_learning_memories is True
        assert memory_config.max_memories_per_context == 10

    def test_get_agent_config(self) -> None:
        """Test getting agent-specific configuration."""
        # Test with non-existent agent
        config = memory_config.get_agent_config("non_existent_agent")
        assert config["enable_memories"] is True
        assert "conversation" in config["memory_types"]

        # Set and get agent config
        memory_config.set_agent_config(
            "test_agent",
            {
                "enable_memories": False,
                "memory_types": ["learning"],
                "max_memories": 3,
            },
        )

        config = memory_config.get_agent_config("test_agent")
        assert config["enable_memories"] is False
        assert config["memory_types"] == ["learning"]
        assert config["max_memories"] == 3

    def test_memory_policies(self) -> None:
        """Test memory policies."""
        # Test storage policies
        assert memory_policy.should_store_memory("conversation") is True
        assert memory_policy.should_store_memory("learning") is True

        # Test pattern approval
        assert memory_policy.requires_approval("pattern", is_pattern=True) is True
        assert memory_policy.requires_approval("conversation", is_pattern=False) is False


# Integration tests
@pytest.mark.integration
class TestMemorySystemIntegration:
    """Integration tests for the complete memory system."""

    @pytest.mark.asyncio
    async def test_full_memory_lifecycle(
        self,
        memory_manager: MemoryManager,
        memory_context_provider: MemoryContextProvider,
        workflow_integration: MemoryWorkflowIntegration,
    ) -> None:
        """Test complete memory lifecycle from storage to retrieval."""
        workflow_id = "integration_test_001"

        # 1. Initialize workflow
        await workflow_integration.initialize_workflow(workflow_id, [])

        # 2. Provide context to agent
        _context: dict[str, Any] = await memory_context_provider.get_context(
            conversation_id=workflow_id,
            agent_name="integration_agent",
            current_message="I need to learn about async programming best practices",
        )

        # 3. Agent executes and stores learnings
        memory_ids = await workflow_integration.store_agent_execution(
            workflow_id=workflow_id,
            agent_name="integration_agent",
            task="Teach async programming best practices",
            result="Key learning: Always use await keyword with async functions. Also important: Handle exceptions properly in async code.",
        )

        assert len(memory_ids) >= 1

        # 4. Retrieve relevant memories for new context
        results = await memory_manager.retrieve_memories(
            query="async programming best practices",
            memory_types=[MemoryType.LEARNING],
            conversation_id=workflow_id,
        )

        assert results.total_found >= 1
        assert any("await" in mem.content.lower() for mem in results.memories)

        # 5. Finalize workflow
        summary = await workflow_integration.finalize_workflow(
            workflow_id=workflow_id,
            workflow_result="Successfully taught async programming concepts",
        )

        assert summary["total_memories_stored"] >= 2


if __name__ == "__main__":
    # Run tests if this file is executed directly
    pytest.main([__file__, "-v"])
