"""DSPy management router.

Provides endpoints for inspecting and managing DSPy modules.
"""

import logging
from typing import Any

import dspy
from fastapi import APIRouter, HTTPException, status

from agentic_fleet.app.dependencies import WorkflowDep

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dspy/prompts", response_model=dict[str, Any])
async def get_dspy_prompts(
    workflow: WorkflowDep,
) -> dict[str, Any]:
    """Retrieve active DSPy prompts and signatures.

    Returns:
        Dictionary mapping module names to their prompt details.
    """
    if not workflow.dspy_reasoner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DSPy reasoner not available",
        )

    prompts = {}

    # Check if named_predictors is available
    if not hasattr(workflow.dspy_reasoner, "named_predictors"):
        return {"error": "DSPy reasoner does not support introspection"}

    for name, predictor in workflow.dspy_reasoner.named_predictors():
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
            for demo in predictor.demos:
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


@router.get("/dspy/config", response_model=dict[str, Any])
async def get_dspy_config() -> dict[str, Any]:
    """Retrieve DSPy configuration.

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


@router.get("/dspy/stats", response_model=dict[str, Any])
async def get_dspy_stats() -> dict[str, Any]:
    """Retrieve DSPy usage statistics.

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
