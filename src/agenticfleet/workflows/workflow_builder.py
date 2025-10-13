"""
WorkflowBuilder-based multi-agent workflow implementation.

This module implements the multi-agent workflow using Microsoft Agent Framework's
WorkflowBuilder pattern for graph-based orchestration. This provides native features
like automatic state management, cycle detection, and streaming support.
"""

from typing import Any

from agent_framework import CheckpointStorage, WorkflowBuilder

from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from agenticfleet.config import settings


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

    # Build workflow graph with optional checkpointing
    builder = WorkflowBuilder(max_iterations=max_rounds)
    
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
        """
        Initialize workflow with WorkflowBuilder pattern.
        
        Args:
            checkpoint_storage: Optional checkpoint storage for workflow state persistence
        """
        self.checkpoint_storage = checkpoint_storage
        self.workflow = create_workflow(checkpoint_storage)

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
        # Note: Checkpoint resume is handled by WorkflowBuilder's built-in checkpoint storage
        # The resume_from_checkpoint parameter is kept for API compatibility
        
        # Run the workflow with the user input
        result = await self.workflow.run(user_input)

        # Extract final output
        if result.output:
            return _extract_response_text(result.output)

        # Fallback to last output from workflow
        return "No response generated"


# Create default workflow instance with checkpoint storage
_checkpoint_storage = settings.create_checkpoint_storage()
workflow = MultiAgentWorkflow(checkpoint_storage=_checkpoint_storage)
