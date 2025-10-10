from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from config.settings import settings


def create_orchestrator_agent() -> ChatAgent:
    """
    Create the Magentic Orchestrator agent using OpenAI Responses API.

    Returns:
        ChatAgent: Configured orchestrator agent
    """
    # Load orchestrator-specific configuration
    config = settings.load_agent_config("agents/orchestrator_agent")
    agent_config = config.get("agent", {})

    # Create OpenAI Responses client
    # API key is read from OPENAI_API_KEY environment variable
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )

    agent = ChatAgent(
        name=agent_config.get("name", "orchestrator"),
        instructions=config.get("system_prompt", ""),
        chat_client=client,
    )

    return agent
