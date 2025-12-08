"""DSPy operations service for AgenticFleet API.

Provides business logic for DSPy module operations including compilation,
caching, and introspection.
"""

import inspect
import logging
from typing import Any

import dspy

from agentic_fleet.utils.compiler import clear_cache, get_cache_info
from agentic_fleet.workflows.supervisor import SupervisorWorkflow

logger = logging.getLogger(__name__)


class DSPyService:
    """Service for DSPy operations.

    Encapsulates business logic for DSPy-related operations,
    separated from HTTP handling concerns.
    """

    def __init__(self, workflow: SupervisorWorkflow) -> None:
        """Initialize the service with a workflow instance.

        Args:
            workflow: The SupervisorWorkflow instance.
        """
        self.workflow = workflow

    def get_predictor_prompts(self) -> dict[str, Any]:
        """Extract prompts from all DSPy predictors.

        Returns:
            Dictionary mapping predictor names to their prompt details.

        Raises:
            ValueError: If the workflow has no DSPy reasoner.
        """
        if not self.workflow.dspy_reasoner:
            raise ValueError("DSPy reasoner not available")

        prompts = {}

        # Check if named_predictors is available
        if not hasattr(self.workflow.dspy_reasoner, "named_predictors"):
            return {"error": "DSPy reasoner does not support introspection"}

        for name, predictor in self.workflow.dspy_reasoner.named_predictors():
            # Extract signature details
            signature = getattr(predictor, "signature", None)
            if not signature:
                continue

            # Get instructions
            instructions = getattr(signature, "instructions", "")

            # Get fields
            inputs = []
            outputs = []

            # Handle fields (DSPy 2.5+ uses model_fields or fields)
            fields = getattr(signature, "fields", {})
            # If fields is empty, try to inspect annotations (older DSPy or Pydantic based)
            if not fields and hasattr(signature, "__annotations__"):
                fields = signature.__annotations__

            for field_name, field in fields.items():
                # Extract description and prefix
                desc = ""
                prefix = ""

                # Try json_schema_extra (Pydantic v2)
                if hasattr(field, "json_schema_extra"):
                    extra = field.json_schema_extra or {}
                    if isinstance(extra, dict):
                        desc = extra.get("desc", "") or extra.get("description", "")
                        prefix = extra.get("prefix", "")

                # Try metadata (Pydantic v1/Field)
                if not desc and hasattr(field, "description"):
                    desc = field.description

                # Try dspy.InputField/OutputField attributes
                if not prefix and hasattr(field, "prefix"):
                    prefix = field.prefix

                field_info = {
                    "name": field_name,
                    "desc": str(desc),
                    "prefix": str(prefix),
                }

                # Determine if input or output
                # DSPy signatures usually have input_fields and output_fields maps
                if hasattr(signature, "input_fields") and field_name in signature.input_fields:
                    inputs.append(field_info)
                elif hasattr(signature, "output_fields") and field_name in signature.output_fields:
                    outputs.append(field_info)
                else:
                    # Fallback heuristic
                    inputs.append(field_info)  # Default to input if unsure

            # Get demos (few-shot examples)
            demos = []
            if hasattr(predictor, "demos"):
                demos_list = getattr(predictor, "demos", None) or []
                for demo in demos_list:
                    # Convert demo to dict
                    demo_dict = {}
                    # demo is usually a dspy.Example which acts like a dict
                    try:
                        for k, v in demo.items():
                            demo_dict[k] = str(v)
                    except Exception as e:
                        # Demo objects may have various formats; skip malformed demos gracefully.
                        logger.warning(f"Malformed demo skipped: {e}")
                    demos.append(demo_dict)

            prompts[name] = {
                "instructions": instructions,
                "inputs": inputs,
                "outputs": outputs,
                "demos_count": len(demos),
                "demos": demos,  # Maybe limit this if too large?
            }

        return prompts

    def get_config(self) -> dict[str, Any]:
        """Get current DSPy configuration.

        Returns:
            Dictionary containing DSPy settings.
        """
        # DSPy config is global via dspy.settings
        lm_info = "unknown"
        if hasattr(dspy.settings, "lm") and dspy.settings.lm:
            lm_info = str(dspy.settings.lm)
            # Try to get model name if available
            if hasattr(dspy.settings.lm, "model"):
                lm_info = f"{dspy.settings.lm.__class__.__name__}(model={dspy.settings.lm.model})"

        config = {
            "lm_provider": lm_info,
            "adapter": str(dspy.settings.adapter)
            if hasattr(dspy.settings, "adapter") and dspy.settings.adapter
            else "default",
        }

        return config

    def get_stats(self) -> dict[str, Any]:
        """Get DSPy usage statistics.

        Returns:
            Dictionary containing usage stats.
        """
        # Check if LM has history
        lm = getattr(dspy.settings, "lm", None)
        history_count = 0
        if lm and hasattr(lm, "history"):
            history_count = len(lm.history)

        stats = {
            "history_count": history_count,
        }

        return stats

    def get_cache_info(self) -> dict[str, Any] | None:
        """Get compilation cache information.

        Returns:
            Cache information dictionary or None if no cache exists.
        """
        return get_cache_info()

    def clear_cache(self) -> None:
        """Clear compilation cache."""
        clear_cache()

    def get_reasoner_summary(self) -> dict[str, Any]:
        """Get reasoner execution summary.

        Returns:
            Summary of reasoner state.
        """
        if not self.workflow.dspy_reasoner:
            return {
                "history_count": 0,
                "routing_cache_size": 0,
                "use_typed_signatures": False,
                "modules_initialized": False,
            }

        summary = self.workflow.dspy_reasoner.get_execution_summary()

        # Ensure expected fields are present
        result = {
            "history_count": summary.get("history_count", 0),
            "routing_cache_size": summary.get("routing_cache_size", 0),
            "use_typed_signatures": summary.get("use_typed_signatures", False),
            "modules_initialized": True,
        }

        return result

    def clear_routing_cache(self) -> None:
        """Clear reasoner routing cache.

        Raises:
            ValueError: If the workflow has no DSPy reasoner.
        """
        if not self.workflow.dspy_reasoner:
            raise ValueError("DSPy reasoner not available")

        self.workflow.dspy_reasoner.clear_routing_cache()

    def list_signatures(self) -> dict[str, Any]:
        """List all available DSPy signatures.

        Returns:
            Dictionary of signature information.
        """
        signatures_info = {}

        try:
            # Import signature modules
            from agentic_fleet.dspy_modules import (
                answer_quality,
                handoff_signatures,
                nlu_signatures,
                signatures,
            )

            # Collect signatures from all modules
            modules = [signatures, handoff_signatures, nlu_signatures, answer_quality]

            for module in modules:
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, dspy.Signature)
                        and obj != dspy.Signature
                    ):
                        # Extract signature info
                        instructions = getattr(obj, "instructions", "") or getattr(
                            obj, "__doc__", ""
                        )
                        input_fields = []
                        output_fields = []

                        # Get fields
                        if hasattr(obj, "input_fields"):
                            input_fields = list(obj.input_fields.keys())
                        if hasattr(obj, "output_fields"):
                            output_fields = list(obj.output_fields.keys())

                        signatures_info[name] = {
                            "name": name,
                            "type": "dspy.Signature",
                            "instructions": instructions.strip() if instructions else None,
                            "input_fields": input_fields,
                            "output_fields": output_fields,
                        }

        except Exception as e:
            logger.error(f"Failed to list signatures: {e}")

        return signatures_info
