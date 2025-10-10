from azure.ai.agent.client import AzureAIAgentClient

from config.settings import settings


def create_orchestrator_agent(client: AzureAIAgentClient, context_provider):
    """
    Create the Orchestrator agent.

    This function:
    - Loads configuration from agents/orchestrator_agent/agent_config.yaml
    - Creates an agent with the provided AzureAIAgentClient
    - Returns a fully configured agent instance

    Args:
        client: The AzureAIAgentClient instance.

    Returns:
        AIAgent: Configured orchestrator agent

    Raises:
        ValueError: If required configuration is missing
        FileNotFoundError: If agent_config.yaml is not found
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("agents/orchestrator_agent")
    agent_config = config.get("agent", {})

    # Create the agent
    agent = client.create_agent(
        name=agent_config.get("name", "orchestrator"),
        instructions=config.get("system_prompt", ""),
        memory=context_provider,
    )

    return agent
