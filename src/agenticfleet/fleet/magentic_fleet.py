"""Microsoft Agent Framework Magentic-based fleet orchestrator."""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from agenticfleet.agents import create_analyst_agent, create_coder_agent, create_researcher_agent
from agenticfleet.config import settings
from agenticfleet.core.approval import ApprovalDecision
from agenticfleet.core.approved_tools import set_approval_handler
from agenticfleet.core.checkpoints import (
    load_checkpoint_metadata_from_path,
    normalize_checkpoint_metadata,
    sort_checkpoint_metadata,
)
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.exceptions import WorkflowError
from agenticfleet.core.logging import get_logger
from agenticfleet.core.openai import get_responses_model_parameter
from agenticfleet.fleet.callbacks import ConsoleCallbacks
from agenticfleet.fleet.fleet_builder import FleetBuilder

try:  # pragma: no cover - runtime import guard
    from agent_framework import (
        ChatAgent,
        HostedCodeInterpreterTool,
        MagenticAgentDeltaEvent,
        MagenticAgentMessageEvent,
        MagenticBuilder,
        MagenticCallbackEvent,
        MagenticCallbackMode,
        MagenticFinalResultEvent,
        MagenticOrchestratorMessageEvent,
        MagenticPlanReviewDecision,
        MagenticPlanReviewReply,
        MagenticPlanReviewRequest,
        RequestInfoEvent,
        WorkflowOutputEvent,
    )
    from agent_framework.openai import OpenAIChatClient, OpenAIResponsesClient

    _AGENT_FRAMEWORK_AVAILABLE = True
except ModuleNotFoundError as import_error:  # pragma: no cover - fallback for tests
    ChatAgent = None  # type: ignore[misc, assignment]
    HostedCodeInterpreterTool = None  # type: ignore[misc, assignment]
    MagenticAgentDeltaEvent = None  # type: ignore[misc, assignment]
    MagenticAgentMessageEvent = None  # type: ignore[misc, assignment]
    MagenticBuilder = None  # type: ignore[misc, assignment]
    MagenticCallbackEvent = None  # type: ignore[misc, assignment]
    MagenticCallbackMode = None  # type: ignore[misc, assignment]
    MagenticFinalResultEvent = None  # type: ignore[misc, assignment]
    MagenticOrchestratorMessageEvent = None  # type: ignore[misc, assignment]
    MagenticPlanReviewDecision = None  # type: ignore[misc, assignment]
    MagenticPlanReviewReply = None  # type: ignore[misc, assignment]
    MagenticPlanReviewRequest = None  # type: ignore[misc, assignment]
    RequestInfoEvent = None  # type: ignore[misc, assignment]
    WorkflowOutputEvent = None  # type: ignore[misc, assignment]
    OpenAIChatClient = None  # type: ignore[misc, assignment]
    OpenAIResponsesClient = None  # type: ignore[misc, assignment]
    _AGENT_FRAMEWORK_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "agent_framework package not available: %s – running in fallback mode.",
        import_error,
    )
else:  # pragma: no cover - debug logging when dependency is present
    logging.getLogger(__name__).debug(
        "agent_framework components loaded: %s",
        ", ".join(
            [
                ChatAgent.__name__,
                HostedCodeInterpreterTool.__name__,
                MagenticAgentDeltaEvent.__name__,
                MagenticAgentMessageEvent.__name__,
                MagenticBuilder.__name__,
                "MagenticCallbackEvent",  # Union type, no __name__
                MagenticCallbackMode.__name__,
                MagenticFinalResultEvent.__name__,
                MagenticOrchestratorMessageEvent.__name__,
                MagenticPlanReviewReply.__name__,
                RequestInfoEvent.__name__,
                WorkflowOutputEvent.__name__,
                OpenAIChatClient.__name__,
                OpenAIResponsesClient.__name__,
            ]
        ),
    )

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from agent_framework import AgentProtocol, CheckpointStorage

    from agenticfleet.cli.ui import ConsoleUI
else:
    AgentProtocol = Any
    CheckpointStorage = Any
    ConsoleUI = Any

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = get_logger(__name__)

NO_RESPONSE_GENERATED = "No response generated"


