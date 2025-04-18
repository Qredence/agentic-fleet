"""MCP factory module.

This module provides a factory for creating MCP instances based on configuration.
"""

import logging
from typing import Any, Dict, Optional, Type

from agentic_fleet.config.llm_config_manager import llm_config_manager
from agentic_fleet.mcp_pool.agent_coordinator_mcp import AgentCoordinatorMCP
from agentic_fleet.mcp_pool.base_mcp import BaseMCP

logger = logging.getLogger(__name__)

# Registry of MCP types
MCP_REGISTRY: Dict[str, Type[BaseMCP]] = {
    "base_mcp": BaseMCP,
    "agent_coordinator_mcp": AgentCoordinatorMCP,
}


def create_mcp(mcp_id: str, **kwargs: Any) -> Optional[BaseMCP]:
    """Create an MCP instance based on the configuration.
    
    Args:
        mcp_id: The ID of the MCP configuration to use
        **kwargs: Additional parameters to pass to the MCP constructor
        
    Returns:
        An MCP instance, or None if the MCP configuration is not found
    """
    try:
        # Get the MCP configuration
        mcp_configs = llm_config_manager.config.get("mcp", {})
        if mcp_id not in mcp_configs:
            logger.warning(f"MCP configuration not found: {mcp_id}")
            return None
            
        mcp_config = mcp_configs[mcp_id]
        
        # Get the MCP type
        mcp_type = mcp_config.get("type", "base_mcp")
        if mcp_type not in MCP_REGISTRY:
            logger.warning(f"Unknown MCP type: {mcp_type}")
            return None
            
        # Create the MCP instance
        mcp_class = MCP_REGISTRY[mcp_type]
        mcp = mcp_class(
            name=mcp_config.get("name", mcp_id),
            description=mcp_config.get("description", ""),
            **{**mcp_config, **kwargs}  # Merge config and kwargs
        )
        
        logger.info(f"Created MCP: {mcp_id} ({mcp_type})")
        return mcp
    except Exception as e:
        logger.error(f"Error creating MCP {mcp_id}: {e}")
        return None


def register_mcp_type(mcp_type: str, mcp_class: Type[BaseMCP]) -> None:
    """Register a new MCP type.
    
    Args:
        mcp_type: The type name to register
        mcp_class: The MCP class to register
    """
    MCP_REGISTRY[mcp_type] = mcp_class
    logger.info(f"Registered MCP type: {mcp_type}")


def get_available_mcp_types() -> Dict[str, str]:
    """Get the available MCP types.
    
    Returns:
        A dictionary mapping MCP type names to their class names
    """
    return {
        mcp_type: mcp_class.__name__
        for mcp_type, mcp_class in MCP_REGISTRY.items()
    }


def get_available_mcp_configs() -> Dict[str, Dict[str, Any]]:
    """Get the available MCP configurations.
    
    Returns:
        A dictionary mapping MCP IDs to their configurations
    """
    return llm_config_manager.config.get("mcp", {})
