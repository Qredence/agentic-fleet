"""
AgenticFleet Configuration Package
==================================

This package manages all configuration for the AgenticFleet system.

Components:
    - settings: Global settings management with environment variables
    - workflow_config.yaml: Workflow execution parameters
    - Agent-specific configurations in each agent directory

Configuration Pattern:
    - Environment variables loaded via .env file
    - YAML configuration files for structured settings
    - Two-tier config: central workflow + individual agent configs
    - Pydantic models for validation and type safety

Usage:
    from config.settings import settings

    # Access configuration
    api_key = settings.openai_api_key
    workflow_config = settings.workflow_config
    agent_config = settings.load_agent_config("orchestrator_agent")
"""

from config.settings import settings

__all__ = ["settings"]
