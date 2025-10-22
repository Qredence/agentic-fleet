"""YAML-based workflow configuration loader for AgenticFleet.

This module provides utilities to define Magentic workflows declaratively using YAML files,
making it easier to configure and manage multi-agent orchestration without writing Python code.
"""

from pathlib import Path
from typing import Any

import yaml
from agent_framework import AgentProtocol, ChatAgent
from agent_framework.openai import OpenAIChatClient, OpenAIResponsesClient

from agenticfleet.core.logging import get_logger
from agenticfleet.fleet.callbacks import ConsoleCallbacks
from agenticfleet.fleet.fleet_builder import FleetBuilder

logger = get_logger(__name__)


def load_workflow_from_yaml(yaml_path: str | Path) -> dict[str, Any]:
    """
    Load workflow configuration from YAML file.

    Args:
        yaml_path: Path to YAML configuration file

    Returns:
        Parsed workflow configuration dictionary
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow configuration not found: {yaml_path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded workflow configuration from {yaml_path}")
    return config


def create_agent_from_config(agent_config: dict[str, Any]) -> ChatAgent:
    """
    Create a ChatAgent from YAML configuration.

    Args:
        agent_config: Agent configuration dictionary

    Returns:
        Configured ChatAgent instance
    """
    name = agent_config["name"]
    description = agent_config.get("description", "")
    instructions = agent_config.get("instructions", "")
    model = agent_config.get("model", "gpt-5-mini")
    tools_config = agent_config.get("tools", [])

    # Create chat client based on model
    chat_client: OpenAIChatClient | OpenAIResponsesClient
    if "search" in model.lower():
        chat_client = OpenAIChatClient(model_id=model)
    else:
        chat_client = OpenAIResponsesClient(model_id=model)

    # Parse tools
    tools: list[Any] = []
    # Tool loading can be extended here as needed
    # Example: load tools from agent config YAML files
    for tool_config in tools_config:
        # Tools should be loaded via agent factory pattern from agent-specific configs
        pass

    agent = ChatAgent(
        name=name,
        description=description,
        instructions=instructions,
        chat_client=chat_client,
        tools=tools if tools else None,
    )

    logger.info(f"Created agent '{name}' with model {model}")
    return agent


def build_workflow_from_config(
    config: dict[str, Any],
    console_callbacks: ConsoleCallbacks | None = None,
) -> Any:
    """
    Build a Magentic workflow from YAML configuration.

    Args:
        config: Workflow configuration dictionary
        console_callbacks: Optional console callbacks for observability

    Returns:
        Configured workflow ready for execution
    """
    # Create agents
    agents: dict[str, AgentProtocol] = {}
    for agent_config in config.get("agents", []):
        agent = create_agent_from_config(agent_config)
        agents[agent_config["name"]] = agent

    logger.info(f"Created {len(agents)} agents: {list(agents.keys())}")

    # Build workflow using FleetBuilder
    builder = FleetBuilder(console_callbacks=console_callbacks or ConsoleCallbacks())
    builder = builder.with_agents(agents)

    # Configure manager
    manager_config = config.get("manager", {})
    manager_model = manager_config.get("model", "gpt-5-mini")
    manager_instructions = manager_config.get("instructions")
    builder = builder.with_manager(instructions=manager_instructions, model=manager_model)

    # Add observability
    callbacks_config = config.get("callbacks", {})
    streaming_enabled = callbacks_config.get("streaming_enabled", True)
    log_progress = callbacks_config.get("log_progress_ledger", True)
    if streaming_enabled or log_progress:
        builder = builder.with_observability()

    # Add checkpointing if enabled
    checkpointing_config = config.get("checkpointing", {})
    if checkpointing_config.get("enabled", False):
        from agent_framework import FileCheckpointStorage

        storage_path = checkpointing_config.get("storage_path", "./checkpoints")
        storage = FileCheckpointStorage(storage_path)
        builder = builder.with_checkpointing(storage)
        logger.info(f"Enabled checkpointing at {storage_path}")

    # Add plan review if enabled
    plan_review_config = config.get("plan_review", {})
    if plan_review_config.get("enabled", False):
        builder = builder.with_plan_review(enabled=True)
        logger.info("Enabled plan review (HITL)")

    workflow = builder.build()
    logger.info(f"Built workflow: {config.get('name', 'Unnamed')}")

    return workflow


def load_and_build_workflow(
    yaml_path: str | Path,
    console_callbacks: ConsoleCallbacks | None = None,
) -> Any:
    """
    Load YAML configuration and build workflow in one step.

    Args:
        yaml_path: Path to YAML configuration file
        console_callbacks: Optional console callbacks for observability

    Returns:
        Configured workflow ready for execution
    """
    config = load_workflow_from_yaml(yaml_path)
    return build_workflow_from_config(config, console_callbacks)
