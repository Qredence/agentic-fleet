"""Entity discovery service wrapping WorkflowFactory."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from agentic_fleet.api.entities.schemas import EntityDetailResponse, InputSchema
from agentic_fleet.api.workflows import service as workflows_service
from agentic_fleet.utils.factory import WorkflowFactory
from agentic_fleet.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)


class EntityDiscovery:
    """Service for discovering and managing workflow entities.

    Provides both synchronous and asynchronous APIs to maintain backward
    compatibility with earlier tests that invoked methods synchronously.
    """

    def __init__(self, workflow_factory: WorkflowFactory | None = None) -> None:
        self._factory = workflow_factory or WorkflowFactory()
        self._entity_cache: dict[str, EntityDetailResponse] = {}
        self._workflow_cache: dict[str, Any] = {}

    # ---------------------- Synchronous public API ---------------------- #
    def list_entities(self) -> list[EntityDetailResponse]:  # pragma: no cover - exercised via tests
        """List entities using synchronous factory API (test/backward compat path)."""
        entities: list[EntityDetailResponse] = []
        try:
            workflows = self._factory.list_available_workflows()
        except Exception:  # Fallback to async if sync unavailable
            return self._run_blocking(self.list_entities_async)
        for wf in workflows:
            entity_id = wf["id"]
            if entity_id in self._entity_cache:
                entities.append(self._entity_cache[entity_id])
            else:
                info = self._create_entity_info(entity_id, wf)
                self._entity_cache[entity_id] = info
                entities.append(info)
        return entities

    def get_entity_info(self, entity_id: str) -> EntityDetailResponse:  # pragma: no cover
        """Get entity info synchronously (test/backward compat path)."""
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        try:
            self._factory.get_workflow_config(entity_id)
        except Exception:
            return self._run_blocking(lambda: self.get_entity_info_async(entity_id))
        workflows = self._factory.list_available_workflows()
        wf_dict = next((w for w in workflows if w["id"] == entity_id), None)
        if wf_dict is None:
            raise ValueError(f"Entity '{entity_id}' not found")
        info = self._create_entity_info(entity_id, wf_dict)
        self._entity_cache[entity_id] = info
        return info

    def reload_entity(self, entity_id: str) -> None:  # pragma: no cover
        """Reload entity configuration synchronously, preserving legacy expectations."""
        if entity_id in self._entity_cache:
            del self._entity_cache[entity_id]
        if entity_id in self._workflow_cache:
            del self._workflow_cache[entity_id]
        try:
            # Access config via factory to validate existence; factory guarantees attribute
            self._factory.get_workflow_config(entity_id)
        except ValueError as exc:
            # Tests expect a specific error message on not found after reload
            raise ValueError(f"Entity '{entity_id}' not found after reload") from exc
        except Exception:
            # Other unexpected exceptions: attempt async path (may raise)
            return self._run_blocking(lambda: self.reload_entity_async(entity_id))
        # Legacy tests expect private _load_config() to be touched if present, ignore failures
        if hasattr(self._factory, "_load_config"):
            from contextlib import suppress

            with suppress(Exception):  # pragma: no cover - defensive
                self._factory._load_config()

    def get_workflow_instance(self, entity_id: str) -> Any:  # pragma: no cover
        """Get (or create) workflow instance synchronously with caching."""
        if entity_id in self._workflow_cache:
            return self._workflow_cache[entity_id]
        try:
            self._factory.get_workflow_config(entity_id)
            workflow = self._factory.create_from_yaml(entity_id)
        except Exception:
            return self._run_blocking(lambda: self.get_workflow_instance_async(entity_id))
        self._workflow_cache[entity_id] = workflow
        return workflow

    # ---------------------- Asynchronous implementation ----------------- #
    async def list_entities_async(self) -> list[EntityDetailResponse]:
        entities: list[EntityDetailResponse] = []
        workflows = await self._factory.list_available_workflows_async()
        for wf in workflows:
            entity_id = wf["id"]
            if entity_id in self._entity_cache:
                entities.append(self._entity_cache[entity_id])
            else:
                info = self._create_entity_info(entity_id, wf)
                self._entity_cache[entity_id] = info
                entities.append(info)
        return entities

    async def get_entity_info_async(self, entity_id: str) -> EntityDetailResponse:
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        try:
            await self._factory.get_workflow_config_async(entity_id)
        except ValueError as exc:
            raise ValueError(f"Entity '{entity_id}' not found") from exc
        workflows = await self._factory.list_available_workflows_async()
        wf_dict = next((w for w in workflows if w["id"] == entity_id), None)
        if wf_dict is None:
            raise ValueError(f"Entity '{entity_id}' not found")
        info = self._create_entity_info(entity_id, wf_dict)
        self._entity_cache[entity_id] = info
        return info

    async def reload_entity_async(self, entity_id: str) -> None:
        if entity_id in self._entity_cache:
            del self._entity_cache[entity_id]
        if entity_id in self._workflow_cache:
            del self._workflow_cache[entity_id]
        try:
            await self._factory.get_workflow_config_async(entity_id)
        except ValueError as exc:
            raise ValueError(f"Entity '{entity_id}' not found after reload") from exc
        logger.info(f"Reloaded entity: {sanitize_for_log(entity_id)}")

    async def get_workflow_instance_async(self, entity_id: str) -> Any:
        if entity_id in self._workflow_cache:
            return self._workflow_cache[entity_id]
        await self._factory.get_workflow_config_async(entity_id)
        if self._should_force_stub():
            workflow = await workflows_service.create_workflow(entity_id)
        else:
            workflow = await self._factory.create_from_yaml_async(entity_id)
        self._workflow_cache[entity_id] = workflow
        return workflow

    # ---------------------- Internal helpers --------------------------- #
    T = TypeVar("T")

    def _run_blocking(
        self, coro_factory: Callable[[], Coroutine[Any, Any, T]]
    ) -> T:  # pragma: no cover - simple utility
        """Execute an asynchronous factory in a blocking manner.

        This helper preserves legacy synchronous test pathways while enforcing that
        the provided factory returns an awaitable producing a concrete type.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro_factory())
        raise RuntimeError(
            "Synchronous EntityDiscovery method called inside running event loop. "
            "Use the '*_async' variant instead."
        )

    def _create_entity_info(
        self, entity_id: str, workflow_dict: dict[str, Any]
    ) -> EntityDetailResponse:
        """Create EntityInfo from workflow dictionary.

        Args:
            entity_id: Entity identifier
            workflow_dict: Workflow dictionary from list_available_workflows()

        Returns:
            EntityInfo object
        """
        # Create input schema following OpenAI Responses API format
        # For now, we accept a string input (message) or structured input
        input_schema = InputSchema(
            type="object",
            properties={
                "input": {
                    "type": "string",
                    "description": "Input message or task description",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Optional conversation ID for context",
                },
            },
            required=["input"],
        )
        return EntityDetailResponse(
            id=entity_id,
            name=workflow_dict.get("name", entity_id),
            description=workflow_dict.get("description", ""),
            input_schema=input_schema,
        )

    def _should_force_stub(self) -> bool:
        """Return True if stubbing is forced via environment variable."""
        forced = os.getenv("AF_FORCE_STUB_WORKFLOW", "").lower() in {"1", "true"}
        logger.debug("AF_FORCE_STUB_WORKFLOW flag evaluated to %s", forced)
        return forced
