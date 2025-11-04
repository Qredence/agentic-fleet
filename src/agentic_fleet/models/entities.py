"""Entity discovery API schemas matching OpenAI Responses API format."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InputSchema(BaseModel):
    """Input schema for an entity following OpenAI Responses API format."""

    type: str = Field(default="object", description="JSON schema type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Schema properties")
    required: list[str] = Field(default_factory=list, description="Required fields")


class EntityInfo(BaseModel):
    """Entity information matching OpenAI Responses API format."""

    id: str = Field(description="Entity identifier (workflow ID)")
    name: str = Field(description="Entity display name")
    description: str = Field(default="", description="Entity description")
    input_schema: InputSchema = Field(description="Input schema for the entity")


class DiscoveryResponse(BaseModel):
    """Response containing list of available entities."""

    entities: list[EntityInfo] = Field(description="List of available entities")


class EntityReloadResponse(BaseModel):
    """Response for entity reload operation."""

    entity_id: str = Field(description="Entity identifier that was reloaded")
    success: bool = Field(description="Whether reload was successful")
    message: str = Field(description="Status message")
