"""UI module for Agentic Fleet."""

# Standard library imports
import logging
from importlib.util import find_spec
from typing import Any, Dict, cast

# Initialize logging
logger = logging.getLogger(__name__)

# Apply patch for Chainlit LiteralAI integration if needed
try:
    if find_spec('chainlit') and find_spec('literalai'):
        from chainlit.data.literalai import LiteralDataLayer

        # Store original create_step method
        original_create_step = LiteralDataLayer.create_step

        async def patched_create_step(self, step_dict: Any) -> Any:
            """Patch to fix StepType enum compatibility issues.

            This patches the incorrect step type values to match the required enum values
            in LiteralAI API.

            Args:
                self: The LiteralDataLayer instance
                step_dict: The step dictionary to be sent

            Returns:
                The result of the original create_step method
            """
            # Fix the step type if needed
            if step_dict.get("type") == "system":
                step_dict["type"] = "system_message"
            elif step_dict.get("type") == "user":
                step_dict["type"] = "user_message"
            elif step_dict.get("type") == "assistant":
                step_dict["type"] = "assistant_message"

            # Call original method with fixed step_dict
            return await original_create_step(self, step_dict)

        # Apply the monkey patch - using a safer approach
        if hasattr(LiteralDataLayer, 'create_step'):
            setattr(LiteralDataLayer, 'create_step', patched_create_step)
            logger.info(
                "Applied patch to LiteralDataLayer.create_step for StepType compatibility")

except Exception as e:
    logger.warning(f"Failed to apply LiteralAI patch: {str(e)}")
