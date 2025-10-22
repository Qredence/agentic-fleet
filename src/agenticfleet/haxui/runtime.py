from __future__ import annotations

import asyncio
import json
import logging
import os
import textwrap
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager

from agenticfleet.config import settings
from agenticfleet.core.approved_tools import set_approval_handler

from .web_approval import WebApprovalHandler

logger = logging.getLogger(__name__)

# Development mode - set to True to bypass fleet execution for frontend testing
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"

try:
    from agenticfleet.fleet import create_default_fleet
    from agenticfleet.fleet.magentic_fleet import MagenticFleet
    from agenticfleet.workflows.workflow_as_agent import create_workflow_agent
except Exception:  # pragma: no cover - dependency missing in some environments
    create_default_fleet = None  # type: ignore[assignment,misc]
    MagenticFleet = None  # type: ignore[assignment,misc]
    create_workflow_agent = None  # type: ignore[assignment,misc]


class FleetRuntime:
    """Wrapper around MagenticFleet with graceful fallbacks."""

    def __init__(self, approval_handler: WebApprovalHandler | None = None) -> None:
        haxui_config = settings.workflow_config.get("haxui", {}) or {}
        concurrency_config = haxui_config.get("concurrency", {}) or {}
        max_parallel = int(concurrency_config.get("max_parallel_requests", 2) or 1)
        if max_parallel < 1:
            max_parallel = 1

        self._fleet: MagenticFleet | None = None  # type: ignore[valid-type]
        self._workflow_as_agent = None  # type: ignore[var-annotated]
        self._initialisation_error: str | None = None
        self.approval_handler = approval_handler or WebApprovalHandler()
        self._max_concurrency = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._queue_lock = asyncio.Lock()
        self._queue_waiters = 0
        self._inflight = 0

    async def ensure_initialised(self) -> None:
        if self._fleet or self._initialisation_error:
            return

        await self.approval_handler.initialise()

        if create_default_fleet is None:
            self._initialisation_error = (  # type: ignore[unreachable]
                "Microsoft Agent Framework is not installed. "
                "Install the agent-framework extras to enable orchestration."
            )
        else:  # pragma: no cover - conditional import may succeed
            try:
                # Create fleet with web approval handler instead of CLI
                self._fleet = create_default_fleet(console_ui=None)  # type: ignore[call-arg]
                if self._fleet is not None and hasattr(self._fleet, "approval_handler"):
                    self._fleet.approval_handler = self.approval_handler
                    approval_policy = getattr(self._fleet, "approval_policy", {}) or {}
                    set_approval_handler(
                        self.approval_handler,
                        require_operations=approval_policy.get("require_approval_for", []),
                        trusted_operations=approval_policy.get("trusted_operations", []),
                    )
                # Create workflow_as_agent instance
                if create_workflow_agent is not None:
                    self._workflow_as_agent = create_workflow_agent(
                        worker_model="gpt-4.1-nano",
                        reviewer_model="gpt-4.1",
                    )
            except Exception as exc:  # pragma: no cover - defensive
                self._initialisation_error = f"Failed to create MagenticFleet: {exc}"

    async def generate_response(
        self,
        entity_id: str,
        *,
        user_text: str | None,
        input_payload: dict | None = None,
        timeout_seconds: int = 120,
        status_callback: (
            Callable[[str, Mapping[str, int | str]], Awaitable[None] | None] | None
        ) = None,
    ) -> tuple[str, dict]:
        """Generate a response string and usage statistics for the given entity."""

        await self.ensure_initialised()

        if self._fleet is None or self._initialisation_error:
            message = self._initialisation_error or "Fleet unavailable."
            if user_text:
                response = f"(offline) Received prompt: {user_text}\n\n{message}"
            elif input_payload:
                payload_str = json.dumps(input_payload, indent=2)
                response = f"(offline) Received payload: {payload_str}\n\n{message}"
            else:
                response = message
            usage = self._estimate_usage(user_text or json.dumps(input_payload or {}))
            return response, usage

        prompt = user_text
        if not prompt and input_payload:
            prompt = json.dumps(input_payload, indent=2)

        if not prompt:
            prompt = "Explain what you can do."

        # Sanitize inputs for logging (prevent log injection)
        safe_entity_id = entity_id.replace("\n", " ").replace("\r", " ")[:100]
        safe_prompt = prompt.replace("\n", " ").replace("\r", " ")[:100]

        logger.info(f"Starting workflow execution for entity: {safe_entity_id}")
        logger.debug(f"Prompt: {safe_prompt}...")
        start_time = time.time()

        result: str
        try:
            async with self._worker_slot(status_callback):
                # Development mode: return mock response immediately
                if DEVELOPMENT_MODE:
                    logger.info("DEVELOPMENT_MODE enabled - returning mock response")
                    await asyncio.sleep(2)  # Simulate some processing
                    mock_response = (
                        "[Mock Response] Received your request: "
                        f"'{prompt[:50]}...'\n\n"
                        "This is a development mode response. The actual MagenticFleet workflow "
                        "is disabled to allow frontend testing. Set DEVELOPMENT_MODE=False in "
                        "runtime.py to enable real workflow execution."
                    )
                    usage = self._estimate_usage(prompt + mock_response)
                    logger.info("Mock response generated successfully")
                    return mock_response, usage

                # Route to appropriate workflow based on entity_id
                if entity_id == "workflow_as_agent" and self._workflow_as_agent is not None:
                    # Use workflow_as_agent pattern
                    accumulated_result: list[str] = []  # type: ignore[unreachable]
                    async for event in self._workflow_as_agent.run_stream(prompt):
                        # Accumulate event strings
                        accumulated_result.append(str(event))
                    result = "\n".join(accumulated_result)
                else:
                    # Default to MagenticFleet
                    result = await asyncio.wait_for(
                        self._fleet.run(prompt), timeout=timeout_seconds
                    )

            elapsed = time.time() - start_time
            logger.info(f"Workflow completed in {elapsed:.2f}s")
            logger.debug(f"Result length: {len(result) if result else 0} chars")

            usage = self._estimate_usage(prompt + (result or ""))
            return result or "No response generated.", usage

        except TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Workflow timeout after {elapsed:.2f}s (limit: {timeout_seconds}s)")
            error_msg = (
                f"The request took longer than {timeout_seconds} seconds to complete. "
                "This might be due to complex processing or network issues. "
                "Please try a simpler query or contact support."
            )
            usage = self._estimate_usage(prompt)
            return error_msg, usage

        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error(f"Workflow error after {elapsed:.2f}s: {exc}", exc_info=True)
            error_msg = f"An error occurred while processing your request: {str(exc)}"
            usage = self._estimate_usage(prompt)
            return error_msg, usage

    @staticmethod
    def _estimate_usage(text: str) -> dict:
        token_guess = max(len(text) // 4, 1)
        prompt_guess = max(len(textwrap.shorten(text, width=200)) // 4, 1)
        total = prompt_guess + token_guess
        return {
            "input_tokens": prompt_guess,
            "output_tokens": token_guess,
            "total_tokens": total,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        }

    async def stream_chunks(
        self,
        entity_id: str,
        *,
        user_text: str | None,
        input_payload: dict | None = None,
        chunk_size: int = 160,
    ) -> AsyncIterator[str]:
        """Stream a response in chunked form for SSE."""

        result, usage = await self.generate_response(
            entity_id,
            user_text=user_text,
            input_payload=input_payload,
        )

        if not result:
            yield ""
            return

        for start in range(0, len(result), chunk_size):
            yield result[start : start + chunk_size]

        # Attach usage metadata to iterator by yielding sentinel JSON
        yield json.dumps({"__usage__": usage})

    async def queue_metrics(self) -> dict[str, int]:
        """Return current queue metrics."""
        async with self._queue_lock:
            return self._queue_snapshot()

    @asynccontextmanager
    async def _worker_slot(
        self,
        status_callback: Callable[[str, Mapping[str, int | str]], Awaitable[None] | None] | None,
    ) -> AsyncIterator[None]:
        metrics = await self._increment_waiters()
        await self._notify_status(status_callback, "queued", metrics)
        await self._semaphore.acquire()
        metrics = await self._mark_running()
        await self._notify_status(status_callback, "started", metrics)
        try:
            yield
        finally:
            self._semaphore.release()
            metrics = await self._mark_finished()
            await self._notify_status(status_callback, "finished", metrics)

    async def _increment_waiters(self) -> dict[str, int]:
        async with self._queue_lock:
            self._queue_waiters += 1
            return self._queue_snapshot()

    async def _mark_running(self) -> dict[str, int]:
        async with self._queue_lock:
            self._queue_waiters = max(0, self._queue_waiters - 1)
            self._inflight += 1
            return self._queue_snapshot()

    async def _mark_finished(self) -> dict[str, int]:
        async with self._queue_lock:
            self._inflight = max(0, self._inflight - 1)
            return self._queue_snapshot()

    async def _notify_status(
        self,
        callback: Callable[[str, Mapping[str, int | str]], Awaitable[None] | None] | None,
        phase: str,
        metrics: Mapping[str, int],
    ) -> None:
        if callback is None:
            return
        payload: dict[str, int | str] = {**metrics, "phase": phase}
        result = callback(phase, payload)
        if asyncio.iscoroutine(result):
            await result

    def _queue_snapshot(self) -> dict[str, int]:
        return {
            "max_parallel": self._max_concurrency,
            "inflight": self._inflight,
            "queued": self._queue_waiters,
        }


def build_entity_catalog() -> tuple[list[dict], list[dict]]:
    """Construct lightweight agent/workflow descriptors from repository config."""

    workflow_cfg = settings.workflow_config or {}
    defaults = workflow_cfg.get("defaults", {})
    manager_cfg = workflow_cfg.get("fleet", {}).get("manager", {})

    agent_entity = {
        "id": "magentic_fleet",
        "type": "agent",
        "name": "Magentic Fleet Orchestrator",
        "description": "Plans and coordinates multi-agent tasks using Microsoft Agent Framework.",
        "framework": "agenticfleet",
        "source": "directory",
        "tools": [],
        "instructions": manager_cfg.get("instructions"),
        "model": manager_cfg.get("model", defaults.get("model")),
        "metadata": {"lazy_loaded": False},
    }

    workflow_entity = {
        "id": "magentic_fleet_workflow",
        "type": "workflow",
        "name": "AgenticFleet Workflow",
        "description": (
            "Default MagenticFleet workflow coordinating researcher, coder, and analyst agents."
        ),
        "framework": "agenticfleet",
        "source": "directory",
        "tools": ["researcher", "coder", "analyst"],
        "executors": ["researcher", "coder", "analyst"],
        "metadata": {"lazy_loaded": False},
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "User task to pass to the MagenticFleet workflow.",
                }
            },
            "required": ["task"],
        },
        "input_type_name": "WorkflowInput",
        "start_executor_id": "magentic_orchestrator",
    }

    workflow_as_agent_entity = {
        "id": "workflow_as_agent",
        "type": "workflow",
        "name": "Reflection & Retry Workflow",
        "description": (
            "Worker generates responses reviewed by Reviewer. Failed responses are "
            "regenerated with feedback until approved. Demonstrates iterative quality improvement."
        ),
        "framework": "agenticfleet",
        "source": "directory",
        "tools": [],
        "executors": ["worker", "reviewer"],
        "metadata": {
            "lazy_loaded": False,
            "pattern": "reflection",
            "quality_assurance": True,
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "User query to process with reflection and review cycle.",
                }
            },
            "required": ["task"],
        },
        "input_type_name": "WorkflowInput",
        "start_executor_id": "worker",
    }

    return [agent_entity], [workflow_entity, workflow_as_agent_entity]
