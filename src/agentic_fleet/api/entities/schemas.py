"""Entity discovery API schemas matching OpenAI Responses API format."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InputSchema(BaseModel):
    """Input schema for an entity following OpenAI Responses API format."""

    type: str = Field(default="object", description="JSON schema type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Schema properties")
    required: list[str] = Field(default_factory=list, description="Required fields")


class EntityDetailResponse(BaseModel):
    """Entity information matching OpenAI Responses API format."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Entity identifier (workflow ID)")
    name: str = Field(description="Entity display name")
    description: str = Field(default="", description="Entity description")
    input_schema: InputSchema = Field(description="Input schema for the entity")


class EntityListResponse(BaseModel):
    """Response containing list of available entities."""

    model_config = ConfigDict(extra="allow")
    entities: list[EntityDetailResponse] = Field(description="List of available entities")


class EntityReloadResponse(BaseModel):
    """Response for entity reload operation."""

    entity_id: str = Field(description="Entity identifier that was reloaded")
    success: bool = Field(description="Whether reload was successful")
    message: str = Field(description="Status message")
