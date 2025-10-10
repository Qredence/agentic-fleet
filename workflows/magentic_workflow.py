"""
Magentic Workflow Implementation

This module implements the Magentic workflow pattern for coordinating multiple
specialized agents in the AgenticFleet system. The workflow uses Microsoft's
Agent Framework to orchestrate agent interactions and manage task delegation.

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
    from workflows.magentic_workflow import run_workflow

    result = await run_workflow("Your task here")
"""

import logging

from azure.ai.agent.client import AzureAIAgentClient
from azure.identity import AzureCliCredential

from config.settings import settings
from context_provider.mem0_context_provider import Mem0ContextProvider

logger = logging.getLogger(__name__)


async def run_workflow(user_input: str):
    """
    Run the Magentic workflow with all specialized agents.

    This function:
    1. Creates an AzureAIAgentClient and Mem0ContextProvider
    2. Creates instances of all specialized agents
    3. Runs the orchestration loop where the orchestrator delegates tasks
    4. Returns the final result

    Args:
        user_input: The user's task.

    Returns:
        str: The final result from the workflow.
    """
    # Create AzureAIAgentClient and Mem0ContextProvider
    client = AzureAIAgentClient(
        endpoint=settings.azure_ai_project_endpoint,
        credential=AzureCliCredential(),
    )
    context_provider = Mem0ContextProvider()

    # Import agent factory functions
    from agents.analyst_agent.agent import create_analyst_agent
    from agents.coder_agent.agent import create_coder_agent
    from agents.orchestrator_agent.agent import create_orchestrator_agent
    from agents.researcher_agent.agent import create_researcher_agent

    # Create agent instances
    orchestrator = create_orchestrator_agent(client, context_provider)
    researcher = create_researcher_agent(client, context_provider)
    coder = create_coder_agent(client, context_provider)
    analyst = create_analyst_agent(client, context_provider)

    agents = {
        "orchestrator": orchestrator,
        "researcher": researcher,
        "coder": coder,
        "analyst": analyst,
    }

    # Start the conversation with the user's input
    conversation = [{"role": "user", "content": user_input}]
    context_provider.add(f"User: {user_input}")

    # Orchestration loop
    for _ in range(settings.workflow_config.get("workflow", {}).get("max_rounds", 10)):
        # Get memory for the conversation
        memory = context_provider.get(user_input)

        # Get the next agent to run from the orchestrator
        orchestrator_response = await orchestrator.run(conversation, memory=memory)
        next_agent_name = orchestrator_response.text.strip().lower()

        if next_agent_name in agents:
            next_agent = agents[next_agent_name]
            logger.info(f"Delegating to {next_agent_name}")

            # Run the selected agent
            agent_response = await next_agent.run(conversation, memory=memory)
            conversation.append({"role": "assistant", "content": agent_response.text})
            context_provider.add(f"{next_agent_name}: {agent_response.text}")
        else:
            # If the orchestrator doesn't delegate, assume it's the final answer
            context_provider.add(f"Orchestrator: {orchestrator_response.text}")
            return orchestrator_response.text

    return "Workflow finished due to max rounds."