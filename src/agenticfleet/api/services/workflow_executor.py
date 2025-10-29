from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from agent_framework.exceptions import ServiceInitializationError, ServiceResponseException
from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.api.event_collector import EventCollector
from agenticfleet.api.models.chat_models import ExecutionStatus
from agenticfleet.api.state import BackendState

LOGGER = logging.getLogger(__name__)

DEFAULT_RESPONSES_MODEL = "gpt-5-mini"
ASSISTANT_INSTRUCTION = (
    "You are the AgenticFleet assistant. Provide concise, accurate updates about the "
    "multi-agent orchestration system, highlighting how the manager coordinates the "
    "researcher, coder, and reviewer agents with dynamic spawning and human-in-the-loop approvals."
)
FALLBACK_SUMMARY = (
    "AgenticFleet is a multi-agent orchestration framework that unites a planning manager with "
    "specialist researcher, coder, and reviewer agents. It supports dynamic agent spawning, "
    "human-in-the-loop approvals, checkpointing, and detailed observability so teams can tackle "
    "complex tasks reliably."
)


async def execute_workflow_background(
    state: BackendState,
    execution_id: str,
    workflow_id: str,
    user_message: str,
) -> None:
    """Execute a workflow and stream events through the websocket manager."""

    redis_client = state.redis_client
    ws_manager = state.websocket_manager
    event_collector = EventCollector(execution_id)

    if redis_client:
        try:
            await redis_client.update_status(execution_id, ExecutionStatus.RUNNING)
        except Exception as exc:  # pragma: no cover - Redis is optional in tests
            LOGGER.warning("Failed to update status in Redis: %s", exc)

    try:
        workflow = state.workflow_factory.create_from_yaml(workflow_id)

        async def stream_events() -> None:
            while True:
                event = await event_collector.get_event(timeout=1.0)
                if event:
                    await ws_manager.send_json(event, execution_id)
                    if event["type"] in ("complete", "error"):
                        break

        stream_task = asyncio.create_task(stream_events())

        try:
            result = await asyncio.wait_for(
                workflow.run(user_message, include_status_events=True),
                timeout=120.0,
            )

            from agent_framework import (
                MagenticAgentDeltaEvent,
                MagenticAgentMessageEvent,
                MagenticFinalResultEvent,
            )

            for event in result:
                if isinstance(event, MagenticAgentDeltaEvent):
                    event_collector.handle_agent_delta(event)
                elif isinstance(event, MagenticAgentMessageEvent):
                    event_collector.handle_agent_message(event)
                elif isinstance(event, MagenticFinalResultEvent):
                    event_collector.handle_final_result(event)
                    break

            if redis_client:
                state_snapshot = await redis_client.get_state(execution_id)
                if state_snapshot:
                    state_snapshot.status = ExecutionStatus.COMPLETED
                    state_snapshot.completed_at = datetime.utcnow()
                    state_snapshot.messages = event_collector.messages
                    await redis_client.save_state(state_snapshot)

        except asyncio.TimeoutError as exc:
            LOGGER.error("Workflow execution timed out for %s", execution_id)
            event_collector.handle_error(exc)
            if redis_client:
                await redis_client.update_status(execution_id, ExecutionStatus.TIMEOUT, str(exc))
            await ws_manager.send_json(
                {
                    "type": "error",
                    "execution_id": execution_id,
                    "data": {"error": "Workflow execution timed out"},
                },
                execution_id,
            )
        except Exception as exc:  # pragma: no cover - safety net
            LOGGER.exception("Workflow execution failed for %s", execution_id)
            event_collector.handle_error(exc)
            if redis_client:
                await redis_client.update_status(execution_id, ExecutionStatus.FAILED, str(exc))
            await ws_manager.send_json(
                {
                    "type": "error",
                    "execution_id": execution_id,
                    "data": {"error": str(exc)},
                },
                execution_id,
            )
        finally:
            if not stream_task.done():
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:  # pragma: no cover - cancellation guard
                    pass
            else:
                await stream_task
    finally:
        await state.websocket_manager.disconnect_all_for_execution(execution_id)


def format_sse_event(event: dict[str, Any]) -> bytes:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n".encode()


async def build_assistant_reply(user_text: str | None) -> tuple[str, str, dict[str, int | None]]:
    prompt = (user_text or "Provide a concise overview of AgenticFleet for a new user.").strip()
    request_payload = (
        f"{ASSISTANT_INSTRUCTION}\n\n"
        "Summarise the following request with actionable highlights about AgenticFleet's "
        "architecture, dynamic agent spawning, and human-in-the-loop safeguards."
        f"\n\nRequest:\n{prompt}"
    )

    usage: dict[str, int | None] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    try:
        client = OpenAIResponsesClient(model_id=DEFAULT_RESPONSES_MODEL)
        response = await client.get_response(request_payload)
        text = (response.text or "").strip()
        if not text and response.messages:
            text = "\n".join(msg.text for msg in response.messages if getattr(msg, "text", ""))
        if not text:
            text = FALLBACK_SUMMARY

        if response.usage_details:
            usage = {
                "input_tokens": response.usage_details.input_token_count,
                "output_tokens": response.usage_details.output_token_count,
                "total_tokens": response.usage_details.total_token_count,
            }

        return text, response.model_id or DEFAULT_RESPONSES_MODEL, usage
    except (ServiceInitializationError, ServiceResponseException) as exc:
        LOGGER.exception(
            "OpenAI Responses client failed (%s); falling back to static summary",
            exc,
            exc_info=True,
        )
        fallback = FALLBACK_SUMMARY
        if user_text:
            fallback = (
                f"{fallback}\n\nI wasn't able to reach the model for this specific request, but here's a "
                "refresher on AgenticFleet. Your original prompt was: "
                f"{user_text.strip()}"
            )
        return fallback, DEFAULT_RESPONSES_MODEL, usage
    except Exception as exc:  # pragma: no cover - guard for unexpected client errors
        LOGGER.exception("Unexpected error while generating assistant reply", exc_info=True)
        fallback = FALLBACK_SUMMARY
        if user_text:
            fallback = (
                f"{fallback}\n\nWe encountered an unexpected issue while processing your request: {exc}."
                f"\nOriginal prompt: {user_text.strip()}"
            )
        return fallback, DEFAULT_RESPONSES_MODEL, usage
