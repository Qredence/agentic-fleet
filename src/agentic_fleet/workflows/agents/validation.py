"""Agent and tool validation utilities."""

from __future__ import annotations

from typing import Any

from ...utils.logger import setup_logger

logger = setup_logger(__name__)


def validate_tool(tool: Any) -> bool:
    """Validate that a tool can be parsed by agent-framework.

    Args:
        tool: Tool instance to validate

    Returns:
        True if tool is valid, False otherwise
    """
    try:
        # Check if tool is None (valid - means no tool)
        if tool is None:
            return True

        # Check if tool is a dict (serialized tool)
        if isinstance(tool, dict):
            return True

        # Check if tool is callable (function)
        if callable(tool):
            return True

        # Check if tool has required ToolProtocol attributes
        if hasattr(tool, "name") and hasattr(tool, "description"):
            # Tool implements ToolProtocol but not SerializationMixin
            # This will cause warnings, but we'll log it
            logger.debug(
                f"Tool {type(tool).__name__} implements ToolProtocol but not SerializationMixin. "
                "Consider adding SerializationMixin to avoid parsing warnings."
            )
            return True

        logger.warning(f"Tool {type(tool).__name__} does not match any recognized tool format")
        return False
    except Exception as e:
        logger.warning(f"Error validating tool {type(tool).__name__}: {e}")
        return False
