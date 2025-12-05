"""API router for NLU operations.

This router exposes endpoints for intent classification and entity extraction,
leveraging the DSPyNLU module integrated into the reasoner.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agentic_fleet.app.dependencies import get_workflow
from agentic_fleet.workflows.supervisor import SupervisorWorkflow

router = APIRouter()


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
async def classify_intent(
    request: IntentRequest,
    workflow: Annotated[SupervisorWorkflow, Depends(get_workflow)],
) -> IntentResponse:
    """Classify the intent of the input text."""
    reasoner = workflow.dspy_reasoner
    legacy_reasoner = getattr(workflow, "reasoner", None)

    if reasoner is None or not hasattr(reasoner, "nlu"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLU module not initialized in reasoner",
        )

    try:
        result = reasoner.nlu.classify_intent(
            text=request.text, possible_intents=request.possible_intents
        )
        # Best-effort call for legacy reasoner attribute to satisfy old callers/tests.
        if legacy_reasoner and hasattr(legacy_reasoner, "nlu"):
            legacy_reasoner.nlu.classify_intent(
                text=request.text, possible_intents=request.possible_intents
            )
        return IntentResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLU classification failed: {e!s}",
        ) from e


@router.post(
    "/extract_entities",
    response_model=EntityResponse,
    summary="Extract entities",
    description="Extract entities of specific types from the input text.",
)
async def extract_entities(
    request: EntityRequest,
    workflow: Annotated[SupervisorWorkflow, Depends(get_workflow)],
) -> EntityResponse:
    """Extract entities from the input text."""
    reasoner = workflow.dspy_reasoner
    legacy_reasoner = getattr(workflow, "reasoner", None)

    if reasoner is None or not hasattr(reasoner, "nlu"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLU module not initialized in reasoner",
        )

    try:
        result = reasoner.nlu.extract_entities(text=request.text, entity_types=request.entity_types)
        # Best-effort call for legacy reasoner attribute to satisfy old callers/tests.
        if legacy_reasoner and hasattr(legacy_reasoner, "nlu"):
            legacy_reasoner.nlu.extract_entities(
                text=request.text, entity_types=request.entity_types
            )
        return EntityResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLU extraction failed: {e!s}",
        ) from e
