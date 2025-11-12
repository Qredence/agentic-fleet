"""Magentic Fleet workflow builder and implementation."""

import hashlib
import json
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from agent_framework import MagenticBuilder
from agent_framework.openai import OpenAIResponsesClient
from langcache import LangCache

from agentic_fleet.models import WorkflowConfig
from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent
from agentic_fleet.models.requests import (
    WorkflowCheckpointMetadata,
    WorkflowResumeRequest,
    WorkflowRunRequest,
)
from agentic_fleet.models.workflow_config import WorkflowManagerConfig
from agentic_fleet.persistence.checkpointing import WorkflowCheckpointService
from agentic_fleet.utils.redis_cache import get_redis_cache
from agentic_fleet.utils.telemetry import optional_span, record_workflow_event
from agentic_fleet.workflow.events import WorkflowEventBridge

logger = logging.getLogger(__name__)


class MagenticFleetWorkflow(RunsWorkflow):
    """Magentic Fleet workflow implementation with caching and checkpoint support."""

    def __init__(
        self,
        workflow: Any,
        workflow_id: str,
        *,
        checkpoint_service: WorkflowCheckpointService | None = None,
        cache_config: dict[str, Any] | None = None,
    ) -> None:
        self._workflow = workflow
        self._workflow_id = workflow_id
        self._event_bridge = WorkflowEventBridge()
        self._checkpoint_service = checkpoint_service

        self._langcache: LangCache | None = None
        self._cache_ttl_ms: int | None = None

        if cache_config and cache_config.get("enabled", False):
            try:
                ttl_seconds = int(cache_config.get("ttl_seconds", 3600))
            except (ValueError, TypeError) as e:
                logger.warning(
                    "[MAGENTIC] Invalid ttl_seconds in cache config, using default: %s", e
                )
                ttl_seconds = 3600
            self._cache_ttl_ms = max(ttl_seconds, 0) * 1000 if ttl_seconds else None
            try:
                self._langcache = get_redis_cache().langcache
                logger.info(
                    "[MAGENTIC] LangCache enabled for workflow %s (ttl=%s ms)",
                    workflow_id,
                    self._cache_ttl_ms,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "[MAGENTIC] LangCache unavailable, caching disabled: %s", exc, exc_info=True
                )
                self._langcache = None

    def supports_checkpointing(self) -> bool:
        """Return whether checkpointing is configured."""

        return self._checkpoint_service is not None

    async def list_checkpoints(self) -> list[WorkflowCheckpointMetadata]:
        """Return metadata for available checkpoints."""

        if not self._checkpoint_service:
            return []
        return await self._checkpoint_service.list_metadata(self._workflow_id)

    async def run(self, request: WorkflowRunRequest | str) -> AsyncGenerator[WorkflowEvent, None]:
        """Execute the workflow for a new request."""

        with optional_span(
            "MagenticFleetWorkflow.run",
            tracer_name=__name__,
            attributes={"workflow.id": self._workflow_id},
        ) as span:
            run_request = self._normalize_request(request)

            if span is not None:
                span.set_attribute("workflow.request.use_cache", bool(run_request.use_cache))
                if run_request.conversation_id:
                    span.set_attribute("workflow.conversation_id", run_request.conversation_id)
                if run_request.correlation_id:
                    span.set_attribute("workflow.correlation_id", run_request.correlation_id)

            cached_content = await self._maybe_get_cached_response(run_request)
            cache_hit = cached_content is not None
            if span is not None:
                span.set_attribute("workflow.cache_hit", cache_hit)

            if cache_hit:
                async for cached_event in self._emit_cache_hit(run_request, cached_content or ""):
                    yield self._prepare_event(cached_event, run_request)
                if span is not None:
                    span.set_attribute("workflow.response_length", len(cached_content or ""))
                return

            storage = self._checkpoint_service.storage if self._checkpoint_service else None

            last_agent_id: str | None = None
            last_kind: str | None = None
            accumulated_content = ""
            agent_buffers: dict[str, str] = {}
            final_result: str | None = None

            try:
                async for event in self._workflow.run_stream(
                    run_request.message, checkpoint_storage=storage
                ):
                    converted_event = self._event_bridge.convert_event(event, openai_format=True)

                    # Emit progress for orchestrator phases
                    if converted_event.get("type") == "orchestrator.message":
                        kind = converted_event["data"].get("kind", "")
                        if kind != last_kind:
                            if kind == "task_ledger":
                                planning_event = self._prepare_event(
                                    {
                                        "type": "progress",
                                        "data": {
                                            "stage": "planning",
                                            "message": "Manager creating task plan",
                                        },
                                    },
                                    run_request,
                                )
                                yield planning_event
                            elif kind == "progress_ledger":
                                evaluating_event = self._prepare_event(
                                    {
                                        "type": "progress",
                                        "data": {
                                            "stage": "evaluating",
                                            "message": "Manager evaluating progress",
                                        },
                                    },
                                    run_request,
                                )
                                yield evaluating_event
                            last_kind = kind

                    if converted_event.get("type") == "message.delta":
                        agent_id = converted_event["data"].get("agent_id")
                        delta = converted_event["data"].get("delta", "")

                        if delta:
                            accumulated_content += delta
                            if agent_id:
                                agent_buffers.setdefault(agent_id, "")
                                agent_buffers[agent_id] += delta

                        if agent_id and agent_id != last_agent_id:
                            if last_agent_id is not None:
                                completion_event = self._prepare_event(
                                    {
                                        "type": "progress",
                                        "data": {
                                            "stage": "agent.complete",
                                            "agent_id": last_agent_id,
                                            "message": f"{last_agent_id} completed",
                                            "accumulated": agent_buffers.get(last_agent_id, ""),
                                        },
                                    },
                                    run_request,
                                )
                                yield completion_event
                            starting_event = self._prepare_event(
                                {
                                    "type": "progress",
                                    "data": {
                                        "stage": "agent.starting",
                                        "agent_id": agent_id,
                                        "message": f"{agent_id} starting",
                                    },
                                },
                                run_request,
                            )
                            yield starting_event
                            last_agent_id = agent_id

                        converted_event_data = converted_event["data"]
                        converted_event_data["accumulated"] = accumulated_content
                        if agent_id:
                            converted_event_data["agent_accumulated"] = agent_buffers.get(
                                agent_id, ""
                            )
                        converted_event_data.setdefault("cached", False)

                    elif converted_event.get("type") == "message.done":
                        converted_event["data"].setdefault("cached", False)
                        final_result = converted_event["data"].get("result")

                    yield self._prepare_event(converted_event, run_request)

                final_content = final_result or accumulated_content
                await self._maybe_store_cache(run_request, final_content)
                logger.info(
                    "[MAGENTIC] Completed response (%s chars, %s agents)",
                    len(final_content),
                    len(agent_buffers),
                )
                if span is not None:
                    span.set_attribute("workflow.response_length", len(final_content))
                    span.set_attribute("workflow.agent_count", len(agent_buffers))

            except Exception as exc:  # pragma: no cover - propagate for tests
                if span is not None:
                    span.record_exception(exc)
                logger.error("[MAGENTIC] Workflow execution failed: %s", exc, exc_info=True)
                error_event = self._prepare_event(self._build_error_event(exc), run_request)
                yield error_event
                raise

    async def resume(self, request: WorkflowResumeRequest) -> AsyncGenerator[WorkflowEvent, None]:
        """Resume the workflow from a stored checkpoint."""

        if not self._checkpoint_service:
            raise ValueError("Checkpointing is not enabled for this workflow")

        synthetic_request = WorkflowRunRequest(
            message="",
            conversation_id=request.conversation_id,
            correlation_id=request.correlation_id,
            metadata=request.metadata,
            context={},
            use_cache=request.use_cache,
        )

        with optional_span(
            "MagenticFleetWorkflow.resume",
            tracer_name=__name__,
            attributes={
                "workflow.id": self._workflow_id,
                "workflow.resume.checkpoint_id": request.checkpoint_id,
            },
        ) as span:
            last_kind: str | None = None
            accumulated_content = ""
            agent_buffers: dict[str, str] = {}

            try:
                async for event in self._workflow.run_stream(
                    checkpoint_id=request.checkpoint_id,
                    checkpoint_storage=self._checkpoint_service.storage,
                ):
                    converted_event = self._event_bridge.convert_event(event, openai_format=True)

                    if converted_event.get("type") == "orchestrator.message":
                        kind = converted_event["data"].get("kind", "")
                        if kind != last_kind:
                            progress_event = self._prepare_event(
                                {
                                    "type": "progress",
                                    "data": {
                                        "stage": "resuming",
                                        "message": f"Resumed workflow stage: {kind}",
                                    },
                                },
                                synthetic_request,
                            )
                            yield progress_event
                            last_kind = kind

                    if converted_event.get("type") == "message.delta":
                        agent_id = converted_event["data"].get("agent_id")
                        delta = converted_event["data"].get("delta", "")

                        if delta:
                            accumulated_content += delta
                            if agent_id:
                                agent_buffers.setdefault(agent_id, "")
                                agent_buffers[agent_id] += delta

                        converted_event["data"]["accumulated"] = accumulated_content
                        if agent_id:
                            converted_event["data"]["agent_accumulated"] = agent_buffers.get(
                                agent_id, ""
                            )

                    yield self._prepare_event(converted_event, synthetic_request)

                if span is not None:
                    span.set_attribute(
                        "workflow.resume.accumulated_length", len(accumulated_content)
                    )
                    span.set_attribute("workflow.resume.agent_count", len(agent_buffers))

            except Exception as exc:  # pragma: no cover - propagate for tests
                if span is not None:
                    span.record_exception(exc)
                logger.error("[MAGENTIC] Workflow resume failed: %s", exc, exc_info=True)
                error_event = self._prepare_event(self._build_error_event(exc), synthetic_request)
                yield error_event
                raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_request(request: WorkflowRunRequest | str) -> WorkflowRunRequest:
        if isinstance(request, WorkflowRunRequest):
            return request
        if isinstance(request, str):
            return WorkflowRunRequest(message=request)
        raise TypeError(f"Unsupported request type: {type(request)!r}")

    def _attach_metadata(self, event: WorkflowEvent, request: WorkflowRunRequest) -> WorkflowEvent:
        if request.correlation_id:
            event["correlation_id"] = request.correlation_id

        data = event["data"]
        if request.conversation_id:
            data.setdefault("conversation_id", request.conversation_id)

        if request.metadata:
            metadata = data.setdefault("metadata", {})
            metadata.update(request.metadata)

        return event

    def _prepare_event(self, event: WorkflowEvent, request: WorkflowRunRequest) -> WorkflowEvent:
        """Attach metadata and emit optional telemetry for a workflow event."""
        prepared_event = self._attach_metadata(event, request)
        event_type: str | None = prepared_event.get("type")
        record_workflow_event(self._workflow_id, event_type=event_type)
        return prepared_event

    def _build_error_event(self, exc: Exception) -> WorkflowEvent:
        return {
            "type": "error",
            "data": {
                "message": f"Magentic workflow error: {exc!s}",
                "error": str(exc),
            },
        }

    def _supports_cache(self) -> bool:
        return self._langcache is not None

    async def _maybe_get_cached_response(self, request: WorkflowRunRequest) -> str | None:
        if not (request.use_cache and self._supports_cache() and request.message.strip()):
            return None
        assert self._langcache is not None  # mypy hint

        cache_key = self._cache_key(request)
        try:
            response = await self._langcache.search_async(
                prompt=request.message,
                similarity_threshold=1.0,
                attributes=self._cache_attributes(cache_key),
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("[MAGENTIC] LangCache search failed: %s", exc, exc_info=True)
            return None

        if not response or not getattr(response, "data", None):
            return None

        for entry in response.data:
            if entry.attributes.get("cache_key") == cache_key:
                logger.info("[MAGENTIC] Cache hit for workflow %s", self._workflow_id)
                return entry.response  # type: ignore
        return None

    async def _maybe_store_cache(self, request: WorkflowRunRequest, content: str) -> None:
        if not (request.use_cache and self._supports_cache() and content.strip()):
            return
        assert self._langcache is not None

        cache_key = self._cache_key(request)
        try:
            await self._langcache.set_async(
                prompt=request.message,
                response=content,
                attributes=self._cache_attributes(cache_key),
                ttl_millis=self._cache_ttl_ms,
            )
            logger.info("[MAGENTIC] Cached workflow response (%s)", self._workflow_id)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("[MAGENTIC] Failed to cache workflow response: %s", exc, exc_info=True)

    async def _emit_cache_hit(
        self, request: WorkflowRunRequest, cached_content: str
    ) -> AsyncGenerator[WorkflowEvent, None]:
        delta_event: WorkflowEvent = {
            "type": "message.delta",
            "openai_type": "response.delta",
            "data": {
                "delta": cached_content,
                "agent_id": "langcache",
                "accumulated": cached_content,
                "cached": True,
            },
        }
        yield self._prepare_event(delta_event, request)

        done_event: WorkflowEvent = {
            "type": "message.done",
            "openai_type": "response.completed",
            "data": {
                "result": cached_content,
                "cached": True,
            },
        }
        yield self._prepare_event(done_event, request)

    def _cache_key(self, request: WorkflowRunRequest) -> str:
        payload = {
            "workflow_id": self._workflow_id,
            "message": request.message,
            "metadata": request.metadata,
            "context": request.context,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _cache_attributes(self, cache_key: str) -> dict[str, str]:
        attrs = {"workflow_id": self._workflow_id, "cache_key": cache_key}
        return attrs


class MagenticFleetWorkflowBuilder:
    """Builder for creating Magentic Fleet workflows from configuration."""

    def __init__(self) -> None:
        """Initialize workflow builder."""
        from agentic_fleet.agents import AgentFactory

        self.agent_factory = AgentFactory()

    def build(self, config: WorkflowConfig) -> MagenticFleetWorkflow:
        """Build a Magentic Fleet workflow from configuration.

        Args:
            config: Workflow configuration from YAML

        Returns:
            Configured MagenticFleetWorkflow instance

        Raises:
            ValueError: If configuration is invalid
        """
        if config.id != "magentic_fleet":
            raise ValueError(
                f"Workflow builder only supports 'magentic_fleet' workflow, got '{config.id}'"
            )

        # Create specialist agents
        # Note: config.agents is already resolved by WorkflowFactory, no need to resolve strings
        specialist_agents: dict[str, Any] = {}
        for agent_name, agent_config in config.agents.items():
            # agent_config should already be a dict from WorkflowFactory resolution
            if not isinstance(agent_config, dict):
                raise ValueError(
                    f"Agent config for '{agent_name}' must be a dict, got {type(agent_config).__name__}"
                )

            # Create agent using AgentFactory
            try:
                agent = self.agent_factory.create_agent(agent_name, agent_config)
                specialist_agents[agent_name] = agent
                logger.info(f"Created agent '{agent_name}' successfully")
            except Exception as e:
                logger.error(f"Failed to create agent '{agent_name}': {e}")
                raise ValueError(f"Agent creation failed for '{agent_name}': {e}") from e

        # Create manager agent
        manager_config = config.manager
        manager_dict = (
            manager_config.model_dump()
            if isinstance(manager_config, WorkflowManagerConfig)
            else dict(manager_config)
        )

        manager_model = manager_dict.get("model")
        if not manager_model:
            raise ValueError("Manager configuration missing 'model' field")

        # Extract manager settings
        manager_instructions = manager_dict.get("instructions", "")
        reasoning_config = manager_dict.get("reasoning") or {}
        reasoning_effort = reasoning_config.get("effort", "high")
        reasoning_verbosity = reasoning_config.get("verbosity", "verbose")
        temperature = manager_dict.get("temperature", 0.6)
        max_tokens = manager_dict.get("max_tokens", 8192)
        store = manager_dict.get("store")
        if store is None:
            store = True

        # Manager limits
        max_round_count = manager_dict.get("max_round_count", 6)
        max_stall_count = manager_dict.get("max_stall_count", 3)
        max_reset_count = manager_dict.get("max_reset_count", 2)

        # Create manager chat client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it before creating the workflow."
            )

        manager_client = OpenAIResponsesClient(
            model_id=manager_model,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            reasoning_verbosity=reasoning_verbosity,
            store=store,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Build workflow using MagenticBuilder
        builder = MagenticBuilder()

        # Register participants (specialist agents)
        builder = builder.participants(**specialist_agents)

        # Configure manager
        builder = builder.with_standard_manager(
            chat_client=manager_client,
            instructions=manager_instructions if manager_instructions else None,
            max_round_count=max_round_count,
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
        )

        # Build workflow
        workflow = builder.build()

        logger.info(
            "Built Magentic Fleet workflow with %s agents, manager model '%s', max_round_count=%s",
            len(specialist_agents),
            manager_model,
            max_round_count,
        )

        checkpoint_service: WorkflowCheckpointService | None = None
        default_checkpoint_dir = Path("var") / "checkpoints" / config.id
        if isinstance(config.checkpointing, dict):
            enabled = config.checkpointing.get("enabled", True)
            if enabled:
                base_dir = config.checkpointing.get("base_dir")
                checkpoint_service = WorkflowCheckpointService(base_dir or default_checkpoint_dir)
        elif config.checkpointing is False:
            checkpoint_service = None
        else:
            checkpoint_service = WorkflowCheckpointService(default_checkpoint_dir)

        cache_config: dict[str, Any] | None = None
        if isinstance(config.cache, dict):
            cache_config = config.cache
        elif config.cache:
            cache_config = {"enabled": True}

        return MagenticFleetWorkflow(
            workflow,
            config.id,
            checkpoint_service=checkpoint_service,
            cache_config=cache_config,
        )
