"""
Application manager for AgenticFleet.

This module provides the main application manager that coordinates:
- Agent team initialization and management
- Configuration handling
- Resource lifecycle management
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from autogen_core.models import ChatCompletionClient
from pydantic import BaseModel

from agentic_fleet.core.agents.base import BaseAgent
from agentic_fleet.core.agents.team_factory import TeamFactory
from agentic_fleet.core.agents.team_manager import TeamManager
from agentic_fleet.config import config_manager

logger = logging.getLogger(__name__)

class ApplicationConfig(BaseModel):
    """Configuration for the application manager."""
    project_root: Path
    debug: bool = False
    log_level: str = "INFO"
    default_team_specialization: str = "general"

class ApplicationManager:
    """
    Main application manager for AgenticFleet.
    
    The application manager:
    1. Initializes and manages agent teams
    2. Handles configuration and resources
    3. Coordinates task execution
    4. Manages application lifecycle
    """

    def __init__(
        self,
        config: ApplicationConfig,
        model_client: Optional[ChatCompletionClient] = None,
    ) -> None:
        """Initialize the application manager.

        Args:
            config: Application configuration
            model_client: The LLM client to use
        """
        self.config = config
        self.model_client = model_client
        
        # Initialize components
        self.team_factory = TeamFactory(model_client=model_client)
        self.active_teams: Dict[str, TeamManager] = {}
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    async def start(self) -> None:
        """Start the application manager."""
        logger.info("Starting application manager")
        
        # Load configurations
        config_manager.load_all()
        
        # Initialize default team if configured
        if self.config.default_team_specialization:
            await self.create_team(self.config.default_team_specialization)

    async def create_team(
        self,
        specialization: str,
        custom_config: Optional[Dict[str, Any]] = None,
        team_id: Optional[str] = None
    ) -> TeamManager:
        """Create a new agent team.

        Args:
            specialization: The team specialization to use
            custom_config: Optional custom configuration
            team_id: Optional specific team ID to use

        Returns:
            The created team manager instance

        Raises:
            ValueError: If team creation fails
        """
        try:
            # Initialize default agents
            available_agents = self._initialize_default_agents()
            
            # Create team using factory
            team = self.team_factory.create_team(
                specialization=specialization,
                available_agents=available_agents,
                custom_config=custom_config
            )
            
            # Generate team ID if not provided
            if not team_id:
                team_id = f"{specialization}_{len(self.active_teams)}"
            
            # Store team
            self.active_teams[team_id] = team
            
            logger.info(f"Created team {team_id} with specialization {specialization}")
            return team

        except Exception as e:
            logger.error(f"Failed to create team: {str(e)}")
            raise ValueError(f"Team creation failed: {str(e)}")

    def _initialize_default_agents(self) -> Dict[str, BaseAgent]:
        """Initialize the default set of agents.

        Returns:
            Dictionary of initialized agents
        """
        from agentic_fleet.core.agents.team import initialize_default_agents
        agents = initialize_default_agents(model_client=self.model_client)
        return {agent.name: agent for agent in agents}

    async def execute_task(
        self,
        task: str,
        team_id: Optional[str] = None,
        specialization: Optional[str] = None
    ) -> Any:
        """Execute a task using an agent team.

        Args:
            task: The task to execute
            team_id: Optional specific team ID to use
            specialization: Optional team specialization to use if creating new team

        Returns:
            Task execution results

        Raises:
            ValueError: If no team is available and none can be created
        """
        # Get or create team
        team = None
        if team_id and team_id in self.active_teams:
            team = self.active_teams[team_id]
        elif specialization:
            team = await self.create_team(specialization)
        elif self.active_teams:
            # Use first available team
            team = next(iter(self.active_teams.values()))
        else:
            # Create default team
            team = await self.create_team(self.config.default_team_specialization)

        if not team:
            raise ValueError("No team available and failed to create one")

        # Execute task
        try:
            return await team.execute_task(task)
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            raise

    def get_team(self, team_id: str) -> Optional[TeamManager]:
        """Get a team by ID.

        Args:
            team_id: ID of the team to retrieve

        Returns:
            The team manager if found, None otherwise
        """
        return self.active_teams.get(team_id)

    def list_teams(self) -> List[Dict[str, Any]]:
        """List all active teams.

        Returns:
            List of team information dictionaries
        """
        return [
            {
                "id": team_id,
                "name": team.config.name,
                "description": team.config.description,
                "metrics": team.get_metrics(),
                "agent_status": team.get_agent_status()
            }
            for team_id, team in self.active_teams.items()
        ]

    async def shutdown(self) -> None:
        """Shut down the application manager and clean up resources."""
        logger.info("Shutting down application manager")
        
        # Clean up teams
        for team in self.active_teams.values():
            try:
                await team.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up team: {str(e)}")
        
        self.active_teams.clear()
        logger.info("Application manager shutdown complete")
