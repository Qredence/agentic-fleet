"""Runtime for HaxUI backend with Fleet and Workflow integration."""

from __future__ import annotations

import logging
from typing import Any

from agenticfleet.config.settings import Settings
from agenticfleet.fleet import create_default_fleet
from agenticfleet.haxui.models import EntityInfo
from agenticfleet.workflows.workflow_as_agent import create_workflow_agent

logger = logging.getLogger(__name__)


def build_entity_catalog() -> tuple[list[EntityInfo], list[EntityInfo]]:
    """
    Build catalog of available agents and workflows.

    Returns:
        Tuple of (agents, workflows) where each is a list of EntityInfo objects
    """
    agents: list[EntityInfo] = []
    workflows: list[EntityInfo] = []

    # Add Magentic Fleet workflow
    try:
        magentic_fleet_info = EntityInfo(
            id="magentic_fleet",
            type="workflow",
            name="Magentic Fleet Orchestration",
            framework="microsoft-agent-framework",
            description="Multi-agent orchestration using Magentic One pattern with manager and specialist agents",
            metadata={
                "pattern": "magentic_one",
                "agents": ["researcher", "coder", "analyst"],
                "orchestrator": "manager",
            },
            executors=["manager", "researcher", "coder", "analyst"],
            start_executor_id="manager",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "User query to process"}
                },
                "required": ["query"],
            },
        )
        workflows.append(magentic_fleet_info)
    except Exception as e:
        logger.warning(f"Failed to register magentic_fleet: {e}")

    # Add workflow_as_agent (reflection pattern)
    try:
        workflow_as_agent_info = EntityInfo(
            id="workflow_as_agent",
            type="workflow",
            name="Reflection Workflow (Worker + Reviewer)",
            framework="microsoft-agent-framework",
            description="Worker generates responses, Reviewer evaluates quality. Iterates until approval.",
            metadata={
                "pattern": "reflection",
                "quality_assurance": True,
                "executors": ["worker", "reviewer"],
            },
            executors=["worker", "reviewer"],
            start_executor_id="worker",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "User query to process"},
                    "worker_model": {
                        "type": "string",
                        "description": "Model for Worker executor",
                        "default": "gpt-4.1-nano",
                    },
                    "reviewer_model": {
                        "type": "string",
                        "description": "Model for Reviewer executor",
                        "default": "gpt-4.1",
                    },
                },
                "required": ["query"],
            },
        )
        workflows.append(workflow_as_agent_info)
    except Exception as e:
        logger.warning(f"Failed to register workflow_as_agent: {e}")

    return agents, workflows


class FleetRuntime:
    """
    Runtime for managing Fleet and Workflow instances.

    Provides lazy initialization of agents and workflows to avoid startup delays.
    """

    def __init__(self) -> None:
        """Initialize the runtime with lazy loading."""
        self._magentic_fleet: Any = None
        self._workflow_as_agent: Any = None
        self._initialized = False
        self._settings = Settings()

    async def ensure_initialised(self) -> None:
        """Ensure runtime is initialized (idempotent)."""
        if self._initialized:
            return

        logger.info("Initializing FleetRuntime...")

        # Initialize Magentic Fleet (lazy)
        try:
            self._magentic_fleet = None  # Will be created on-demand
            logger.info("Magentic Fleet registered (lazy)")
        except Exception as e:
            logger.error(f"Failed to initialize Magentic Fleet: {e}")

        # Initialize workflow_as_agent (lazy)
        try:
            self._workflow_as_agent = None  # Will be created on-demand
            logger.info("Workflow as Agent registered (lazy)")
        except Exception as e:
            logger.error(f"Failed to initialize workflow_as_agent: {e}")

        self._initialized = True
        logger.info("FleetRuntime initialized")

    def get_magentic_fleet(self) -> Any:
        """Get or create Magentic Fleet instance."""
        if self._magentic_fleet is None:
            logger.info("Creating Magentic Fleet instance...")
            self._magentic_fleet = create_default_fleet()
        return self._magentic_fleet

    def get_workflow_as_agent(
        self, worker_model: str = "gpt-4.1-nano", reviewer_model: str = "gpt-4.1"
    ) -> Any:
        """
        Get or create workflow_as_agent instance.

        Args:
            worker_model: Model ID for Worker executor
            reviewer_model: Model ID for Reviewer executor

        Returns:
            Workflow agent instance
        """
        # Always create a new instance with specified models
        logger.info(f"Creating workflow_as_agent (worker={worker_model}, reviewer={reviewer_model})")
        return create_workflow_agent(worker_model=worker_model, reviewer_model=reviewer_model)
