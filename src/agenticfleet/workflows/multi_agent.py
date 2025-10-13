"""
Custom multi-agent workflow implementation for coordinating specialized agents.

This module defines a custom workflow class to orchestrate multiple agents
(Orchestrator, Researcher, Coder, Analyst) for complex tasks. The workflow
logic is implemented independently and does not use the official Microsoft Agent
Framework's built-in workflow orchestration patterns.
Agents may be based on the Microsoft Agent Framework, but the orchestration is custom.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from agent_framework import CheckpointStorage

from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from agenticfleet.config import settings
from agenticfleet.core.exceptions import WorkflowError
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)


class MultiAgentWorkflow:
    """
    Sequential multi-agent workflow orchestrator.

    Uses the orchestrator agent to coordinate task delegation to specialized
    agents (researcher, coder, analyst) based on the official Python Agent
    Framework pattern.
    """

    DELEGATE_PREFIX: ClassVar[str] = "DELEGATE:"
    FINAL_ANSWER_PREFIX: ClassVar[str] = "FINAL_ANSWER:"

    def __init__(self, checkpoint_storage: CheckpointStorage | None = None) -> None:
        """
        Initialize workflow with all agent participants.

        Args:
            checkpoint_storage: Optional checkpoint storage for workflow state persistence
        """
        self.orchestrator = create_orchestrator_agent()
        self.researcher = create_researcher_agent()
        self.coder = create_coder_agent()
        self.analyst = create_analyst_agent()

        # Execution limits from config
        workflow_config = settings.workflow_config.get("workflow", {})
        self.max_rounds = workflow_config.get("max_rounds", 10)
        self.max_stalls = workflow_config.get("max_stalls", 3)

        # Checkpointing support
        self.checkpoint_storage = checkpoint_storage
        self.workflow_id: str | None = None
        self.current_checkpoint_id: str | None = None

        # Workflow state
        self.current_round = 0
        self.stall_count = 0
        self.last_response: str | None = None
        self.context: dict[str, Any] = {}

    def set_workflow_id(self, workflow_id: str) -> None:
        """
        Set the workflow ID for checkpoint management.

        Args:
            workflow_id: Unique identifier for this workflow execution
        """
        self.workflow_id = workflow_id

    async def create_checkpoint(self, metadata: dict[str, Any] | None = None) -> str | None:
        """
        Create a checkpoint of the current workflow state.

        Args:
            metadata: Optional metadata to include in the checkpoint

        Returns:
            Checkpoint ID or None if checkpointing is disabled
        """
        if not self.checkpoint_storage:
            return None

        checkpoint_id = str(uuid.uuid4())

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "workflow_id": self.workflow_id or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_round": self.current_round,
            "stall_count": self.stall_count,
            "last_response": self.last_response,
            "context": self.context,
            "metadata": metadata or {},
        }

        # Save checkpoint using the CheckpointStorage abstraction
        await self.checkpoint_storage.save_checkpoint(checkpoint_id, checkpoint_data)

        self.current_checkpoint_id = checkpoint_id
        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint_id

    async def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore workflow state from a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to restore

        Returns:
            True if restoration was successful, False otherwise
        """
        if not self.checkpoint_storage:
            logger.warning("Checkpointing is disabled, cannot restore")
            return False

        try:
            # Load checkpoint from storage
            checkpoint_path = Path(self.checkpoint_storage.storage_path) / f"{checkpoint_id}.json"
            if not checkpoint_path.exists():
                logger.error(f"Checkpoint not found: {checkpoint_id}")
                return False

            with open(checkpoint_path) as f:
                checkpoint_data = json.load(f)

            # Restore state
            self.workflow_id = checkpoint_data.get("workflow_id")
            self.current_round = checkpoint_data.get("current_round", 0)
            self.stall_count = checkpoint_data.get("stall_count", 0)
            self.last_response = checkpoint_data.get("last_response")
            self.context = checkpoint_data.get("context", {})
            self.current_checkpoint_id = checkpoint_id

            logger.info(f"Restored workflow from checkpoint: {checkpoint_id}")
            logger.info(f"  Round: {self.current_round}/{self.max_rounds}")
            logger.info(f"  Stall count: {self.stall_count}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return False

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[dict[str, Any]]:
        """
        List all checkpoints, optionally filtered by workflow_id.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            List of checkpoint metadata dicts
        """
        if not self.checkpoint_storage:
            return []

        checkpoints = []
        checkpoint_dir = Path(self.checkpoint_storage.storage_path)

        if not checkpoint_dir.exists():
            return []

        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)

                if workflow_id is None or data.get("workflow_id") == workflow_id:
                    checkpoints.append(
                        {
                            "checkpoint_id": data.get("checkpoint_id"),
                            "workflow_id": data.get("workflow_id"),
                            "timestamp": data.get("timestamp"),
                            "current_round": data.get("current_round"),
                            "metadata": data.get("metadata", {}),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

        # Sort by timestamp, newest first
        checkpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return checkpoints

    async def run(self, user_input: str, resume_from_checkpoint: str | None = None) -> str:
        """
        Execute workflow by routing user input through orchestrator.

        The orchestrator analyzes the request and delegates to appropriate
        specialized agents as needed. Uses sequential execution pattern
        from official Agent Framework.

        Args:
            user_input: User's request or query
            resume_from_checkpoint: Optional checkpoint ID to resume from

        Returns:
            str: Final response from the orchestrator

        Raises:
            WorkflowError: If max rounds or stalls exceeded
        """
        # Generate workflow ID if not set
        if not self.workflow_id:
            self.workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"

        # Restore from checkpoint if requested
        if resume_from_checkpoint:
            restored = await self.restore_from_checkpoint(resume_from_checkpoint)
            if not restored:
                raise WorkflowError(f"Failed to restore from checkpoint: {resume_from_checkpoint}")
            logger.info(f"Resuming workflow from round {self.current_round}")
        else:
            # Reset state for new execution
            self.current_round = 0
            self.stall_count = 0
            self.last_response = None

            # Create context with available agents
            self.context = {
                "available_agents": {
                    "researcher": "Performs web searches and data gathering",
                    "coder": "Writes, executes, and debugs code",
                    "analyst": "Analyzes data and generates insights",
                },
                "user_query": user_input,
            }

        while self.current_round < self.max_rounds:
            self.current_round += 1

            try:
                # Orchestrator decides next action
                result = await self.orchestrator.run(
                    f"Round {self.current_round}/{self.max_rounds}\n"
                    f"User Query: {user_input}\n"
                    f"Context: {self.context}\n"
                    f"Previous Response: {self.last_response or 'None'}\n\n"
                    "Analyze the request and either:\n"
                    "1. Provide a final answer if no delegation needed\n"
                    "2. Delegate to researcher/coder/analyst if more work needed\n"
                    "3. Synthesize results if subtasks complete"
                )

                response_text = self._extract_response_text(result)

                # Check for stalling (identical responses)
                if response_text == self.last_response:
                    self.stall_count += 1
                    if self.stall_count >= self.max_stalls:
                        final_response = (
                            f"Workflow stalled after {self.stall_count} identical responses. "
                            f"Last response:\n{response_text}"
                        )
                        # Save final checkpoint before returning
                        if self.checkpoint_storage:
                            await self.create_checkpoint({"status": "stalled"})
                        return final_response
                else:
                    self.stall_count = 0

                self.last_response = response_text

                # Create checkpoint after each round
                if self.checkpoint_storage:
                    await self.create_checkpoint(
                        {
                            "round": self.current_round,
                            "status": "in_progress",
                            "user_input": user_input,
                        }
                    )

                # Check if orchestrator delegated to another agent
                if self.DELEGATE_PREFIX in response_text:
                    # Parse delegation instruction
                    agent_response = await self._handle_delegation(response_text, self.context)
                    self.context["last_delegation_result"] = agent_response
                    continue

                # Check if orchestrator provided final answer
                if (
                    self.FINAL_ANSWER_PREFIX in response_text
                    or self.current_round == self.max_rounds
                ):
                    # Save final checkpoint
                    if self.checkpoint_storage:
                        await self.create_checkpoint(
                            {
                                "status": "completed",
                                "user_input": user_input,
                            }
                        )
                    return response_text

            except Exception as e:
                # Save checkpoint on error
                if self.checkpoint_storage:
                    await self.create_checkpoint(
                        {
                            "status": "error",
                            "error": str(e),
                            "user_input": user_input,
                        }
                    )
                raise WorkflowError(f"Error in workflow round {self.current_round}: {str(e)}")

        final_response = (
            f"Max rounds ({self.max_rounds}) reached. Last response:\n{self.last_response}"
        )
        # Save final checkpoint
        if self.checkpoint_storage:
            await self.create_checkpoint(
                {
                    "status": "max_rounds_reached",
                    "user_input": user_input,
                }
            )
        return final_response

    async def _handle_delegation(self, orchestrator_response: str, context: dict[str, Any]) -> str:
        """
        Handle delegation from orchestrator to specialized agent.

        Args:
            orchestrator_response: Response containing delegation instruction
            context: Current workflow context

        Returns:
            str: Response from delegated agent
        """
        # Parse delegation (format: "DELEGATE: <agent_name> - <task>")
        delegation_lines = [
            line
            for line in orchestrator_response.split("\n")
            if line.startswith(self.DELEGATE_PREFIX)
        ]
        if not delegation_lines:
            return "Error: Could not parse delegation instruction"

        delegation_line = delegation_lines[0]
        parts = delegation_line.replace(self.DELEGATE_PREFIX, "", 1).strip().split(" - ", 1)
        agent_name = parts[0].strip().lower() if parts else ""
        task = parts[1].strip() if len(parts) > 1 else context.get("user_query", "")

        # Route to appropriate agent
        agent_map = {"researcher": self.researcher, "coder": self.coder, "analyst": self.analyst}

        if agent_name not in agent_map:
            return f"Error: Unknown agent '{agent_name}'"

        agent = agent_map[agent_name]
        try:
            result = await agent.run(task)
            return self._extract_response_text(result)
        except Exception as e:
            return f"Error: Agent '{agent_name}' failed to execute task: {str(e)}"

    @staticmethod
    def _extract_response_text(result: Any) -> str:
        """Normalize agent responses to text across varying response types."""
        for attr in ("content", "output_text", "text", "response"):
            value: Any = getattr(result, attr, None)
            if value is None:
                continue
            if callable(value):
                value = value()
            if isinstance(value, str):
                return value
        return str(result)


# Create default workflow instance with checkpoint storage
_checkpoint_storage = settings.create_checkpoint_storage()
workflow = MultiAgentWorkflow(checkpoint_storage=_checkpoint_storage)
