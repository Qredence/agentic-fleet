"""AutoGen-based models and agents.

This module implements AutoGen-compatible agents and models for AI-powered interactions.
It follows AutoGen's patterns for message handling, configuration, and agent lifecycle management.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Union, Any

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler
)
from autogen_agentchat.agents import (
    AssistantAgent,
    UserProxyAgent
)
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
    AssistantMessage
)
from autogen_ext.models.openai import (
    AzureOpenAIChatCompletionClient,
    OpenAIChatCompletionClient
)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_azure_client() -> AzureOpenAIChatCompletionClient:
    """Create an Azure OpenAI client with proper configuration."""
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )
        
        return AzureOpenAIChatCompletionClient(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=token_provider,
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
            }
        )
    except Exception as e:
        logger.error(f"Failed to create Azure client: {str(e)}")
        raise

def create_cogcache_client() -> OpenAIChatCompletionClient:
    """Create a CogCache client with proper configuration."""
    try:
        return OpenAIChatCompletionClient(
            base_url="https://proxy-api.cogcache.com/v1/",
            api_key=os.getenv("COGCACHE_API_KEY"),
            model=os.getenv("COGCACHE_MODEL", "gpt-4"),
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
            }
        )
    except Exception as e:
        logger.error(f"Failed to create CogCache client: {str(e)}")
        raise

class EnhancedAssistantAgent(AssistantAgent):
    """Enhanced AutoGen assistant agent with improved capabilities."""
    
    def __init__(
        self,
        name: str,
        system_message: str,
        model_client: Optional[ChatCompletionClient] = None,
        **kwargs: Any
    ) -> None:
        """Initialize the enhanced assistant agent."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(
            "Initializing assistant agent",
            extra={
                "agent_name": name,
                "model_client": model_client.__class__.__name__ if model_client else "default"
            }
        )
        model_client = model_client or create_azure_client()
        super().__init__(
            name=name,
            system_message=system_message,
            model_client=model_client,
            **kwargs
        )

    async def process_message(
        self,
        message: Union[str, Dict],
        context: Optional[Any] = None
    ) -> Any:
        """Process incoming messages with enhanced error handling."""
        try:
            self.logger.debug(
                "Processing message",
                extra={
                    "message_type": type(message).__name__,
                    "context_present": context is not None
                }
            )
            result = await super().process_message(message, context)
            self.logger.info(
                "Message processed successfully",
                extra={"result_type": type(result).__name__}
            )
            return result
        except Exception as e:
            self.logger.error(
                "Error processing message",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise

class EnhancedUserProxyAgent(UserProxyAgent):
    """Enhanced AutoGen user proxy agent with improved capabilities."""
    
    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Initialize the enhanced user proxy agent."""
        super().__init__(
            name=name,
            system_message=system_message or "You are a helpful user proxy.",
            **kwargs
        )

    async def process_message(
        self,
        message: Union[str, Dict],
        context: Optional[Any] = None
    ) -> Union[str, Dict]:
        """Process incoming messages with enhanced error handling."""
        try:
            return await super().process_message(message, context)
        except Exception as e:
            logger.exception(f"Error processing message in {self.name}")
            return {
                "type": "error",
                "content": str(e),
                "source": self.name
            }

async def create_agent_team(
    task: str,
    model_client: Optional[ChatCompletionClient] = None
) -> MagenticOneGroupChat:
    """Create a team of agents for collaborative task solving.
    
    Args:
        task: The task to be solved
        model_client: Optional model client (uses Azure by default)
        
    Returns:
        A configured group chat team
    """
    try:
        model_client = model_client or create_azure_client()
        
        # Create agents
        assistant = EnhancedAssistantAgent(
            name="Assistant",
            system_message="You are a helpful AI assistant.",
            model_client=model_client
        )
        
        user_proxy = EnhancedUserProxyAgent(
            name="UserProxy",
            system_message="You are a helpful user proxy."
        )
        
        # Create team
        team = MagenticOneGroupChat(
            participants=[assistant, user_proxy],
            model_client=model_client
        )
        
        return team
        
    except Exception as e:
        logger.error(f"Failed to create agent team: {str(e)}")
        raise

async def main() -> None:
    """Example usage of the AutoGen-based agent system."""
    try:
        # Create team
        team = await create_agent_team("What are fun things to do in Seattle?")
        
        # Run conversation
        async for response in team.run_stream(task="What are fun things to do in Seattle?"):
            if isinstance(response, (str, dict)):
                print(response)
                
    except Exception as e:
        logger.exception("Error in main")
        raise

if __name__ == "__main__":
    asyncio.run(main())
