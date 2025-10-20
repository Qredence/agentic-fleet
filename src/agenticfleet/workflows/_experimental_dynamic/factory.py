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

    manager = StandardMagenticManager(**manager_kwargs)  # type: ignore[arg-type]

    builder = MagenticBuilder().with_standard_manager(manager=manager).participants(**participants)

    if checkpoint_storage is not None:
        builder = builder.with_checkpointing(checkpoint_storage)

    workflow = builder.build()
    logger.info("Dynamic Magentic workflow created successfully.")
    return cast(Workflow, workflow)


__all__ = ["create_dynamic_workflow"]