class MagenticFleet:
    """
    Magentic-based fleet orchestrator using Microsoft Agent Framework.

    Coordinates specialist agents via Microsoft's Magentic workflow pattern,
    handling plan creation, delegation, optional plan review, and streaming
    observability callbacks surfaced in the CLI.
    """

    def __init__(
        self,
        checkpoint_storage: CheckpointStorage | None = None,
        approval_handler: Any | None = None,
        approval_policy: dict[str, Any] | None = None,
        agents: dict[str, AgentProtocol] | None = None,
        console_callbacks: ConsoleCallbacks | None = None,
    ) -> None:
        self.checkpoint_storage = checkpoint_storage
        self.approval_handler = approval_handler
        self.approval_policy = approval_policy or {}
        self.console_callbacks = console_callbacks or ConsoleCallbacks()
        self.workflow_id: str | None = None
        self._latest_final_text: str | None = None

        if agents is None:
            logger.info("Creating default specialist agents")
            self.agents = self._create_default_agents()
        else:
            logger.info("Using provided specialist agents: %s", list(agents))
            self.agents = agents

        self._apply_coder_tooling()
        self.workflow = self._build_magentic_workflow()

    def _create_default_agents(self) -> dict[str, AgentProtocol]:
        agents: dict[str, AgentProtocol] = {}

        try:
            agents["researcher"] = cast(AgentProtocol, create_researcher_agent())
        except Exception as error:  # pragma: no cover - defensive guard
            logger.warning("Failed to create researcher agent: %s", error)

        try:
            agents["coder"] = cast(AgentProtocol, create_coder_agent())
        except Exception as error:  # pragma: no cover - defensive guard
            logger.warning("Failed to create coder agent: %s", error)

        try:
            agents["analyst"] = cast(AgentProtocol, create_analyst_agent())
        except Exception as error:  # pragma: no cover - defensive guard
            logger.warning("Failed to create analyst agent: %s", error)

        if not agents:
            raise WorkflowError("Failed to create any specialist agents")

        return agents

    def _apply_coder_tooling(self) -> None:
        """Attach hosted code interpreter tooling to the coder agent."""

        if not _AGENT_FRAMEWORK_AVAILABLE or OpenAIResponsesClient is None:
            logger.debug("Skipping coder tooling initialisation (agent_framework unavailable).")
            return

        if HostedCodeInterpreterTool is None:  # type: ignore
            logger.debug("HostedCodeInterpreterTool unavailable; skipping tool injection.")  # type: ignore
            return

        coder = self.agents.get("coder")
        if coder is None:
            logger.debug("No coder agent registered; skipping tooling initialisation.")
            return

        if not hasattr(coder, "chat_client"):
            logger.debug("Coder agent lacks a chat_client attribute; skipping tooling.")
            return

        defaults = settings.workflow_config.get("defaults", {})
        model_name = (
            defaults.get("tool_model")
            or defaults.get("model")
            or getattr(settings, "openai_model", None)
        )

        if not isinstance(model_name, str) or not model_name.strip():
            logger.debug("No model configured for coder tooling; skipping initialisation.")
            return

        responses_param = get_responses_model_parameter(OpenAIResponsesClient)
        try:
            client_kwargs: dict[str, str | None] = {responses_param: model_name}
            chat_client = cast(Any, OpenAIResponsesClient)(**client_kwargs)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to initialise coder chat client: %s", exc)
            return

        try:
            setattr(coder, "chat_client", chat_client)
        except AttributeError:  # pragma: no cover - defensive guard
            logger.debug("Coder agent chat_client attribute is read-only; skipping update.")
        else:
            logger.debug("Configured coder agent chat client with model '%s'.", model_name)

        interpreter_cls = cast(Any, HostedCodeInterpreterTool)

        current_tools = getattr(coder, "tools", None)

        def has_interpreter(tools: Any) -> bool:
            if tools is None:
                return False
            if isinstance(tools, list | tuple | set):
                return any(isinstance(tool, interpreter_cls) for tool in tools)
            return isinstance(tools, interpreter_cls)

        if has_interpreter(current_tools):
            logger.debug("Coder agent already has a HostedCodeInterpreterTool; skipping attach.")
            return

        try:
            interpreter = interpreter_cls()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to instantiate HostedCodeInterpreterTool: %s", exc)
            return

        if current_tools is None:
            setattr(coder, "tools", [interpreter])
        elif isinstance(current_tools, list):
            current_tools.append(interpreter)
        elif isinstance(current_tools, tuple):
            setattr(coder, "tools", current_tools + (interpreter,))
        else:
            setattr(coder, "tools", [current_tools, interpreter])

    def _build_magentic_workflow(self) -> Any:
        """Construct the Magentic workflow with repository conventions."""

        chat_message_store_factory = settings.redis_chat_message_store_factory()

        builder = FleetBuilder(console_callbacks=self.console_callbacks).with_agents(self.agents)
        builder = builder.with_manager(chat_message_store_factory=chat_message_store_factory)
        builder = builder.with_observability()

        if self.checkpoint_storage:
            builder = builder.with_checkpointing(self.checkpoint_storage)

        builder = builder.with_plan_review()
        workflow = builder.build()

        return workflow

    def set_workflow_id(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id

    def set_console_ui(self, ui: ConsoleUI | None) -> None:
        self.console_callbacks.set_ui(ui)

    async def run(
        self,
        user_input: str,
        resume_from_checkpoint: str | None = None,
    ) -> str:
        if not self.workflow_id:
            self.workflow_id = f"fleet_{uuid.uuid4().hex[:8]}"

        run_kwargs: dict[str, Any] = {}
        if resume_from_checkpoint:
            run_kwargs["resume_from_checkpoint"] = resume_from_checkpoint

        run_stream_method = getattr(self.workflow, "run_stream", None)
        send_responses_method = getattr(self.workflow, "send_responses_streaming", None)
        supports_streaming = (
            _AGENT_FRAMEWORK_AVAILABLE
            and run_stream_method is not None
            and callable(run_stream_method)
            and inspect.isasyncgenfunction(run_stream_method)
        )

        if not supports_streaming:
            logger.debug("Fallback workflow execution (agent_framework unavailable)")
            result = await self.workflow.run(user_input, **run_kwargs)
            final_render = self.console_callbacks.consume_final_render()
            if final_render and final_render.raw_text:
                self._latest_final_text = final_render.raw_text
                return final_render.raw_text
            answer = self._extract_final_answer_from_result(result)
            if answer != NO_RESPONSE_GENERATED:
                self._latest_final_text = answer
            return answer

        pending_request: Any | None = None
        pending_responses: dict[str, Any] | None = None
        final_output_text: str | None = None
        completed = False
        resume_token_used = resume_from_checkpoint is not None

        while True:
            stream: Any | None = None
            if (
                pending_responses
                and callable(send_responses_method)
                and inspect.isasyncgenfunction(send_responses_method)
            ):
                stream = send_responses_method(pending_responses, **run_kwargs)
            elif run_stream_method is not None:
                stream = run_stream_method(user_input, **run_kwargs)
            else:
                break

            if resume_token_used:
                run_kwargs.pop("resume_from_checkpoint", None)
                resume_token_used = False

            pending_responses = None
            had_events = False

            if stream is not None:
                async for event in stream:
                    had_events = True
                    if MagenticAgentDeltaEvent is not None and isinstance(
                        event, MagenticAgentDeltaEvent
                    ):
                        continue
                    if (
                        RequestInfoEvent is not None
                        and MagenticPlanReviewRequest is not None
                        and isinstance(event, RequestInfoEvent)
                        and event.request_type is MagenticPlanReviewRequest
                    ):
                        pending_request = event
                    elif WorkflowOutputEvent is not None and isinstance(event, WorkflowOutputEvent):
                        if event.data is not None:
                            final_output_text = str(event.data)
                        completed = True
                    elif (
                        MagenticFinalResultEvent is not None
                        and isinstance(event, MagenticFinalResultEvent)
                        and event.message is not None
                    ):
                        self._latest_final_text = getattr(event.message, "text", None) or str(
                            event.message
                        )
                    elif (
                        MagenticAgentMessageEvent is not None
                        and isinstance(event, MagenticAgentMessageEvent)
                        and event.message is not None
                    ):
                        self._latest_final_text = getattr(event.message, "text", None) or str(
                            event.message
                        )

            if pending_request is not None:
                reply = await self._handle_plan_review_request(pending_request)
                pending_responses = {pending_request.request_id: reply}
                pending_request = None
                continue

            if completed or not had_events:
                break

        final_render = self.console_callbacks.consume_final_render()
        if final_render and final_render.raw_text:
            self._latest_final_text = final_render.raw_text
            return final_render.raw_text

        if self._latest_final_text:
            return self._latest_final_text

        if final_output_text:
            return final_output_text

        return NO_RESPONSE_GENERATED

    def _extract_final_answer_from_result(self, result: object) -> str:
        """Best-effort extraction of a final answer from workflow output."""

        if result is None:
            return NO_RESPONSE_GENERATED

        if hasattr(result, "output"):
            output = result.output  # type: ignore[attr-defined]
            if isinstance(output, str):
                return output
            if hasattr(output, "content"):
                content_value = getattr(output, "content")
                if content_value is not None:
                    return str(content_value)
            if output is not None:
                return str(output)

        if hasattr(result, "content"):
            content = result.content  # type: ignore[attr-defined]
            if content is not None:
                return str(content)

        result_str = str(result)
        if result_str and result_str != "None" and not result_str.startswith("<MagicMock"):
            return result_str

        logger.warning("Could not extract final answer from result: %s", type(result).__name__)
        return NO_RESPONSE_GENERATED

    async def _handle_plan_review_request(
        self,
        event: Any,
    ) -> Any:
        if MagenticPlanReviewReply is None or MagenticPlanReviewDecision is None:
            raise WorkflowError(
                "Plan review handling requested but agent framework is unavailable."
            )

        request = cast(Any, event.data)
        await self.console_callbacks.notice_callback("Plan review requested.")
        await asyncio.sleep(0)

        if self.approval_handler is not None:
            approval_request = create_approval_request(
                operation_type="plan_review",
                agent_name="magentic_orchestrator",
                operation="Approve or revise plan",
                details={
                    "task_text": request.task_text,
                    "facts_text": request.facts_text,
                    "plan_text": request.plan_text,
                    "round_index": request.round_index,
                },
            )
            response = await self.approval_handler.request_approval(approval_request)

            if response.decision == ApprovalDecision.APPROVED:
                edited = response.modified_code if response.modified_code else None
                return MagenticPlanReviewReply(
                    decision=MagenticPlanReviewDecision.APPROVE,
                    edited_plan_text=edited,
                    comments=response.reason,
                )

            if response.decision == ApprovalDecision.MODIFIED:
                return MagenticPlanReviewReply(
                    decision=MagenticPlanReviewDecision.APPROVE,
                    edited_plan_text=response.modified_code,
                    comments=response.reason,
                )

            return MagenticPlanReviewReply(
                decision=MagenticPlanReviewDecision.REVISE,
                comments=response.reason or "Reviewer requested a revised plan.",
            )

        return MagenticPlanReviewReply(decision=MagenticPlanReviewDecision.APPROVE)

    async def list_checkpoints(self) -> list[dict[str, Any]]:
        storage = self.checkpoint_storage

        if storage and hasattr(storage, "list_checkpoints"):
            try:
                raw_checkpoints = await storage.list_checkpoints()
            except Exception as error:  # pragma: no cover - defensive guard
                logger.warning("Failed to read checkpoints from storage: %s", error)
            else:
                normalized = [
                    checkpoint_dict
                    for checkpoint_dict in (
                        normalize_checkpoint_metadata(checkpoint)
                        for checkpoint in (raw_checkpoints or [])
                    )
                    if checkpoint_dict is not None
                ]
                return sort_checkpoint_metadata(normalized)

        fallback_path = self._default_checkpoint_directory()
        logger.debug("Scanning local checkpoint directory at %s", fallback_path)
        return await asyncio.to_thread(
            load_checkpoint_metadata_from_path,
            fallback_path,
        )

    def _default_checkpoint_directory(self) -> Path:
        checkpoint_config = (
            settings.workflow_config.get("workflow", {}).get("checkpointing", {}) or {}
        )
        storage_path = checkpoint_config.get("storage_path", "./var/checkpoints")
        # Inline legacy path normalization logic to avoid private API dependency
        old_prefix = "checkpoints"
        new_prefix = "var/checkpoints"
        if isinstance(storage_path, str) and storage_path.startswith(old_prefix):
            storage_path = storage_path.replace(old_prefix, new_prefix, 1)
        try:
            return Path(storage_path).expanduser()
        except TypeError:  # pragma: no cover - defensive guard
            logger.debug(
                "Invalid checkpoint storage path configured (%r); using default ./var/checkpoints",
                storage_path,
            )
            return Path("var/checkpoints")


def create_default_fleet(console_ui: ConsoleUI | None = None) -> MagenticFleet:
    """
    Instantiate a MagenticFleet wired to the repository defaults.

    Args:
        console_ui: Optional CLI UI implementation used to render streaming callbacks.

    Returns:
        A configured MagenticFleet ready for execution.
    """

    checkpoint_storage = settings.create_checkpoint_storage()
    approval_handler = None
    hitl_config = settings.workflow_config.get("workflow", {}).get("human_in_the_loop", {}) or {}

    if hitl_config.get("enabled", False):
        from agenticfleet.core.cli_approval import CLIApprovalHandler

        timeout_seconds = hitl_config.get("approval_timeout_seconds", 300)
        auto_reject = hitl_config.get("auto_reject_on_timeout", False)
        approval_handler = CLIApprovalHandler(
            timeout_seconds=timeout_seconds,
            auto_reject_on_timeout=auto_reject,
        )
        logger.info(
            "HITL enabled with timeout=%s, auto_reject=%s",
            timeout_seconds,
            auto_reject,
        )
        set_approval_handler(
            approval_handler,
            require_operations=hitl_config.get("require_approval_for", []),
            trusted_operations=hitl_config.get("trusted_operations", []),
        )
    else:
        set_approval_handler(None)

    console_callbacks = ConsoleCallbacks(console_ui)

    return MagenticFleet(
        checkpoint_storage=checkpoint_storage,
        approval_policy=hitl_config,
        approval_handler=approval_handler,
        console_callbacks=console_callbacks,
    )
