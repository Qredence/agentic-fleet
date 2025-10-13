"""
WorkflowBuilder-based multi-agent workflow implementation.

This module implements the multi-agent workflow using Microsoft Agent Framework's
WorkflowBuilder pattern for graph-based orchestration. This provides native features
like automatic state management, cycle detection, and streaming support.
"""

from typing import Any

from agent_framework import WorkflowBuilder

from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from agenticfleet.config import settings


def _should_delegate_to_researcher(message: Any) -> bool:
    """Check if orchestrator wants to delegate to researcher."""
    if not message:
        return False

    # Extract text from message
    response_text = _extract_response_text(message)

    # Check for delegation to researcher
    return "DELEGATE: researcher" in response_text or "DELEGATE:researcher" in response_text


def _should_delegate_to_coder(message: Any) -> bool:
    """Check if orchestrator wants to delegate to coder."""
    if not message:
        return False

    response_text = _extract_response_text(message)
    return "DELEGATE: coder" in response_text or "DELEGATE:coder" in response_text


def _should_delegate_to_analyst(message: Any) -> bool:
    """Check if orchestrator wants to delegate to analyst."""
    if not message:
        return False

    response_text = _extract_response_text(message)
    return "DELEGATE: analyst" in response_text or "DELEGATE:analyst" in response_text


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


def create_workflow() -> Any:
    """
    Create multi-agent workflow using WorkflowBuilder pattern.

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

    # Build workflow graph
    workflow = (
        WorkflowBuilder(max_iterations=max_rounds)
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

    def __init__(self) -> None:
        """Initialize workflow with WorkflowBuilder pattern."""
        self.workflow = create_workflow()

    async def run(self, user_input: str) -> str:
        """
        Execute workflow by routing user input through the graph.

        The orchestrator analyzes the request and delegates to appropriate
        specialized agents based on conditional edges. The WorkflowBuilder
        handles execution tracking and state management automatically.

        Args:
            user_input: User's request or query

        Returns:
            str: Final response from the workflow
        """
        # Run the workflow with the user input
        result = await self.workflow.run(user_input)

        # Extract final output
        if result.output:
            return _extract_response_text(result.output)

        # Fallback to last output from workflow
        return "No response generated"


# Create default workflow instance
workflow = MultiAgentWorkflow()
