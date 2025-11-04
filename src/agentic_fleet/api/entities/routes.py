"""Entity discovery and management routes."""

from __future__ import annotations

from typing import no_type_check

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.entities.schemas import DiscoveryResponse, EntityInfo, EntityReloadResponse
from agentic_fleet.api.entities.service import EntityDiscovery

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


@no_type_check
@router.get("/entities", response_model=DiscoveryResponse)
async def list_entities() -> DiscoveryResponse:
    """List all available entities (workflows).

    Returns:
        DiscoveryResponse with list of entities
    """
    discovery = get_entity_discovery()
    entities = await discovery.list_entities_async()
    return DiscoveryResponse(entities=entities)


@no_type_check
@router.get("/entities/{entity_id}", response_model=EntityInfo)
async def get_entity_info(entity_id: str) -> EntityInfo:
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@no_type_check
@router.post("/entities/{entity_id}/reload", response_model=EntityReloadResponse)
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
