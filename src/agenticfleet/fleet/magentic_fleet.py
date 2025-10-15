"""Microsoft Agent Framework Magentic-based fleet orchestrator."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_researcher_agent,
)
from agenticfleet.config import settings
from agenticfleet.core.exceptions import WorkflowError
from agenticfleet.core.logging import get_logger
from agenticfleet.fleet.fleet_builder import FleetBuilder

if TYPE_CHECKING:
    from agent_framework import AgentProtocol, CheckpointStorage

logger = get_logger(__name__)

NO_RESPONSE_GENERATED = "No response generated"


class MagenticFleet:
    """
    Magentic-based fleet orchestrator using Microsoft Agent Framework.

    This class replaces the custom MultiAgentWorkflow with a proper Magentic
    implementation that uses:
    - StandardMagenticManager for planning and progress evaluation
    - MagenticOrchestratorExecutor for coordination loop
    - MagenticAgentExecutor wrappers for each specialist agent

    The planner dynamically delegates to agents based on JSON-structured
    progress ledgers rather than manual DELEGATE token parsing.
    """

    def __init__(
        self,
        checkpoint_storage: CheckpointStorage | None = None,
        approval_handler: Any | None = None,
        agents: dict[str, AgentProtocol] | None = None,
    ) -> None:
        """
        Initialize the Magentic fleet orchestrator.

        Args:
            checkpoint_storage: Optional storage for workflow state persistence.
            approval_handler: Optional handler for HITL plan review operations.
            agents: Optional custom agent dictionary (uses defaults if None).
        """
        self.checkpoint_storage = checkpoint_storage
        self.approval_handler = approval_handler
        self.workflow_id: str | None = None

        # Create or use provided agents
        if agents is None:
            logger.info("Creating default specialist agents")
            self.agents = self._create_default_agents()
        else:
            logger.info(f"Using {len(agents)} provided agents")
            self.agents = agents

        # Build the Magentic workflow
        self.workflow = self._build_magentic_workflow()

        # Configure HITL if enabled
        if approval_handler:
            from agenticfleet.core.approved_tools import set_approval_handler

            set_approval_handler(approval_handler)
            logger.info("HITL approval handler configured for fleet")

    def _create_default_agents(self) -> dict[str, AgentProtocol]:
        """
        Create the default set of specialist agents.

        Returns:
            Dictionary mapping agent names to AgentProtocol instances.
        """
        agents: dict[str, AgentProtocol] = {}

        try:
            researcher = create_researcher_agent()
            agents["researcher"] = researcher
            logger.debug("Created researcher agent")
        except Exception as error:
            logger.warning(f"Failed to create researcher agent: {error}")

        try:
            coder = create_coder_agent()
            agents["coder"] = coder
            logger.debug("Created coder agent")
        except Exception as error:
            logger.warning(f"Failed to create coder agent: {error}")

        try:
            analyst = create_analyst_agent()
            agents["analyst"] = analyst
            logger.debug("Created analyst agent")
        except Exception as error:
            logger.warning(f"Failed to create analyst agent: {error}")

        if not agents:
            raise WorkflowError("Failed to create any specialist agents")

        logger.info(f"Created {len(agents)} specialist agents: {list(agents.keys())}")
        return agents

    def _build_magentic_workflow(self) -> Any:
        """
        Build the Magentic workflow using FleetBuilder.

        Returns:
            Configured Magentic workflow ready for execution.
        """
        logger.info("Building Magentic workflow with FleetBuilder")

        builder = FleetBuilder()

        # Configure the workflow
        workflow = (
            builder.with_agents(self.agents)
            .with_manager()  # Uses default instructions and model from config
            .with_observability()  # Enable streaming and progress callbacks
            .with_checkpointing(self.checkpoint_storage)
            .with_plan_review()  # Uses config setting
            .build()
        )

        logger.info("Magentic workflow built successfully")
        return workflow

    def set_workflow_id(self, workflow_id: str) -> None:
        """
        Set the workflow ID for tracking and checkpoint management.

        Args:
            workflow_id: Unique identifier for this workflow execution.
        """
        self.workflow_id = workflow_id
        logger.debug(f"Workflow ID set to: {workflow_id}")

    async def run(
        self,
        user_input: str,
        resume_from_checkpoint: str | None = None,
    ) -> str:
        """
        Execute the Magentic workflow.

        The workflow follows the Magentic coordination cycle:
        1. Plan: Manager gathers facts and creates plan
        2. Evaluate: Manager creates progress ledger (JSON)
        3. Act: Orchestrator delegates to selected agent
        4. Observe: Agent response appended to chat history
        5. Repeat until completion or replan if stalled

        Args:
            user_input: The user's request or query.
            resume_from_checkpoint: Optional checkpoint ID to resume from.

        Returns:
            The final response synthesized by the manager.
        """
        # Generate workflow ID if not set
        if not self.workflow_id:
            self.workflow_id = f"fleet_{uuid.uuid4().hex[:8]}"
            logger.info(f"Generated workflow ID: {self.workflow_id}")

        # Handle checkpoint resumption if requested
        if resume_from_checkpoint:
            logger.info(f"Attempting to resume from checkpoint: {resume_from_checkpoint}")
            # Note: Checkpoint restoration is handled by the workflow's
            # CheckpointStorage integration automatically
            # We just need to pass the checkpoint_id to the workflow

        try:
            logger.info(f"Starting Magentic workflow for: {user_input[:100]}...")

            # Execute the Magentic workflow
            # The workflow returns a result object with the final ChatMessage
            run_kwargs: dict[str, Any] = {}
            if resume_from_checkpoint is not None:
                run_kwargs["resume_from_checkpoint"] = resume_from_checkpoint

            result = await self.workflow.run(user_input, **run_kwargs)

            # Extract the final answer from the result
            response_text = self._extract_final_answer(result)

            logger.info("Magentic workflow completed successfully")
            return response_text

        except Exception as error:
            logger.error(f"Magentic workflow execution failed: {error}", exc_info=True)
            raise WorkflowError(f"Fleet execution failed: {error}") from error

    def _extract_final_answer(self, result: Any) -> str:
        """
        Extract the final answer text from the workflow result.

        Args:
            result: The result object returned by the workflow.

        Returns:
            The final answer as a string.
        """
        # Try to get the output from the result
        if hasattr(result, "output"):
            output = result.output
            if isinstance(output, str):
                return output
            if hasattr(output, "content"):
                content = output.content
                if content is not None:
                    return str(content)
                # If content is None, fall through to check if output itself has value
            if output is not None:
                return str(output)

        # Try to get content directly
        if hasattr(result, "content"):
            content = result.content
            if content is not None:
                return str(content)
            # If content is explicitly None, no response was generated
            return NO_RESPONSE_GENERATED

        # Fallback to string representation only if it's not a mock
        result_str = str(result)
        if result_str and result_str != "None":
            return result_str

        logger.warning("Could not extract final answer from result")
        return NO_RESPONSE_GENERATED

    async def list_checkpoints(self) -> list[Any]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint metadata dictionaries.
        """
        import json
        from pathlib import Path

        checkpoints: list[Any] = []

        # If we have checkpoint storage, try to use it
        if self.checkpoint_storage and hasattr(self.checkpoint_storage, "list_checkpoints"):
            # If the storage has a list method, use it
            storage_checkpoints = await self.checkpoint_storage.list_checkpoints()
            for checkpoint in storage_checkpoints:
                # Convert WorkflowCheckpoint to dict
                checkpoint_dict = {
                    "id": getattr(checkpoint, "id", str(uuid.uuid4())),
                    "timestamp": getattr(checkpoint, "timestamp", ""),
                    "current_round": getattr(checkpoint, "current_round", 0),
                    "metadata": getattr(checkpoint, "metadata", {}),
                }
                checkpoints.append(checkpoint_dict)
        else:
            # Fallback: scan the checkpoints directory
            checkpoint_dir = Path("./checkpoints")
            if checkpoint_dir.exists():
                for checkpoint_file in checkpoint_dir.glob("*.json"):
                    try:
                        with open(checkpoint_file) as f:
                            checkpoint_data = json.load(f)

                        # Extract the expected fields
                        checkpoint_info = {
                            "checkpoint_id": checkpoint_data.get("checkpoint_id"),
                            "workflow_id": checkpoint_data.get("workflow_id"),
                            "timestamp": checkpoint_data.get("timestamp"),
                            "current_round": checkpoint_data.get("executor_states", {})
                            .get("magentic_orchestrator", {})
                            .get("plan_review_round", 0),
                            "metadata": {
                                "status": checkpoint_data.get("metadata", {}).get(
                                    "checkpoint_type", "unknown"
                                )
                            },
                        }
                        checkpoints.append(checkpoint_info)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse checkpoint file {checkpoint_file}: {e}")
                        continue

        # Sort by timestamp descending (newest first)
        checkpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return checkpoints


# Default fleet instance factory for backward compatibility
# Note: Do not instantiate at module level to avoid import errors
# Use create_default_fleet() function instead


def create_default_fleet() -> MagenticFleet:
    """
    Create a default MagenticFleet instance with settings from config.

    Returns:
        Configured MagenticFleet instance ready to run.
    """
    checkpoint_storage = settings.create_checkpoint_storage()

    approval_handler = None
    hitl_config = settings.workflow_config.get("workflow", {}).get("human_in_the_loop", {})
    if hitl_config.get("enabled", False):
        from agenticfleet.core.cli_approval import CLIApprovalHandler

        timeout_seconds = hitl_config.get("approval_timeout_seconds", 300)
        auto_reject = hitl_config.get("auto_reject_on_timeout", False)
        approval_handler = CLIApprovalHandler(
            timeout_seconds=timeout_seconds,
            auto_reject_on_timeout=auto_reject,
        )
        logger.info(f"HITL enabled with timeout={timeout_seconds}s, auto_reject={auto_reject}")

    return MagenticFleet(
        checkpoint_storage=checkpoint_storage,
        approval_handler=approval_handler,
    )
