"""Factory for creating Magentic workflows from YAML configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from agent_framework import ChatAgent, HostedCodeInterpreterTool
from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.api.models import WorkflowConfig, WorkflowsConfig

if TYPE_CHECKING:
    from agent_framework import Workflow

logger = logging.getLogger(__name__)


class WorkflowFactory:
    """Factory for creating Magentic workflows from YAML configuration."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize the workflow factory.

        Args:
            config_path: Path to the YAML configuration file.
                        Defaults to config/workflows.yaml at project root.

        """
        if config_path is None:
            # Default to config/workflows.yaml at project root
            # Navigate from src/agenticfleet/api -> project root -> config
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "workflows.yaml"

        self.config_path = Path(config_path)
        self._config: WorkflowsConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate workflow configuration from YAML."""
        if not self.config_path.exists():
            msg = f"Configuration file not found: {self.config_path}"
            raise FileNotFoundError(msg)

        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)

        # Validate with Pydantic
        self._config = WorkflowsConfig(**raw_config)
        logger.info(f"Loaded {len(self._config.workflows)} workflow(s) from {self.config_path}")

    def list_available_workflows(self) -> list[dict[str, Any]]:
        """List all available workflows with metadata.

        Returns:
            List of workflow metadata dictionaries containing:
            - id: workflow identifier
            - name: human-readable name
            - description: brief description
            - factory: factory function name
            - agent_count: number of agents

        """
        if self._config is None:
            return []
        return self._config.list_workflows()

    def get_workflow_config(self, workflow_id: str) -> WorkflowConfig:
        """Get configuration for a specific workflow.

        Args:
            workflow_id: ID of the workflow to retrieve

        Returns:
            WorkflowConfig for the specified workflow

        Raises:
            ValueError: If workflow_id is not found

        """
        if self._config is None:
            msg = "No configuration loaded"
            raise ValueError(msg)

        config = self._config.get_workflow(workflow_id)
        if config is None:
            msg = f"Workflow '{workflow_id}' not found in configuration"
            raise ValueError(msg)

        return config

    def create_from_yaml(self, workflow_id: str) -> Workflow:
        """Create a workflow from YAML configuration.

        Args:
            workflow_id: ID of the workflow to create

        Returns:
            Configured Workflow instance

        Raises:
            ValueError: If workflow_id is not found or factory function fails

        """
        config = self.get_workflow_config(workflow_id)

        # Import workflow factory functions
        from agenticfleet import workflow as workflow_module

        # Get the factory function
        factory_name = config.factory
        if not hasattr(workflow_module, factory_name):
            msg = f"Factory function '{factory_name}' not found in workflow module"
            raise ValueError(msg)

        factory_func = getattr(workflow_module, factory_name)

        # Build arguments for factory function based on workflow type
        if workflow_id == "collaboration":
            kwargs = self._build_collaboration_args(config)
        elif workflow_id == "magentic_fleet":
            kwargs = self._build_magentic_fleet_args(config)
        else:
            msg = f"Unknown workflow type: {workflow_id}"
            raise ValueError(msg)

        logger.info(f"Creating workflow '{workflow_id}' using {factory_name}")
        workflow: Workflow = factory_func(**kwargs)
        return workflow

    def _build_collaboration_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for collaboration workflow factory.

        Args:
            config: Workflow configuration

        Returns:
            Dictionary of arguments for create_collaboration_workflow()

        """
        kwargs: dict[str, Any] = {}

        # Agent instructions
        if "researcher" in config.agents:
            kwargs["researcher_instructions"] = config.agents["researcher"].instructions
        if "coder" in config.agents:
            kwargs["coder_instructions"] = config.agents["coder"].instructions
        if "reviewer" in config.agents:
            kwargs["reviewer_instructions"] = config.agents["reviewer"].instructions

        # Manager configuration
        kwargs["manager_instructions"] = config.manager.instructions
        kwargs["max_round_count"] = config.manager.max_round_count
        kwargs["max_stall_count"] = config.manager.max_stall_count
        kwargs["max_reset_count"] = config.manager.max_reset_count

        # Models (use first agent's model as default)
        first_agent = next(iter(config.agents.values()))
        kwargs["participant_model"] = first_agent.model
        kwargs["manager_model"] = config.manager.model

        return kwargs

    def _build_magentic_fleet_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for magentic fleet workflow factory.

        Args:
            config: Workflow configuration

        Returns:
            Dictionary of arguments for create_magentic_fleet_workflow()

        """
        kwargs: dict[str, Any] = {}

        # Agent instructions and models
        for agent_name, agent_config in config.agents.items():
            kwargs[f"{agent_name}_instructions"] = agent_config.instructions
            kwargs[f"{agent_name}_model"] = agent_config.model

        # Manager configuration
        kwargs["manager_instructions"] = config.manager.instructions
        kwargs["manager_model"] = config.manager.model
        kwargs["max_round_count"] = config.manager.max_round_count
        kwargs["max_stall_count"] = config.manager.max_stall_count
        kwargs["max_reset_count"] = config.manager.max_reset_count

        return kwargs

    def create_agent_from_config(
        self,
        agent_name: str,
        agent_config: dict[str, Any],
    ) -> ChatAgent:
        """Create a ChatAgent from configuration dictionary.

        This method provides more granular control over agent creation
        when not using the workflow factory functions.

        Args:
            agent_name: Name for the agent
            agent_config: Agent configuration dictionary

        Returns:
            Configured ChatAgent instance

        """
        # Create OpenAI client with reasoning configuration
        reasoning_config = agent_config.get("reasoning", {})
        client = OpenAIResponsesClient(
            model_id=agent_config["model"],
            reasoning=reasoning_config if reasoning_config else None,
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_tokens", 4096),
            store=agent_config.get("store", True),
        )

        # Collect tools
        tools = []
        tool_names = agent_config.get("tools", [])
        for tool_name in tool_names:
            if tool_name == "HostedCodeInterpreterTool":
                tools.append(HostedCodeInterpreterTool())
            else:
                logger.warning(f"Unknown tool '{tool_name}' for agent '{agent_name}'")

        # Create agent
        agent = ChatAgent(
            name=agent_name,
            description=agent_config.get("description", ""),
            instructions=agent_config["instructions"],
            chat_client=client,
            tools=tuple(tools) if tools else None,
        )

        logger.info(f"Created agent '{agent_name}' with model {agent_config['model']}")
        return agent
