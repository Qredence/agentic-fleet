"""Entity discovery and management routes."""

from __future__ import annotations

from fastapi import APIRouter

from agentic_fleet.api.entities.schemas import (
    EntityDetailResponse,
    EntityListResponse,
    EntityReloadResponse,
)
from agentic_fleet.api.entities.service import EntityDiscovery
from agentic_fleet.api.exceptions import EntityNotFoundError

router = APIRouter()

# Singleton instance for entity discovery
_entity_discovery: EntityDiscovery | None = None


def get_entity_discovery() -> EntityDiscovery:
    """Get or create EntityDiscovery instance.

    Returns:
        EntityDiscovery instance
    """
    global _entity_discovery
    if _entity_discovery is None:
        _entity_discovery = EntityDiscovery()
    return _entity_discovery


@router.get("/entities", response_model=EntityListResponse)  # type: ignore
async def list_entities() -> EntityListResponse:
    """List all available entities (workflows).

    Returns:
        DiscoveryResponse with list of entities
    """
    discovery = get_entity_discovery()
    entities = await discovery.list_entities_async()
    return EntityListResponse(entities=entities)


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)  # type: ignore
async def get_entity_info(entity_id: str) -> EntityDetailResponse:
    """Get detailed information about a specific entity.

    Args:
        entity_id: Entity identifier (workflow ID)

    Returns:
        EntityInfo object

    Raises:
        HTTPException: If entity not found
    """
    discovery = get_entity_discovery()
    try:
        return await discovery.get_entity_info_async(entity_id)
    except ValueError as exc:
        raise EntityNotFoundError(entity_id) from exc


@router.post("/entities/{entity_id}/reload", response_model=EntityReloadResponse)  # type: ignore
async def reload_entity(entity_id: str) -> EntityReloadResponse:
    """Reload entity configuration without restarting the server.

    Args:
        entity_id: Entity identifier (workflow ID)

    Returns:
        EntityReloadResponse with reload status

    Raises:
        HTTPException: If entity not found
    """
    discovery = get_entity_discovery()
    try:
        await discovery.reload_entity_async(entity_id)
        return EntityReloadResponse(
            entity_id=entity_id,
            success=True,
            message=f"Entity '{entity_id}' reloaded successfully",
        )
    except ValueError as exc:
        raise EntityNotFoundError(entity_id) from exc
