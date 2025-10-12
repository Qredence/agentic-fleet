"""
AgenticFleet Configuration Package
==================================

This package manages all configuration for the AgenticFleet system.

Components:
    - settings: Global settings management with environment variables
    - workflow.yaml: Workflow execution parameters
    - Agent-specific configurations in each agent directory

Configuration Pattern:
    - Environment variables loaded via .env file
    - YAML configuration files for structured settings
    - Two-tier config: central workflow + individual agent configs
    - Type-safe configuration with Pydantic validation

Usage:
    from agenticfleet.config import settings

    # Access configuration
    api_key = settings.openai_api_key
    workflow_config = settings.workflow_config
    agent_config = settings.load_agent_config("orchestrator")
"""

from agenticfleet.config.settings import settings

__all__ = ["settings"]
