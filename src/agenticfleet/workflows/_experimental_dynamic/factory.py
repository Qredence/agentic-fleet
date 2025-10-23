"""Workflow factory for dynamic Magentic orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from agent_framework import (
    AgentProtocol,
    CheckpointStorage,
    MagenticBuilder,
    StandardMagenticManager,
    Workflow,
)

from agenticfleet.core.logging import get_logger
from agenticfleet.fleet.callbacks import ConsoleCallbacks

from .modules import create_default_dynamic_participants
from .prompts import MANAGER_PROMPT
from .settings import build_manager_kwargs, make_responses_client

logger = get_logger(__name__)


def create_dynamic_workflow(
    *,
    participants: Mapping[str, AgentProtocol] | None = None,
    include_default_tool_agents: bool = True,
    manager_instructions: str | None = None,
    manager_model: str | None = None,
    progress_ledger_retry_count: int | None = None,
    checkpoint_storage: CheckpointStorage | None = None,
    console_callbacks: ConsoleCallbacks | None = None,
    streaming_enabled: bool = True,
    log_progress: bool = True,
) -> Workflow:
    """
    Build a Magentic workflow with dynamic agent routing and optional tool agents.

    The resulting workflow mirrors the runtime behaviour documented in
    `StandardMagenticManager._run_inner_loop_locked`, where the progress ledger
    decides whether the request is satisfied, whether progress is being made, and
    which participant speaks next.
    """
    if participants is None:
        participant_bundle = create_default_dynamic_participants(
            include_tool_agents=include_default_tool_agents
        )
        participants = participant_bundle.as_dict()
    elif not participants:
        raise ValueError("At least one participant must be supplied.")

    logger.info(
        "Building dynamic Magentic workflow with participants: %s",
        ", ".join(sorted(participants)),
    )

    manager_client = make_responses_client(model=manager_model)

    manager_kwargs = build_manager_kwargs(
        chat_client=manager_client,
        instructions=manager_instructions or MANAGER_PROMPT,
        progress_ledger_retry_count=progress_ledger_retry_count,
    )

    manager = StandardMagenticManager(**manager_kwargs)

    builder = MagenticBuilder().with_standard_manager(manager=manager).participants(**participants)

    if checkpoint_storage is not None:
        builder = builder.with_checkpointing(checkpoint_storage)

    # Attach observability callbacks if provided
    if console_callbacks is not None and (streaming_enabled or log_progress):
        try:
            from agent_framework import (
                MagenticAgentDeltaEvent,
                MagenticAgentMessageEvent,
                MagenticCallbackEvent,
                MagenticCallbackMode,
                MagenticFinalResultEvent,
                MagenticOrchestratorMessageEvent,
            )

            async def unified_callback(event: MagenticCallbackEvent) -> None:
                if isinstance(event, MagenticOrchestratorMessageEvent):
                    if event.kind == "task_ledger" and log_progress:
                        await console_callbacks.plan_creation_callback(event.message)
                    elif event.kind == "progress_ledger" and log_progress:
                        await console_callbacks.progress_ledger_callback(event.message)
                    elif event.kind == "notice" and event.message:
                        await console_callbacks.notice_callback(str(event.message))
                elif isinstance(event, MagenticAgentDeltaEvent):
                    if streaming_enabled:
                        await console_callbacks.agent_delta_callback(event)
                elif isinstance(event, MagenticAgentMessageEvent):
                    if streaming_enabled and event.message:
                        await console_callbacks.agent_message_callback(event.message)
                elif isinstance(event, MagenticFinalResultEvent) and event.message and log_progress:
                    await console_callbacks.final_answer_callback(event.message)

            mode = (
                MagenticCallbackMode.STREAMING
                if streaming_enabled
                else MagenticCallbackMode.NON_STREAMING
            )
            builder = builder.on_event(unified_callback, mode=mode)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Failed to attach dynamic workflow callbacks: %s", exc)

    workflow = builder.build()
    logger.info("Dynamic Magentic workflow created successfully.")
    return cast(Workflow, workflow)


__all__ = ["create_dynamic_workflow"]
