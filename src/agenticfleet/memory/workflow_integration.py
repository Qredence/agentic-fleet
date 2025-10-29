"""
Workflow Integration - Integrates memory system with AgenticFleet workflows.

Provides seamless memory integration with Microsoft Agent Framework workflows,
ensuring agents have access to relevant memories and can store new insights.
"""

import logging
from typing import Any

from .config import memory_config, memory_policy
from .context_provider import MemoryContextProvider
from .manager import MemoryManager
from .mcp_integration import OpenMemoryMCPIntegration
from .models import MemoryPriority, MemoryType


# Define fallback classes
class FallbackAgent:
    """Fallback Agent class for when Microsoft Agent Framework is not available."""

    def __init__(self, name: str):
        self.name = name


class FallbackWorkflow:
    """Fallback Workflow class for when Microsoft Agent Framework is not available."""

    pass


# Try to import real classes, fall back to dummies
try:
    from agent_framework_core import Agent, Workflow  # type: ignore
except ImportError:
    Agent = FallbackAgent
    Workflow = FallbackWorkflow

logger = logging.getLogger(__name__)


class MemoryWorkflowIntegration:
    """
    Integration layer for memory system with AgenticFleet workflows.

    Manages memory lifecycle during workflow execution, including context
    injection, memory storage, and learning capture.
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        context_provider: MemoryContextProvider,
        openmemory_integration: OpenMemoryMCPIntegration | None = None,
    ):
        """
        Initialize workflow integration.

        Args:
            memory_manager: Memory manager instance
            context_provider: Memory context provider
            openmemory_integration: OpenMemory MCP integration (optional)
        """
        self.memory_manager = memory_manager
        self.context_provider = context_provider
        self.openmemory_integration = openmemory_integration
        self._workflow_memories: dict[str, list[str]] = {}

    async def initialize_workflow(self, workflow_id: str, agents: list[Agent]) -> None:
        """
        Initialize memory integration for a workflow.

        Args:
            workflow_id: Unique workflow identifier
            agents: List of agents in the workflow
        """
        try:
            # Initialize memory tracking for this workflow
            self._workflow_memories[workflow_id] = []

            # Store workflow context
            await self._store_workflow_context(workflow_id, agents)

            logger.info(f"Initialized memory integration for workflow: {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to initialize workflow memory integration: {e}")

    async def provide_agent_context(
        self,
        workflow_id: str,
        agent_name: str,
        current_message: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Provide memory context to an agent before execution.

        Args:
            workflow_id: Workflow identifier
            agent_name: Name of the current agent
            current_message: Current message/task
            conversation_history: Recent conversation history

        Returns:
            Context data including relevant memories
        """
        try:
            # Get agent-specific configuration
            agent_config = memory_config.get_agent_config(agent_name)

            if not agent_config.get("enable_memories", True):
                return {"memories": [], "memory_count": 0}

            # Retrieve relevant memories
            context_data = await self.context_provider.get_context(
                conversation_id=workflow_id,
                agent_name=agent_name,
                current_message=current_message,
                workflow_state={"workflow_id": workflow_id},
            )

            # Filter based on agent configuration
            allowed_types = agent_config.get("memory_types", ["conversation", "learning", "error"])
            filtered_memories = [
                mem for mem in context_data["memories"] if mem["type"] in allowed_types
            ][: agent_config.get("max_memories", 5)]

            logger.debug(f"Provided {len(filtered_memories)} memories to agent {agent_name}")

            return {
                "memories": filtered_memories,
                "memory_count": len(filtered_memories),
                "workflow_id": workflow_id,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Failed to provide context to agent {agent_name}: {e}")
            return {"memories": [], "memory_count": 0, "error": str(e)}

    async def store_agent_execution(
        self,
        workflow_id: str,
        agent_name: str,
        task: str,
        result: str,
        execution_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Store memories from agent execution.

        Args:
            workflow_id: Workflow identifier
            agent_name: Name of the executing agent
            task: Task that was executed
            result: Result/output from the agent
            execution_metadata: Additional execution metadata

        Returns:
            List of stored memory IDs
        """
        memory_ids = []

        try:
            # Get agent configuration
            agent_config = memory_config.get_agent_config(agent_name)

            # Store conversation memory if enabled
            if (
                agent_config.get("store_conversations", True)
                and memory_policy.auto_store_conversations
            ):
                conv_memory_id = await self.context_provider.store_conversation_memory(
                    conversation_id=workflow_id,
                    agent_name=agent_name,
                    message=task,
                    response=result,
                    context_type="workflow_execution",
                    metadata=execution_metadata,
                )
                if conv_memory_id:
                    memory_ids.append(conv_memory_id)

            # Detect and store learnings
            if agent_config.get("store_learnings", True):
                learnings = await self._detect_learnings(agent_name, task, result)
                for learning in learnings:
                    learning_id = await self.context_provider.store_learning_memory(
                        agent_name=agent_name,
                        learning=learning["content"],
                        context=learning.get("context"),
                        importance_level=learning.get("importance", "medium"),
                        tags=learning.get("tags"),
                    )
                    if learning_id:
                        memory_ids.append(learning_id)

            # Detect and store patterns
            if agent_config.get("store_patterns", False):
                patterns = await self._detect_patterns(agent_name, task, result)
                for pattern in patterns:
                    if memory_policy.requires_approval("pattern", is_pattern=True):
                        # In a real implementation, this would trigger HITL approval
                        logger.info(f"Pattern detected requiring approval: {pattern['name']}")
                        continue

                    pattern_id = await self.context_provider.store_pattern_memory(
                        agent_name=agent_name,
                        pattern_name=pattern["name"],
                        pattern_description=pattern["description"],
                        usage_example=pattern.get("example"),
                        tags=pattern.get("tags"),
                    )
                    if pattern_id:
                        memory_ids.append(pattern_id)

            # Store error memories if errors occurred
            if agent_config.get("store_errors", True) and memory_policy.auto_store_errors:
                errors = await self._detect_errors(agent_name, task, result)
                for error in errors:
                    error_id = await self.context_provider.store_error_memory(
                        agent_name=agent_name,
                        error_description=error["description"],
                        solution=error["solution"],
                        error_type=error.get("type"),
                        context=error.get("context"),
                    )
                    if error_id:
                        memory_ids.append(error_id)

            # Ensure workflow tracking exists and track memories for this workflow
            if workflow_id not in self._workflow_memories:
                self._workflow_memories[workflow_id] = []

            self._workflow_memories[workflow_id].extend(memory_ids)

            logger.info(
                f"Stored {len(memory_ids)} memories for agent {agent_name} in workflow {workflow_id}"
            )
            return memory_ids

        except Exception as e:
            logger.error(f"Failed to store execution memories for agent {agent_name}: {e}")
            return memory_ids

    async def finalize_workflow(
        self,
        workflow_id: str,
        workflow_result: str | None = None,
        workflow_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Finalize memory integration for a completed workflow.

        Args:
            workflow_id: Workflow identifier
            workflow_result: Final workflow result
            workflow_metadata: Workflow execution metadata

        Returns:
            Summary of memories stored during the workflow
        """
        try:
            workflow_memory_ids = self._workflow_memories.get(workflow_id, [])

            # Store workflow summary memory
            if workflow_result and memory_policy.should_store_memory("workflow"):
                summary_memory_id = await self.memory_manager.store_memory(
                    title=f"Workflow Summary - {workflow_id}",
                    content=f"Workflow Result:\n{workflow_result}",
                    memory_type=MemoryType.WORKFLOW,
                    priority=memory_config.priority_map.get("workflow", MemoryPriority.MEDIUM),
                    context_keywords=["workflow", "summary", workflow_id],
                    metadata={
                        "workflow_id": workflow_id,
                        "total_memories": len(workflow_memory_ids),
                        "completed_at": (
                            workflow_metadata.get("completed_at") if workflow_metadata else None
                        ),
                    },
                    conversation_id=workflow_id,
                )
                workflow_memory_ids.append(summary_memory_id)

            # Generate workflow memory summary
            summary = {
                "workflow_id": workflow_id,
                "total_memories_stored": len(workflow_memory_ids),
                "memory_ids": workflow_memory_ids,
                "workflow_result": workflow_result,
                "metadata": workflow_metadata,
            }

            # Clean up workflow tracking
            if workflow_id in self._workflow_memories:
                del self._workflow_memories[workflow_id]

            logger.info(
                f"Finalized memory integration for workflow {workflow_id}: {len(workflow_memory_ids)} memories"
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to finalize workflow memory integration: {e}")
            return {"workflow_id": workflow_id, "error": str(e), "total_memories_stored": 0}

    # Private helper methods

    async def _store_workflow_context(self, workflow_id: str, agents: list[Agent]) -> None:
        """Store initial workflow context."""
        agent_names = [agent.name for agent in agents]

        await self.memory_manager.store_memory(
            title=f"Workflow Context - {workflow_id}",
            content=f"Workflow participants: {', '.join(agent_names)}\nWorkflow ID: {workflow_id}",
            memory_type=MemoryType.CONTEXT,
            context_keywords=["workflow", "context", workflow_id, *agent_names],
            metadata={
                "workflow_id": workflow_id,
                "participants": agent_names,
                "participant_count": len(agent_names),
            },
            conversation_id=workflow_id,
        )

    async def _detect_learnings(
        self, agent_name: str, task: str, result: str
    ) -> list[dict[str, Any]]:
        """Detect learning insights from agent execution."""
        learnings = []

        # Simple learning detection patterns
        learning_indicators = [
            "i learned",
            "i discovered",
            "i found that",
            "i realized",
            "the key insight",
            "important lesson",
            "best practice",
            "effective approach",
            "optimal solution",
            "successful strategy",
        ]

        result_lower = result.lower()
        for indicator in learning_indicators:
            if indicator in result_lower:
                # Extract the learning (simplified)
                start_idx = result_lower.find(indicator)
                if start_idx != -1:
                    # Extract a reasonable chunk around the indicator
                    learning_start = max(0, start_idx - 50)
                    learning_end = min(len(result), start_idx + 200)
                    learning_content = result[learning_start:learning_end].strip()

                    learnings.append(
                        {
                            "content": learning_content,
                            "context": f"Task: {task[:100]}...",
                            "importance": "medium",
                            "tags": ["learning", agent_name],
                        }
                    )

        return learnings[:3]  # Limit to prevent noise

    async def _detect_patterns(
        self, agent_name: str, task: str, result: str
    ) -> list[dict[str, Any]]:
        """Detect reusable patterns from agent execution."""
        patterns = []

        # Pattern detection indicators
        pattern_indicators = [
            "this approach can be reused",
            "general pattern",
            "template for",
            "reusable solution",
            "standard approach",
            "best practice is",
        ]

        result_lower = result.lower()
        for indicator in pattern_indicators:
            if indicator in result_lower:
                # Extract the pattern (simplified)
                start_idx = result_lower.find(indicator)
                if start_idx != -1:
                    pattern_start = max(0, start_idx - 30)
                    pattern_end = min(len(result), start_idx + 150)
                    pattern_content = result[pattern_start:pattern_end].strip()

                    patterns.append(
                        {
                            "name": f"Pattern from {agent_name}",
                            "description": pattern_content,
                            "example": f"Task: {task[:100]}...",
                            "tags": ["pattern", agent_name, "reusable"],
                        }
                    )

        return patterns[:2]  # Limit to prevent noise

    async def _detect_errors(self, agent_name: str, task: str, result: str) -> list[dict[str, Any]]:
        """Detect errors and solutions from agent execution."""
        errors = []

        # Error indicators
        error_indicators = [
            "error:",
            "failed",
            "exception",
            "issue",
            "problem",
            "challenge",
            "difficulty",
            "obstacle",
            "setback",
        ]

        # Solution indicators
        solution_indicators = [
            "solution:",
            "fix:",
            "resolved",
            "solved",
            "addressed",
            "overcame",
            "handled",
            "managed",
            "worked around",
        ]

        result_lower = result.lower()

        # Look for error-solution pairs
        for error_indicator in error_indicators:
            if error_indicator in result_lower:
                error_start = result_lower.find(error_indicator)
                if error_start != -1:
                    # Look for solution after the error
                    for solution_indicator in solution_indicators:
                        solution_start = result_lower.find(solution_indicator, error_start)
                        if solution_start != -1:
                            # Extract error and solution
                            error_end = solution_start
                            error_content = result[error_start:error_end].strip()

                            solution_start_idx = solution_start
                            solution_end = min(len(result), solution_start_idx + 200)
                            solution_content = result[solution_start_idx:solution_end].strip()

                            errors.append(
                                {
                                    "description": error_content,
                                    "solution": solution_content,
                                    "type": "execution_error",
                                    "context": f"Task: {task[:100]}...",
                                }
                            )

                            break  # Only take first solution for each error

        return errors[:3]  # Limit to prevent noise


# Global workflow integration instance
workflow_integration: MemoryWorkflowIntegration | None = None


def get_workflow_integration() -> MemoryWorkflowIntegration | None:
    """Get the global workflow integration instance."""
    return workflow_integration


def set_workflow_integration(integration: MemoryWorkflowIntegration) -> None:
    """Set the global workflow integration instance."""
    global workflow_integration
    workflow_integration = integration
