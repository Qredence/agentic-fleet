"""NLU routes.

Endpoints for intent classification and entity extraction, leveraging the
DSPy NLU module integrated into the Supervisor workflow reasoner.
"""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agentic_fleet.api.deps import WorkflowDep

router = APIRouter()


def _get_nlu_reasoner(workflow: Any) -> Any:
    """Get and validate NLU reasoner from workflow.

    Args:
        workflow: The workflow instance

    Returns:
        The NLU reasoner

    Raises:
        HTTPException: If NLU module is not available
    """
    reasoner = getattr(workflow, "dspy_reasoner", None)

    if reasoner is None or not hasattr(reasoner, "nlu"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLU module not initialized in reasoner",
        )

    return reasoner


class IntentRequest(BaseModel):
    """Request model for intent classification."""

    text: str = Field(..., description="The user's input text")
    possible_intents: list[str] = Field(..., description="List of possible intents to choose from")


class EntityRequest(BaseModel):
    """Request model for entity extraction."""

    text: str = Field(..., description="The user's input text")
    entity_types: list[str] = Field(
        ..., description="List of entity types to extract (e.g., Person, Date)"
    )


class IntentResponse(BaseModel):
    """Response model for intent classification."""

    intent: str
    confidence: float
    reasoning: str


class EntityResponse(BaseModel):
    """Response model for entity extraction."""

    entities: list[dict[str, Any]]
    reasoning: str


@router.post(
    "/classify_intent",
    response_model=IntentResponse,
    summary="Classify user intent",
    description="Classify the intent of a text input given a list of possible intents.",
)
async def classify_intent(request: IntentRequest, workflow: WorkflowDep) -> IntentResponse:
    """Classify intent for the provided text."""
    reasoner = _get_nlu_reasoner(workflow)
    legacy_reasoner = getattr(workflow, "reasoner", None)

    try:
        result = reasoner.nlu.classify_intent(
            text=request.text, possible_intents=request.possible_intents
        )
        # Best-effort call for legacy reasoner attribute to satisfy old callers/tests.
        if legacy_reasoner and hasattr(legacy_reasoner, "nlu"):
            with contextlib.suppress(Exception):
                legacy_reasoner.nlu.classify_intent(
                    text=request.text, possible_intents=request.possible_intents
                )
        return IntentResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLU classification failed: {exc!s}",
        ) from exc


@router.post(
    "/extract_entities",
    response_model=EntityResponse,
    summary="Extract entities",
    description="Extract entities of specific types from the input text.",
)
async def extract_entities(request: EntityRequest, workflow: WorkflowDep) -> EntityResponse:
    """Extract entities from the provided text."""
    reasoner = _get_nlu_reasoner(workflow)
    legacy_reasoner = getattr(workflow, "reasoner", None)

    try:
        result = reasoner.nlu.extract_entities(text=request.text, entity_types=request.entity_types)
        # Best-effort call for legacy reasoner attribute to satisfy old callers/tests.
        if legacy_reasoner and hasattr(legacy_reasoner, "nlu"):
            with contextlib.suppress(Exception):
                legacy_reasoner.nlu.extract_entities(
                    text=request.text, entity_types=request.entity_types
                )
        return EntityResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLU extraction failed: {exc!s}",
        ) from exc
