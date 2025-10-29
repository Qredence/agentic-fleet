"""Workflow factories built on Microsoft Agent Framework's Magentic primitives.

This module provides factory functions for creating Magentic workflows without
module-level side effects. All workflows are created on-demand via factory functions.

For YAML-driven workflow creation, see haxui.workflow_factory.WorkflowFactory.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from agent_framework import (
    ChatAgent,
    HostedCodeInterpreterTool,
    MagenticAgentDeltaEvent,
    MagenticAgentMessageEvent,
    MagenticBuilder,
    MagenticFinalResultEvent,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)
from agent_framework.openai import OpenAIResponsesClient
from dotenv import load_dotenv

if TYPE_CHECKING:
    from agent_framework import Workflow

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL_ID = "gpt-5-mini"
_MAGENTIC_REASONING_OPTIONS = {"effort": "high", "verbosity": "verbose"}

EXECUTOR_PROMPT = """You are the executor module. Carry out the active instruction from the
manager or planner. Execute reasoning-heavy steps, delegate to registered tools when needed,
and produce clear artefacts or status updates. If a tool is required, call it explicitly and
then explain the outcome."""

VERIFIER_PROMPT = """You are the verifier module. Inspect the current state, outputs, and
assumptions. Confirm whether the work satisfies requirements, highlight defects or missing
information, and suggest concrete follow-up actions."""

GENERATOR_PROMPT = """You are the generator module. Assemble the final response for the
user. Incorporate verified outputs, cite supporting evidence when available, and ensure the
result addresses the original request without leaking internal reasoning unless explicitly
requested."""

CODER_INSTRUCTIONS = (
    "You are the coder. Write and execute code as needed to unblock the team. Produce "
    "well-documented snippets, explain results, and call the hosted interpreter tool "
    "for calculations or data analysis."
)

# Collaboration workflow instructions
COLLABORATION_RESEARCHER_INSTRUCTIONS = (
    "You are the researcher. Gather evidence, explore contexts, and provide comprehensive "
    "background information to support the team's work."
)

COLLABORATION_CODER_INSTRUCTIONS = CODER_INSTRUCTIONS

COLLABORATION_REVIEWER_INSTRUCTIONS = (
    "You are the reviewer. Validate work quality, check for errors and inconsistencies, "
    "and suggest improvements to ensure high-quality outputs."
)

COLLABORATION_MANAGER_INSTRUCTIONS = (
    "You are the manager. Coordinate the team of researcher, coder, and reviewer. "
    "Delegate tasks strategically and synthesize their outputs into final answers."
)

# Magentic Fleet instructions
MAGENTIC_FLEET_PLANNER_INSTRUCTIONS = (
    "You are the planner. Break down complex requests into clear, actionable steps. "
    "Assign ownership and define success criteria for each step."
)

MAGENTIC_FLEET_EXECUTOR_INSTRUCTIONS = EXECUTOR_PROMPT

MAGENTIC_FLEET_CODER_INSTRUCTIONS = CODER_INSTRUCTIONS

MAGENTIC_FLEET_VERIFIER_INSTRUCTIONS = VERIFIER_PROMPT

MAGENTIC_FLEET_GENERATOR_INSTRUCTIONS = GENERATOR_PROMPT

MAGENTIC_FLEET_MANAGER_INSTRUCTIONS = (
    "You are the orchestrator managing a five-agent team: planner, executor, coder, "
    "verifier, and generator. Coordinate their work strategically to deliver comprehensive "
    "solutions. Leverage the planner for decomposition, executor for implementation, "
    "coder for technical tasks, verifier for quality assurance, and generator for synthesis."
)


# Event handlers for workflow observability
def handle_orchestrator_message(event: MagenticOrchestratorMessageEvent) -> None:
    """Handle manager's planning and coordination messages.

    The orchestrator emits messages during planning, agent selection, and coordination.
    These messages reveal the manager's decision-making process.
    """
    message_text = getattr(event.message, "text", "")
    logger.info(f"🎯 Manager [{event.kind}]: {message_text[:100]}...")


def handle_agent_delta(event: MagenticAgentDeltaEvent) -> None:
    """Handle streaming agent output in real-time.

    Delta events contain incremental text chunks as agents generate responses.
    Use this for live streaming output to users.
    """
    if event.text:
        print(event.text, end="", flush=True)


def handle_agent_message(event: MagenticAgentMessageEvent) -> None:
    """Handle complete agent messages after streaming finishes.

    Message events contain the complete response from an agent.
    Useful for logging and processing finished agent outputs.
    """
    agent_id = event.agent_id
    message = event.message
    if message is not None:
        text = getattr(message, "text", "")
        logger.info(f"✓ {agent_id}: {text[:80]}...")


def handle_final_result(event: MagenticFinalResultEvent) -> None:
    """Handle workflow final result.

    The final result event signals workflow completion and contains
    the synthesized output from all agent interactions.
    """
    if event.message is not None:
        result_text = getattr(event.message, "text", "")
        logger.info(f"🎉 Final result: {result_text[:100]}...")


def handle_workflow_output(event: WorkflowOutputEvent) -> None:
    """Handle structured workflow output data.

    Output events contain structured data produced by the workflow,
    separate from the text-based final result.
    """
    logger.debug(f"📊 Workflow output: {event.data}")


MAGENTIC_FLEET_DEFAULT_MODEL = _MODEL_ID


def _create_responses_client(
    model: str | None = None,
    *,
    reasoning: dict[str, str] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    store: bool | None = None,
) -> OpenAIResponsesClient:
    """Create an OpenAI Responses client with optional customisation."""
    kwargs: dict[str, Any] = {"model_id": model or _MODEL_ID}
    if reasoning is not None:
        kwargs["reasoning"] = reasoning
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if store is not None:
        kwargs["store"] = store
    return OpenAIResponsesClient(**kwargs)


def create_collaboration_workflow(
    *,
    participant_model: str | None = None,
    manager_model: str | None = None,
    researcher_instructions: str | None = None,
    coder_instructions: str | None = None,
    reviewer_instructions: str | None = None,
    manager_instructions: str | None = None,
    max_round_count: int = 12,
    max_stall_count: int = 3,
    max_reset_count: int = 1,
) -> Workflow:
    """Build a Magentic workflow with researcher, coder, reviewer collaboration."""
    participant_client = _create_responses_client(
        participant_model,
        reasoning=_MAGENTIC_REASONING_OPTIONS,
    )
    manager_client = _create_responses_client(
        manager_model or participant_model,
        reasoning=_MAGENTIC_REASONING_OPTIONS,
    )

    researcher = participant_client.create_agent(
        name="researcher",
        instructions=researcher_instructions or COLLABORATION_RESEARCHER_INSTRUCTIONS,
        description="Research specialist who gathers evidence and context",
    )
    coder = participant_client.create_agent(
        name="coder",
        instructions=coder_instructions or COLLABORATION_CODER_INSTRUCTIONS,
        description="Engineer responsible for implementing solutions",
    )
    reviewer = participant_client.create_agent(
        name="reviewer",
        instructions=reviewer_instructions or COLLABORATION_REVIEWER_INSTRUCTIONS,
        description="Reviewer who validates and refines outputs",
    )

    builder = (
        MagenticBuilder()
        .participants(researcher=researcher, coder=coder, reviewer=reviewer)
        .with_standard_manager(
            chat_client=manager_client,
            instructions=manager_instructions or COLLABORATION_MANAGER_INSTRUCTIONS,
            max_round_count=max_round_count,
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
        )
    )

    return builder.build()


def create_magentic_fleet_workflow(
    *,
    planner_model: str | None = None,
    executor_model: str | None = None,
    coder_model: str | None = None,
    verifier_model: str | None = None,
    generator_model: str | None = None,
    manager_model: str | None = None,
    planner_instructions: str | None = None,
    executor_instructions: str | None = None,
    coder_instructions: str | None = None,
    verifier_instructions: str | None = None,
    generator_instructions: str | None = None,
    manager_instructions: str | None = None,
    max_round_count: int = 6,
    max_stall_count: int = 3,
    max_reset_count: int = 2,
) -> Workflow:
    """Construct the five-agent orchestration showcased in the Magentic Fleet notebook."""
    default_model = MAGENTIC_FLEET_DEFAULT_MODEL
    planner_model = planner_model or default_model
    executor_model = executor_model or default_model
    coder_model = coder_model or default_model
    verifier_model = verifier_model or default_model
    generator_model = generator_model or default_model
    manager_model = manager_model or default_model

    planner = ChatAgent(
        name="planner",
        description="Decomposes the request into actionable steps and assigns ownership.",
        instructions=planner_instructions or MAGENTIC_FLEET_PLANNER_INSTRUCTIONS,
        chat_client=_create_responses_client(
            planner_model,
            temperature=0.5,
            max_tokens=4096,
            store=True,
            reasoning={"effort": "high"},
        ),
    )
    executor = ChatAgent(
        name="executor",
        description="Executes active plan steps and coordinates other specialists.",
        instructions=executor_instructions or MAGENTIC_FLEET_EXECUTOR_INSTRUCTIONS,
        chat_client=_create_responses_client(
            executor_model,
            temperature=0.6,
            max_tokens=4096,
            store=True,
            reasoning={"effort": "medium"},
        ),
    )
    coder = ChatAgent(
        name="coder",
        description="Writes and executes code to unblock the team.",
        instructions=coder_instructions or MAGENTIC_FLEET_CODER_INSTRUCTIONS,
        chat_client=_create_responses_client(
            coder_model,
            temperature=0.3,
            max_tokens=8192,
            store=True,
            reasoning={"effort": "high"},
        ),
        tools=HostedCodeInterpreterTool(),
    )
    verifier = ChatAgent(
        name="verifier",
        description="Validates intermediate outputs and flags quality issues.",
        instructions=verifier_instructions or MAGENTIC_FLEET_VERIFIER_INSTRUCTIONS,
        chat_client=_create_responses_client(
            verifier_model,
            temperature=0.5,
            max_tokens=4096,
            store=True,
            reasoning={"effort": "high"},
        ),
    )
    generator = ChatAgent(
        name="generator",
        description="Synthesises verified work into the final answer.",
        instructions=generator_instructions or MAGENTIC_FLEET_GENERATOR_INSTRUCTIONS,
        chat_client=_create_responses_client(
            generator_model,
            temperature=0.8,
            max_tokens=6144,
            store=True,
            reasoning={"effort": "low"},
        ),
    )

    manager_client = _create_responses_client(
        manager_model,
        temperature=0.6,
        max_tokens=8192,
        store=True,
        reasoning={"effort": "high"},
    )

    builder = (
        MagenticBuilder()
        .participants(
            planner=planner,
            executor=executor,
            coder=coder,
            verifier=verifier,
            generator=generator,
        )
        .with_standard_manager(
            chat_client=manager_client,
            instructions=manager_instructions or MAGENTIC_FLEET_MANAGER_INSTRUCTIONS,
            max_round_count=max_round_count,
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
        )
    )
    return builder.build()


__all__: Sequence[str] = [
    # Instruction constants
    "COLLABORATION_CODER_INSTRUCTIONS",
    "COLLABORATION_MANAGER_INSTRUCTIONS",
    "COLLABORATION_RESEARCHER_INSTRUCTIONS",
    "COLLABORATION_REVIEWER_INSTRUCTIONS",
    "MAGENTIC_FLEET_CODER_INSTRUCTIONS",
    "MAGENTIC_FLEET_DEFAULT_MODEL",
    "MAGENTIC_FLEET_EXECUTOR_INSTRUCTIONS",
    "MAGENTIC_FLEET_GENERATOR_INSTRUCTIONS",
    "MAGENTIC_FLEET_MANAGER_INSTRUCTIONS",
    "MAGENTIC_FLEET_PLANNER_INSTRUCTIONS",
    "MAGENTIC_FLEET_VERIFIER_INSTRUCTIONS",
    # Event types (re-exported for convenience)
    "MagenticAgentDeltaEvent",
    "MagenticAgentMessageEvent",
    "MagenticFinalResultEvent",
    "MagenticOrchestratorMessageEvent",
    "WorkflowOutputEvent",
    # Workflow factories
    "create_collaboration_workflow",
    "create_magentic_fleet_workflow",
    "handle_agent_delta",
    "handle_agent_message",
    "handle_final_result",
    # Event handlers
    "handle_orchestrator_message",
    "handle_workflow_output",
]
