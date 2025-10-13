"""WorkflowBuilder-based multi-agent workflow implementation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_framework import CheckpointStorage, WorkflowBuilder

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


def _should_delegate_to_researcher(context: Any) -> bool:
    """Check if orchestrator wants to delegate to researcher."""
    response_text = _extract_last_output_text(context)

    # Check for delegation to researcher
    return "DELEGATE: researcher" in response_text or "DELEGATE:researcher" in response_text


def _should_delegate_to_coder(context: Any) -> bool:
    """Check if orchestrator wants to delegate to coder."""
    response_text = _extract_last_output_text(context)
    return "DELEGATE: coder" in response_text or "DELEGATE:coder" in response_text


def _should_delegate_to_analyst(context: Any) -> bool:
    """Check if orchestrator wants to delegate to analyst."""
    response_text = _extract_last_output_text(context)
    return "DELEGATE: analyst" in response_text or "DELEGATE:analyst" in response_text


def _extract_last_output_text(context: Any) -> str:
    """Extract the latest executor output text from a workflow context."""
    if not context:
        return ""

    last_output = getattr(context, "last_output", None)
    if not last_output:
        return ""

    # Prefer the payload stored on the workflow event if available
    payload = getattr(last_output, "output", last_output)

    if payload is None:
        return ""

    return _extract_response_text(payload)


def _extract_response_text(result: Any) -> str:
    """
    Normalize agent responses to text across varying response types.

    Expected types:
        - dict: with one of the keys "content", "output_text", "text", "response"
        - object: with one of the attributes "content", "output_text", "text", "response"
        - str: returned as is
        - other: fallback to str(result)
    """
    # If result is a string, return it directly
    if isinstance(result, str):
        return result
    # If result is a dict, check for known keys
    if isinstance(result, dict):
        for key in ("content", "output_text", "text", "response"):
            value = result.get(key)
            if value is None:
                continue
            if callable(value):
                value = value()
            if isinstance(value, str):
                return value
    else:
        # Otherwise, check for known attributes
        for attr in ("content", "output_text", "text", "response"):
            value = getattr(result, attr, None)
            if value is None:
                continue
            if callable(value):
                value = value()
            if isinstance(value, str):
                return value
    # Fallback: return string representation
    return str(result)


def create_workflow(checkpoint_storage: CheckpointStorage | None = None) -> Any:
    """
    Create multi-agent workflow using WorkflowBuilder pattern.

    Args:
        checkpoint_storage: Optional checkpoint storage for workflow state persistence

    Returns:
        Workflow: Configured workflow with orchestrator and specialized agents
    """
    # Load workflow configuration
    workflow_config = settings.workflow_config.get("workflow", {})
    max_rounds = workflow_config.get("max_rounds", 10)

    # Create all agents
    orchestrator = create_orchestrator_agent()
    researcher = create_researcher_agent()
    coder = create_coder_agent()
    analyst = create_analyst_agent()

    builder_kwargs: dict[str, Any] = {"max_iterations": max_rounds}
    if checkpoint_storage is not None:
        builder_kwargs["checkpoint_storage"] = checkpoint_storage

    # Build workflow graph with optional checkpointing
    builder = WorkflowBuilder(**builder_kwargs)
    
    workflow = (
        builder
        # Add all agents as executors
        .add_agent(orchestrator)
        .add_agent(researcher)
        .add_agent(coder)
        .add_agent(analyst)
        # Orchestrator conditionally delegates to specialist agents
        .add_edge(orchestrator, researcher, condition=_should_delegate_to_researcher)
        .add_edge(orchestrator, coder, condition=_should_delegate_to_coder)
        .add_edge(orchestrator, analyst, condition=_should_delegate_to_analyst)
        # All specialist agents return to orchestrator
        .add_edge(researcher, orchestrator)
        .add_edge(coder, orchestrator)
        .add_edge(analyst, orchestrator)
        # Start with orchestrator
        .set_start_executor(orchestrator)
        .build()
    )

    return workflow


class MultiAgentWorkflow:
    """
    WorkflowBuilder-based multi-agent workflow orchestrator.

    This class provides compatibility with the previous MultiAgentWorkflow API
    while using the official Microsoft Agent Framework's WorkflowBuilder pattern
    for graph-based orchestration.
    """

    def __init__(self, checkpoint_storage: CheckpointStorage | None = None) -> None:
        """Initialize workflow with WorkflowBuilder pattern."""

        workflow_config = settings.workflow_config.get("workflow", {})

        self.max_rounds = workflow_config.get("max_rounds", 10)
        self.max_stalls = workflow_config.get("max_stalls", 3)

        self.checkpoint_storage = checkpoint_storage
        self.workflow_id: str | None = None
        self.current_checkpoint_id: str | None = None
        self.current_round = 0
        self.stall_count = 0
        self.last_response: str | None = None
        self.context: dict[str, Any] = {}

        self.workflow = create_workflow(checkpoint_storage)

    def set_workflow_id(self, workflow_id: str) -> None:
        """Set the workflow ID for checkpoint management."""

        self.workflow_id = workflow_id

    async def create_checkpoint(
        self, metadata: dict[str, Any] | None = None
    ) -> str | None:
        """Create a checkpoint of the current workflow state."""

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

        checkpoint_dir = Path(self.checkpoint_storage.storage_path)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{checkpoint_id}.json"

        with open(checkpoint_path, "w", encoding="utf-8") as file:
            json.dump(checkpoint_data, file, indent=2)

        self.current_checkpoint_id = checkpoint_id
        logger.info("Created checkpoint: %s", checkpoint_id)
        return checkpoint_id

    async def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore workflow state from a checkpoint."""

        if not self.checkpoint_storage:
            logger.warning("Checkpointing is disabled, cannot restore")
            return False

        checkpoint_path = (
            Path(self.checkpoint_storage.storage_path) / f"{checkpoint_id}.json"
        )

        if not checkpoint_path.exists():
            logger.error("Checkpoint not found: %s", checkpoint_id)
            return False

        try:
            with open(checkpoint_path, encoding="utf-8") as file:
                data = json.load(file)
        except Exception as error:  # pragma: no cover - defensive
            logger.error("Failed to load checkpoint %s: %s", checkpoint_id, error)
            return False

        self.workflow_id = data.get("workflow_id")
        self.current_round = data.get("current_round", 0)
        self.stall_count = data.get("stall_count", 0)
        self.last_response = data.get("last_response")
        self.context = data.get("context", {}) or {}
        self.current_checkpoint_id = checkpoint_id

        logger.info(
            "Restored workflow %s from checkpoint %s",
            self.workflow_id,
            checkpoint_id,
        )
        return True

    async def list_checkpoints(
        self, workflow_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List available checkpoints, optionally filtering by workflow ID."""

        if not self.checkpoint_storage:
            return []

        checkpoint_dir = Path(self.checkpoint_storage.storage_path)
        if not checkpoint_dir.exists():
            return []

        checkpoints: list[dict[str, Any]] = []
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, encoding="utf-8") as file:
                    data = json.load(file)
            except Exception as error:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to read checkpoint %s: %s", checkpoint_file, error
                )
                continue

            if workflow_id is not None and data.get("workflow_id") != workflow_id:
                continue

            checkpoints.append(
                {
                    "checkpoint_id": data.get("checkpoint_id"),
                    "workflow_id": data.get("workflow_id"),
                    "timestamp": data.get("timestamp"),
                    "current_round": data.get("current_round"),
                    "metadata": data.get("metadata", {}),
                }
            )

        checkpoints.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
        return checkpoints

    async def run(self, user_input: str, resume_from_checkpoint: str | None = None) -> str:
        """
        Execute workflow by routing user input through the graph.

        The orchestrator analyzes the request and delegates to appropriate
        specialized agents based on conditional edges. The WorkflowBuilder
        handles execution tracking and state management automatically.

        Args:
            user_input: User's request or query
            resume_from_checkpoint: Optional checkpoint ID to resume from (placeholder for future)

        Returns:
            str: Final response from the workflow
        """

        # Prepare workflow state before execution
        if resume_from_checkpoint:
            restored = await self.restore_from_checkpoint(resume_from_checkpoint)
            if not restored:
                raise WorkflowError(
                    f"Failed to restore from checkpoint: {resume_from_checkpoint}"
                )
        else:
            if not self.workflow_id:
                self.workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
            self.current_round = 0
            self.stall_count = 0
            self.last_response = None
            self.context = {"user_query": user_input}
            self.current_checkpoint_id = None

        self.current_round = (self.current_round or 0) + 1

        result = await self.workflow.run(user_input)

        response_text = (
            _extract_response_text(result.output)
            if getattr(result, "output", None)
            else "No response generated"
        )
        self.last_response = response_text
        return response_text


# Create default workflow instance with checkpoint storage
_checkpoint_storage = settings.create_checkpoint_storage()
workflow = MultiAgentWorkflow(checkpoint_storage=_checkpoint_storage)
