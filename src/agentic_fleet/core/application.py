"""Core application module for AgenticFleet."""

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv

from agentic_fleet.backend.application_manager import ApplicationManager
from agentic_fleet.backend.chainlit_components.chat_settings import ChatSettings
from agentic_fleet.config import Settings


class AgentInitializationError(Exception):
    """Exception raised when agent initialization fails."""
    pass


load_dotenv()
logger = logging.getLogger(__name__)

# Team configurations for different use cases
TEAM_CONFIGURATIONS = {
    "default": {
        "name": "Default Team",
        "description": "General-purpose agent team with web, file, and code capabilities",
        "agents": ["WebSurfer", "FileSurfer", "Coder", "Executor"],
        "max_rounds": 50,
        "max_stalls": 5,
    },
    "code_focused": {
        "name": "Code Team",
        "description": "Team focused on code generation and execution",
        "agents": ["FileSurfer", "Coder", "Executor"],
        "max_rounds": 30,
        "max_stalls": 3,
    },
    "research": {
        "name": "Research Team",
        "description": "Team focused on web research and information gathering",
        "agents": ["WebSurfer", "FileSurfer"],
        "max_rounds": 40,
        "max_stalls": 4,
    },
}


def create_chat_profile(
    settings: Optional[Settings] = None,
    team_config: str = "default",
    model_client: Optional[AzureOpenAIChatCompletionClient] = None,
) -> Dict[str, Any]:
    """Create a chat profile with specified configuration.

    Args:
        settings: Application settings
        team_config: Team configuration key
        model_client: Azure OpenAI model client

    Returns:
        Dict containing chat profile configuration
    """
    settings = settings or Settings()
    config = TEAM_CONFIGURATIONS.get(team_config, TEAM_CONFIGURATIONS["default"])

    return {
        "name": config["name"],
        "description": config["description"],
        "max_rounds": config["max_rounds"],
        "max_stalls": config["max_stalls"],
        "model_client": model_client,
        "team_config": team_config,
    }


def create_chat_profile_with_code_execution(
    workspace_dir: str,
    settings: Optional[Settings] = None,
    team_config: str = "default",
    execution_timeout: int = 300,
) -> Dict[str, Any]:
    """Create a chat profile with code execution capabilities.

    Args:
        workspace_dir: Directory for code execution
        settings: Application settings
        team_config: Team configuration key
        execution_timeout: Code execution timeout in seconds

    Returns:
        Dict containing chat profile with code execution configuration
    """
    profile = create_chat_profile(settings, team_config)
    profile["workspace_dir"] = workspace_dir
    profile["execution_timeout"] = execution_timeout
    return profile


