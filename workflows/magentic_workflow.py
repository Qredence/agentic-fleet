"""
Magentic Workflow Implementation

This module implements the Magentic workflow pattern for coordinating multiple
specialized agents in the AgenticFleet system. The workflow uses Microsoft's
Agent Framework to orchestrate agent interactions and manage task delegation.

The Magentic Workflow:
- Registers multiple specialized agents as participants
- Manages communication and coordination between agents
- Handles event streaming for observability
- Enforces execution limits (max rounds, stalls, resets)
- Provides a unified interface for task execution

Architecture:
    User Request → Orchestrator → Specialized Agents → Synthesized Response
                        ↓
                   [Researcher, Coder, Analyst]

Key Features:
- Dynamic agent delegation based on task requirements
- Event-driven architecture for real-time monitoring
- Automatic workflow management (retry, reset, termination)
- Thread-safe conversation context management

Usage:
    from workflows.magentic_workflow import create_magentic_workflow

    workflow = create_magentic_workflow()
    result = await workflow.run("Your task here")
"""

from agent_framework import MagenticBuilder
from agent_framework.openai import OpenAIResponsesClient

from config.settings import settings


def create_magentic_workflow():
    """
    Create the Magentic workflow with all specialized agents.

    This function builds a complete multi-agent workflow following the
    Microsoft Agent Framework's Magentic pattern. It:

    1. Imports all agent factory functions
    2. Creates instances of all specialized agents
    3. Configures the MagenticBuilder with:
       - Agent participants (orchestrator, researcher, coder, analyst)
       - Event handlers for observability
       - Standard manager with execution limits
    4. Returns the built workflow ready for execution

    The workflow uses stable identifiers for participants, which is crucial
    for features like checkpointing and conversation persistence.

    Returns:
        MagenticWorkflow: Configured workflow ready to execute tasks

    Raises:
        ValueError: If configuration is invalid or agents fail to initialize

    Example:
        >>> workflow = create_magentic_workflow()
        >>> result = await workflow.run("Research Python ML libraries")
        >>> print(result)
    """
    # Import agent factory functions
    # These create fully configured agent instances with their tools
    from agents.analyst_agent.agent import create_analyst_agent
    from agents.coder_agent.agent import create_coder_agent
    from agents.orchestrator_agent.agent import create_orchestrator_agent
    from agents.researcher_agent.agent import create_researcher_agent

    # Get workflow configuration from centralized config
    # This includes max_rounds, max_stalls, max_resets, timeout_seconds
    workflow_config = settings.workflow_config.get("workflow", {})

    def on_event(event):
        """
        Handle workflow events for observability and debugging.

        This function is called for every event in the workflow, including:
        - Agent responses
        - Tool invocations
        - Workflow state changes
        - Streaming content deltas

        Args:
            event: Workflow event object from the agent framework
                  Contains event type, agent name, message, and other metadata
        """
        # Get the event type for conditional handling
        event_type = type(event).__name__

        # Handle different types of events with appropriate formatting
        if hasattr(event, "agent_name") and hasattr(event, "response"):
            # Agent response event - show which agent responded
            response_preview = (
                event.response[:150] + "..." if len(event.response) > 150 else event.response
            )
            print(f"🤖 [{event.agent_name}] {response_preview}")

        elif hasattr(event, "message") and event.message:
            # General workflow event - system messages, state changes
            print(f"📋 [Workflow] {event.message}")

        elif hasattr(event, "delta") and event.delta:
            # Streaming content - print without newline for smooth streaming
            print(event.delta, end="", flush=True)

    # Build the Magentic workflow using the builder pattern
    workflow = (
        MagenticBuilder()
        # Register participants with stable identifiers
        # These names are used for agent delegation and must be consistent
        .participants(
            orchestrator=create_orchestrator_agent(),  # Main coordinator
            researcher=create_researcher_agent(),  # Information gathering
            coder=create_coder_agent(),  # Code execution
            analyst=create_analyst_agent(),  # Data analysis
        )
        # Add event handling for real-time observability
        # This allows monitoring of agent interactions and workflow progress
        .on_event(on_event)
        # Configure the standard manager with execution limits
        # This prevents infinite loops and manages workflow lifecycle
        # API key is read from OPENAI_API_KEY environment variable
        .with_standard_manager(
            chat_client=OpenAIResponsesClient(
                model_id=settings.openai_model,
            ),
            max_round_count=workflow_config.get("max_rounds", 10),  # Max conversation rounds
            max_stall_count=workflow_config.get("max_stalls", 3),  # Max rounds without progress
            max_reset_count=workflow_config.get("max_resets", 2),  # Max workflow resets
        )
        # Build and return the configured workflow
        .build()
    )

    return workflow