class ApplicationManager:
    """Manages application lifecycle and resources."""

    def __init__(self, settings: Settings):
        """Initialize application manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._initialized = False
        self.agent_team = None
        self.teams: Dict[str, MagenticOneGroupChat] = {}

    async def start(self) -> None:
        """Start the application and initialize resources."""
        if self._initialized:
            logger.warning("Application already initialized")
            return

        try:
            logger.info("Starting application...")
            # Initialize resources here
            self._initialized = True
            logger.info("Application started successfully")

        except Exception as e:
            logger.error(f"Failed to start application: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop the application and cleanup resources."""
        if not self._initialized:
            logger.warning("Application not initialized")
            return

        try:
            logger.info("Stopping application...")
            # Cleanup resources here
            self._initialized = False
            logger.info("Application stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop application: {str(e)}")
            raise

    async def process_message(self, message: str, settings: ChatSettings) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """Process a message using the current agent team.

        Args:
            message: The message to process
            settings: Current chat settings

        Yields:
            Response chunks from the agent team
        """
        if not self._initialized:
            raise RuntimeError("Application not initialized")

        if not self.agent_team:
            # Initialize agent team if not already done
            self.agent_team = await self.initialize_agent_team()

        try:
            # Validate agent roles
            if any(agent.role not in [self.settings.assistant_role, self.settings.coder_role] 
                   for agent in self.agent_team.agents):
                raise AgentInitializationError("Invalid agent role configuration")

            # Process message through agent team
            async for response in self.agent_team.process_chat(message):
                yield response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            yield {"type": "error", "message": str(e)}

    async def initialize_agent_team(self) -> MagenticOneGroupChat:
        """Initialize the agent team with current settings.

        Returns:
            Configured agent team
        """
        try:
            model_client = AzureOpenAIChatCompletionClient(
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                api_version=self.settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                deployment_name=self.settings.AZURE_OPENAI_DEPLOYMENT,
                model=self.settings.AZURE_OPENAI_MODEL,
            )

            # Create agent team using Magentic-One pattern
            team = await self.create_agent_team(model_client)
            return team

        except Exception as e:
            logger.error(f"Failed to initialize agent team: {str(e)}")
            raise

    async def create_agent_team(self, model_client: AzureOpenAIChatCompletionClient) -> MagenticOneGroupChat:
        """Create and configure the agent team.

        Args:
            model_client: Azure OpenAI model client

        Returns:
            Configured agent team
        """
        # Implementation of agent team creation using Magentic-One pattern
        # This will be implemented based on the specific requirements
        pass

    async def create_team(
        self,
        profile: Dict[str, Any],
        model_client: Optional[AzureOpenAIChatCompletionClient] = None,
    ) -> MagenticOneGroupChat:
        """Create a new agent team based on profile configuration.

        Args:
            profile: Chat profile configuration
            model_client: Azure OpenAI model client

        Returns:
            Configured agent team
        """
        try:
            agents = []
            config = TEAM_CONFIGURATIONS[profile.get("team_config", "default")]

            for agent_type in config["agents"]:
                if agent_type == "WebSurfer":
                    agents.append(
                        MultimodalWebSurfer(
                            name="WebSurfer",
                            model_client=model_client,
                            description="Expert web surfer agent",
                            start_page=self.settings.DEFAULT_START_PAGE,
                            headless=True,
                            debug_dir="./files/debug",
                        )
                    )
                elif agent_type == "FileSurfer":
                    agents.append(
                        FileSurfer(
                            name="FileSurfer",
                            model_client=model_client,
                            description="Expert file system navigator",
                        )
                    )
                elif agent_type == "Coder":
                    agents.append(
                        MagenticOneCoderAgent(
                            name="Coder",
                            model_client=model_client,
                            system_message="""
                            You are a Principal Software Engineer. Your responsibilities include:
                            - Writing production-grade code
                            - Implementing best practices
                            - Performing code reviews
                            - Writing comprehensive tests
                            - Documenting architectural decisions
                            """,
                            code_executor=LocalCommandLineCodeExecutor(
                                work_dir=profile.get("workspace_dir", "./workspace"),
                                timeout=profile.get("execution_timeout", 300),
                            )
                        )
                    )
                elif agent_type == "Executor":
                    executor = LocalCommandLineCodeExecutor(
                        work_dir=profile.get("workspace_dir", "./workspace"),
                        timeout=profile.get("execution_timeout", 300),
                    )
                    agents.append(
                        CodeExecutorAgent(
                            name="Executor",
                            code_executor=executor,
                            description="Expert code execution agent",
                        )
                    )
                elif agent_type == "Assistant":
                    agents.append(
                        AssistantAgent(
                            name="Assistant",
                            model_client=model_client,
                            system_message="""
                            You are a Senior Solution Architect. Your responsibilities include:
                            - Analyzing user requirements
                            - Validating technical feasibility
                            - Coordinating with coding agent
                            - Ensuring security best practices
                            - Communicating solutions to users
                            """
                        )
                    )

            team = MagenticOneGroupChat(
                participants=agents,
                model_client=model_client,
                max_turns=profile.get("max_rounds", 50),
                max_stalls=profile.get("max_stalls", 5),
            )

            team_id = f"{profile['team_config']}_{len(self.teams)}"
            self.teams[team_id] = team
            return team

        except Exception as e:
            logger.error(f"Failed to create team: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up application resources."""
        for team in self.teams.values():
            try:
                await team.cleanup()
            except Exception as e:
                logger.error(f"Error during team cleanup: {str(e)}")


async def create_application(settings: Optional[Settings] = None) -> ApplicationManager:
    """Create and initialize application manager.

    Args:
        settings: Application settings

    Returns:
        Initialized application manager
    """
    app = ApplicationManager(settings)
    return app


async def stream_text(text: str) -> List[str]:
    """Stream text content word by word.

    Args:
        text: Text to stream

    Returns:
        List of words from the text
    """
    return text.split()
