"""WebSocket chat streaming service.

This module holds the implementation behind the `/api/ws/chat` WebSocket endpoint.
Routes should stay thin and delegate to this service for:
- Origin validation
- Session lifecycle management
- Multi-turn AgentThread caching
- Workflow event streaming → StreamEvent mapping
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from agent_framework._threads import AgentThread
else:
    try:
        from agent_framework._threads import AgentThread
    except Exception:  # pragma: no cover - optional dependency / stubbed environments

        class AgentThread:  # type: ignore[no-redef]
            """Fallback AgentThread stub used when agent-framework is unavailable."""

            pass


from fastapi import HTTPException, WebSocket, WebSocketDisconnect, status

from agentic_fleet.api.events.mapping import classify_event, map_workflow_event
from agentic_fleet.evaluation.background import schedule_quality_evaluation
from agentic_fleet.models import (
    ChatRequest,
    MessageRole,
    StreamEvent,
    StreamEventType,
    WorkflowResumeRequest,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.services.chat_helpers import (
    _get_or_create_thread,
    _hydrate_thread_from_conversation,
    _log_stream_event,
    _message_role_value,
    _prefer_service_thread_mode,
    _sanitize_log_input,
    _thread_has_any_messages,
)
from agentic_fleet.utils.cfg import load_config
from agentic_fleet.utils.cfg.settings import get_settings
from agentic_fleet.utils.infra.logging import setup_logger
from agentic_fleet.workflows.config import build_workflow_config_from_yaml
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

logger = setup_logger(__name__)


_UNSET_TASK: object = object()


async def _event_generator(
    workflow: Any,
    session: WorkflowSession,
    session_manager: Any,
    *,
    task: str | object | None = _UNSET_TASK,
    log_reasoning: bool = False,
    reasoning_effort: str | None = None,
    cancel_event: asyncio.Event | None = None,
    thread: AgentThread | None = None,
    conversation_history: list[Any] | None = None,
    checkpoint_id: str | None = None,
    checkpoint_storage: Any | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Generate streaming events from workflow execution."""
    accumulated_reasoning = ""
    has_error = False
    error_message = ""

    try:
        await session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        logger.info(
            "Starting workflow stream: workflow_id=%s, task_preview=%s",
            session.workflow_id,
            session.task[:50],
        )

        init_event_type = StreamEventType.ORCHESTRATOR_MESSAGE
        init_category, init_ui_hint = classify_event(init_event_type)
        init_event = StreamEvent(
            type=init_event_type,
            message="Starting workflow execution...",
            category=init_category,
            ui_hint=init_ui_hint,
            workflow_id=session.workflow_id,
        )
        init_event.log_line = _log_stream_event(init_event, session.workflow_id)
        yield init_event.to_sse_dict()

        stream_kwargs: dict[str, Any] = {
            "reasoning_effort": reasoning_effort,
            "thread": thread,
            "conversation_history": conversation_history,
            # Align workflow history ids with the session id used by the websocket surface.
            "workflow_id": session.workflow_id,
            # We'll evaluate quality after sending the final answer so users don't wait.
            "schedule_quality_eval": False,
        }

        run_task: str | None
        if task is _UNSET_TASK:
            run_task = session.task
            is_resume = False
        elif task is None:
            run_task = None
            is_resume = True
        else:
            if not isinstance(task, str):
                raise TypeError("task override must be str | None")
            run_task = task
            is_resume = False

        # IMPORTANT: agent-framework requires message XOR checkpoint_id.
        # - new run: task/message provided => omit checkpoint_id
        # - resume: task/message omitted (None) => include checkpoint_id
        if checkpoint_id is not None and is_resume:
            stream_kwargs["checkpoint_id"] = checkpoint_id
        elif checkpoint_id is not None and not is_resume:
            logger.debug(
                "Ignoring checkpoint_id for new run in websocket streaming generator (checkpoint_id=%s)",
                checkpoint_id,
            )

        if checkpoint_storage is not None:
            stream_kwargs["checkpoint_storage"] = checkpoint_storage

        async for event in workflow.run_stream(run_task, **stream_kwargs):
            if cancel_event is not None and cancel_event.is_set():
                logger.info("Workflow cancelled: workflow_id=%s", session.workflow_id)
                break

            stream_event, accumulated_reasoning = map_workflow_event(event, accumulated_reasoning)
            if stream_event is None:
                continue

            events_to_emit = stream_event if isinstance(stream_event, list) else [stream_event]
            for se in events_to_emit:
                se.workflow_id = session.workflow_id
                log_line = _log_stream_event(se, session.workflow_id)
                if log_line:
                    se.log_line = log_line
                yield se.to_sse_dict()

    except Exception as exc:
        has_error = True
        error_message = str(exc)
        logger.error(
            "Workflow stream error: workflow_id=%s, error=%s",
            session.workflow_id,
            error_message,
            exc_info=True,
        )

        error_event_type = StreamEventType.ERROR
        error_category, error_ui_hint = classify_event(error_event_type)
        error_event = StreamEvent(
            type=error_event_type,
            error=error_message,
            reasoning_partial=bool(accumulated_reasoning) if accumulated_reasoning else None,
            category=error_category,
            ui_hint=error_ui_hint,
            workflow_id=session.workflow_id,
        )
        error_event.log_line = _log_stream_event(error_event, session.workflow_id)
        yield error_event.to_sse_dict()

    finally:
        final_status = WorkflowStatus.FAILED if has_error else WorkflowStatus.COMPLETED
        await session_manager.update_status(
            session.workflow_id,
            final_status,
            completed_at=datetime.now(),
        )

        if log_reasoning and accumulated_reasoning:
            logger.info(
                "Workflow reasoning captured: workflow_id=%s, reasoning_length=%d",
                session.workflow_id,
                len(accumulated_reasoning),
            )

        done_event_type = StreamEventType.DONE
        done_category, done_ui_hint = classify_event(done_event_type)
        done_event = StreamEvent(
            type=done_event_type,
            category=done_category,
            ui_hint=done_ui_hint,
            workflow_id=session.workflow_id,
        )
        done_event.log_line = _log_stream_event(done_event, session.workflow_id)
        yield done_event.to_sse_dict()

        logger.info(
            "Workflow stream completed: workflow_id=%s, status=%s, had_error=%s",
            session.workflow_id,
            final_status.value,
            has_error,
        )


def _validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket connection origin against allowed CORS origins."""
    settings = get_settings()
    origin = websocket.headers.get("origin", "")

    # Allow connections without origin header (same-origin, CLI tools, etc.)
    if not origin:
        return True

    if settings.ws_allow_localhost:
        localhost_patterns = (
            "http://localhost:",
            "http://127.0.0.1:",
            "https://localhost:",
            "https://127.0.0.1:",
        )
        if any(origin.startswith(p) for p in localhost_patterns):
            return True

    if "*" in settings.cors_allowed_origins:
        return True

    if origin in settings.cors_allowed_origins:
        return True

    logger.warning(
        "WebSocket connection rejected: invalid origin '%s'", _sanitize_log_input(origin)
    )
    return False


class ChatWebSocketService:
    """Service implementing the WebSocket chat protocol at `/api/ws/chat`."""

    async def _send_error_and_close(
        self, websocket: WebSocket, error_message: str, workflow_id: str | None = None
    ) -> None:
        """Send error event and close WebSocket connection."""
        error_type = StreamEventType.ERROR
        error_category, error_ui_hint = classify_event(error_type)
        error_event = StreamEvent(
            type=error_type,
            error=error_message,
            category=error_category,
            ui_hint=error_ui_hint,
            workflow_id=workflow_id,
        )
        await websocket.send_json(error_event.to_sse_dict())
        await websocket.close()

    async def _initialize_managers(
        self, websocket: WebSocket
    ) -> tuple[Any, Any] | None:
        """Initialize and validate session and conversation managers."""
        app = websocket.app
        session_manager = (
            app.state.session_manager if hasattr(app.state, "session_manager") else None
        )
        conversation_manager = (
            app.state.conversation_manager if hasattr(app.state, "conversation_manager") else None
        )

        if session_manager is None or conversation_manager is None:
            logger.error("Required managers not available in app state")
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "Server not initialized",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close()
            return None

        return session_manager, conversation_manager

    async def _initialize_workflow(self, websocket: WebSocket) -> Any | None:
        """Get or create shared SupervisorWorkflow from app state."""
        app = websocket.app
        try:
            workflow = getattr(app.state, "supervisor_workflow", None)
            if workflow is None:
                yaml_config = getattr(app.state, "yaml_config", None)
                if yaml_config is None:
                    logger.warning(
                        "YAML config not found in app.state, loading from file (should not happen in normal operation)"
                    )
                    yaml_config = load_config(validate=False)

                workflow_config = build_workflow_config_from_yaml(
                    yaml_config,
                    compile_dspy=False,
                )

                workflow = await create_supervisor_workflow(
                    compile_dspy=False,
                    config=workflow_config,
                    dspy_routing_module=getattr(app.state, "dspy_routing_module", None),
                    dspy_quality_module=getattr(app.state, "dspy_quality_module", None),
                    dspy_tool_planning_module=getattr(app.state, "dspy_tool_planning_module", None),
                )
                app.state.supervisor_workflow = workflow
            return workflow
        except Exception as exc:
            logger.error(
                "Failed to initialize workflow for WebSocket session: %s", exc, exc_info=True
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "error": "Workflow initialization failed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close()
            return None

    async def _parse_initial_request(
        self, websocket: WebSocket
    ) -> tuple[bool, str | None, str | None, str | None, str | None, bool] | None:
        """Parse initial WebSocket request and return (is_resume, conversation_id, message, reasoning_effort, checkpoint_id, enable_checkpointing)."""
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=15)
        except TimeoutError:
            await websocket.send_json(
                {
                    "type": StreamEventType.ERROR.value,
                    "error": "WebSocket handshake timed out",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
            return None

        msg_type = data.get("type")
        is_resume = msg_type == "workflow.resume"

        conversation_id: str | None
        message: str | None
        reasoning_effort: str | None
        effective_checkpoint_id: str | None
        enable_checkpointing: bool

        if is_resume:
            resume_req = WorkflowResumeRequest(**data)
            conversation_id = resume_req.conversation_id
            message = None
            reasoning_effort = resume_req.reasoning_effort
            effective_checkpoint_id = resume_req.checkpoint_id
            enable_checkpointing = False
            logger.info(
                "WebSocket resume request received: conversation_id=%s, checkpoint_id=%s",
                conversation_id,
                str(effective_checkpoint_id)[:64],
            )
        else:
            request = ChatRequest(**data)
            conversation_id = request.conversation_id
            message = request.message
            reasoning_effort = request.reasoning_effort
            enable_checkpointing = bool(request.enable_checkpointing)

            raw_checkpoint_id = request.checkpoint_id
            if raw_checkpoint_id is not None:
                enable_checkpointing = True
                logger.warning(
                    "Received checkpoint_id along with a message; ignoring checkpoint_id for new run "
                    "(client_checkpoint_id=%s). Use enable_checkpointing for new runs or workflow.resume to resume.",
                    raw_checkpoint_id,
                )

            effective_checkpoint_id = None

            msg_preview = message[:50] if len(message) > 50 else message
            sanitized_preview = re.sub(r"[\x00-\x1F\x7F\u2028\u2029]", "", msg_preview)
            logger.info(
                "WebSocket chat request received: message_preview=%s, reasoning_effort=%s, conversation_id=%s, enable_checkpointing=%s",
                sanitized_preview,
                reasoning_effort,
                conversation_id,
                enable_checkpointing,
            )

        return (
            is_resume,
            conversation_id,
            message,
            reasoning_effort,
            effective_checkpoint_id,
            enable_checkpointing,
        )

    def _create_checkpoint_storage(
        self, enable_checkpointing: bool, is_resume: bool
    ) -> Any | None:
        """Create checkpoint storage if needed."""
        if not (enable_checkpointing or is_resume):
            return None

        try:
            from agent_framework._workflows import (
                FileCheckpointStorage,
                InMemoryCheckpointStorage,
            )

            checkpoint_dir = ".var/checkpoints"
            try:
                from pathlib import Path

                Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            except Exception:
                checkpoint_dir = ""

            if checkpoint_dir:
                return FileCheckpointStorage(checkpoint_dir)
            else:
                return InMemoryCheckpointStorage()
        except Exception:
            return None

    async def _setup_conversation_context(
        self,
        conversation_id: str | None,
        message: str | None,
        conversation_manager: Any,
        is_resume: bool,
        enable_checkpointing: bool,
    ) -> tuple[list[Any], Any | None, Any | None]:
        """Setup conversation history, thread, and checkpoint storage."""
        conversation_history: list[Any] = []
        if conversation_id:
            existing = conversation_manager.get_conversation(conversation_id)
            if existing is not None and getattr(existing, "messages", None):
                conversation_history = list(existing.messages)

        if (
            message
            and conversation_history
            and _message_role_value(getattr(conversation_history[-1], "role", ""))
            == MessageRole.USER.value
            and str(getattr(conversation_history[-1], "content", "")).strip() == message.strip()
        ):
            conversation_history = conversation_history[:-1]

        checkpoint_storage = self._create_checkpoint_storage(enable_checkpointing, is_resume)

        conversation_thread = await _get_or_create_thread(conversation_id)
        _prefer_service_thread_mode(conversation_thread)

        if conversation_history and not _thread_has_any_messages(conversation_thread):
            await _hydrate_thread_from_conversation(conversation_thread, conversation_history)

        if not is_resume and conversation_id and message:
            conversation_manager.add_message(
                conversation_id,
                MessageRole.USER,
                message,
                author="User",
            )

        return conversation_history, conversation_thread, checkpoint_storage

    async def _create_session(
        self,
        websocket: WebSocket,
        session_manager: Any,
        message: str | None,
        effective_checkpoint_id: str | None,
        reasoning_effort: str | None,
    ) -> WorkflowSession | None:
        """Create workflow session."""
        try:
            session = await session_manager.create_session(
                task=message or f"[resume:{effective_checkpoint_id}]",
                reasoning_effort=reasoning_effort,
            )
            return session
        except HTTPException as exc:
            await self._send_error_and_close(websocket, exc.detail)
            return None

    async def _send_connected_event(
        self,
        websocket: WebSocket,
        session: WorkflowSession,
        conversation_id: str | None,
        effective_checkpoint_id: str | None,
        is_resume: bool,
        checkpoint_storage: Any | None,
    ) -> None:
        """Send connected event to client."""
        connected_type = StreamEventType.CONNECTED
        connected_category, connected_ui_hint = classify_event(connected_type)
        connected_event = StreamEvent(
            type=connected_type,
            message="Connected",
            data={
                "conversation_id": conversation_id,
                "checkpoint_id": effective_checkpoint_id,
                "is_resume": is_resume,
                "checkpointing_enabled": bool(checkpoint_storage is not None),
            },
            category=connected_category,
            ui_hint=connected_ui_hint,
            workflow_id=session.workflow_id,
        )
        connected_event.log_line = _log_stream_event(connected_event, session.workflow_id)
        await websocket.send_json(connected_event.to_sse_dict())

    async def _heartbeat_loop(
        self, websocket: WebSocket, session: WorkflowSession, last_event_ts_holder: list[datetime]
    ) -> None:
        """Send periodic heartbeats to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(5)
                heartbeat_event = StreamEvent(
                    type=StreamEventType.HEARTBEAT,
                    message="heartbeat",
                    workflow_id=session.workflow_id,
                    timestamp=datetime.now(),
                )
                await websocket.send_json(heartbeat_event.to_sse_dict())
                last_event_ts_holder[0] = datetime.now()
        except Exception:
            return

    async def _listen_for_cancel(
        self,
        websocket: WebSocket,
        workflow: Any,
        session: WorkflowSession,
        cancel_event: asyncio.Event,
    ) -> None:
        """Listen for cancel requests and workflow responses from client."""
        try:
            while not cancel_event.is_set():
                try:
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.25)
                    msg_type = msg.get("type")
                    if msg_type == "cancel":
                        logger.info("Cancel requested for workflow: %s", session.workflow_id)
                        cancel_event.set()
                        break
                    if msg_type in ("workflow.response", "workflow_response", "response"):
                        request_id = msg.get("request_id")
                        response_payload = msg.get("response")
                        if not request_id:
                            logger.warning(
                                "Received workflow response without request_id (workflow_id=%s)",
                                session.workflow_id,
                            )
                            continue

                        try:
                            await workflow.send_workflow_responses(
                                {str(request_id): response_payload}
                            )
                            logger.info(
                                "Forwarded workflow response (workflow_id=%s, request_id=%s)",
                                session.workflow_id,
                                request_id,
                            )
                        except Exception as exc:
                            logger.error(
                                "Failed to forward workflow response (workflow_id=%s, request_id=%s): %s",
                                session.workflow_id,
                                request_id,
                                exc,
                                exc_info=True,
                            )
                except TimeoutError:
                    continue
        except WebSocketDisconnect:
            cancel_event.set()
        except Exception:
            cancel_event.set()

    async def _check_timeouts(
        self,
        websocket: WebSocket,
        session: WorkflowSession,
        cancel_event: asyncio.Event,
        last_event_ts: datetime,
        stream_start_ts: datetime,
        max_runtime_seconds: int = 300,
    ) -> bool:
        """Check for idle and max runtime timeouts. Returns True if timeout occurred."""
        if (datetime.now() - last_event_ts).total_seconds() > 120:
            timeout_type = StreamEventType.ERROR
            timeout_category, timeout_ui_hint = classify_event(timeout_type)
            timeout_event = StreamEvent(
                type=timeout_type,
                error="Stream idle timeout",
                category=timeout_category,
                ui_hint=timeout_ui_hint,
                workflow_id=session.workflow_id,
            )
            await websocket.send_json(timeout_event.to_sse_dict())
            cancel_event.set()
            return True

        if (datetime.now() - stream_start_ts).total_seconds() > max_runtime_seconds:
            timeout_type = StreamEventType.ERROR
            timeout_category, timeout_ui_hint = classify_event(timeout_type)
            timeout_event = StreamEvent(
                type=timeout_type,
                error="Stream max runtime exceeded",
                category=timeout_category,
                ui_hint=timeout_ui_hint,
                workflow_id=session.workflow_id,
            )
            await websocket.send_json(timeout_event.to_sse_dict())
            cancel_event.set()
            return True

        return False

    async def _handle_cancellation(
        self, websocket: WebSocket, session: WorkflowSession
    ) -> None:
        """Send cancellation and done events."""
        cancelled_type = StreamEventType.CANCELLED
        cancelled_category, cancelled_ui_hint = classify_event(cancelled_type)
        cancelled_event = StreamEvent(
            type=cancelled_type,
            message="Streaming cancelled by client",
            category=cancelled_category,
            ui_hint=cancelled_ui_hint,
            workflow_id=session.workflow_id,
        )
        await websocket.send_json(cancelled_event.to_sse_dict())
        
        done_type = StreamEventType.DONE
        done_category, done_ui_hint = classify_event(done_type)
        done_event = StreamEvent(
            type=done_type,
            category=done_category,
            ui_hint=done_ui_hint,
            workflow_id=session.workflow_id,
        )
        await websocket.send_json(done_event.to_sse_dict())

    def _accumulate_event_data(
        self,
        event_data: dict[str, Any],
        response_text: str,
        response_delta_text: str,
        last_agent_text: str,
        last_author: str | None,
        last_agent_id: str | None,
        response_completed_emitted: bool,
        saw_done: bool,
    ) -> tuple[str, str, str, str | None, str | None, bool, bool]:
        """Accumulate response data from event. Returns updated state."""
        event_type = event_data.get("type")

        author = event_data.get("author") or event_data.get("agent_id")
        if author:
            last_author = event_data.get("author") or last_author or author
            last_agent_id = event_data.get("agent_id") or last_agent_id

        if event_type == StreamEventType.RESPONSE_DELTA.value:
            response_delta_text += event_data.get("delta", "")
            response_text = response_delta_text
        elif event_type == StreamEventType.RESPONSE_COMPLETED.value:
            completed_msg = event_data.get("message", "")
            if completed_msg:
                response_text = completed_msg
            last_author = event_data.get("author") or last_author
            response_completed_emitted = True
        elif event_type in (
            StreamEventType.AGENT_OUTPUT.value,
            StreamEventType.AGENT_MESSAGE.value,
        ):
            agent_msg = event_data.get("message", "")
            if agent_msg:
                last_agent_text = agent_msg

        if event_type == StreamEventType.DONE.value:
            saw_done = True

        return (
            response_text,
            response_delta_text,
            last_agent_text,
            last_author,
            last_agent_id,
            response_completed_emitted,
            saw_done,
        )

    async def _process_event_stream(
        self,
        websocket: WebSocket,
        workflow: Any,
        session: WorkflowSession,
        session_manager: Any,
        message: str | None,
        reasoning_effort: str | None,
        cancel_event: asyncio.Event,
        conversation_thread: Any | None,
        conversation_history: list[Any],
        effective_checkpoint_id: str | None,
        checkpoint_storage: Any | None,
        last_event_ts_holder: list[datetime],
        stream_start_ts: datetime,
    ) -> tuple[str, str, str | None, str | None, bool, bool]:
        """Process event stream and return accumulated response data."""
        log_reasoning = False
        if hasattr(workflow, "config") and workflow.config:
            config = workflow.config
            logging_config = getattr(config, "logging", None)
            if logging_config and hasattr(logging_config, "log_reasoning"):
                log_reasoning = bool(logging_config.log_reasoning)

        response_text = ""
        response_delta_text = ""
        last_agent_text = ""
        last_author: str | None = None
        last_agent_id: str | None = None
        saw_done = False
        response_completed_emitted = False

        try:
            async for event_data in _event_generator(
                workflow,
                session,
                session_manager,
                task=message,
                log_reasoning=log_reasoning,
                reasoning_effort=reasoning_effort,
                cancel_event=cancel_event,
                thread=conversation_thread,
                conversation_history=conversation_history,
                checkpoint_id=effective_checkpoint_id,
                checkpoint_storage=checkpoint_storage,
            ):
                # Check timeouts
                if await self._check_timeouts(
                    websocket,
                    session,
                    cancel_event,
                    last_event_ts_holder[0],
                    stream_start_ts,
                ):
                    break

                # Handle cancellation
                if cancel_event.is_set():
                    await self._handle_cancellation(websocket, session)
                    break

                # Accumulate event data
                (
                    response_text,
                    response_delta_text,
                    last_agent_text,
                    last_author,
                    last_agent_id,
                    response_completed_emitted,
                    saw_done,
                ) = self._accumulate_event_data(
                    event_data,
                    response_text,
                    response_delta_text,
                    last_agent_text,
                    last_author,
                    last_agent_id,
                    response_completed_emitted,
                    saw_done,
                )

                # Send event to client
                await websocket.send_json(event_data)
                last_event_ts_holder[0] = datetime.now()

                # Break on DONE
                if event_data.get("type") == StreamEventType.DONE.value:
                    break

        except Exception:
            raise

        return (
            response_text,
            last_agent_text,
            last_author,
            last_agent_id,
            saw_done,
            response_completed_emitted,
        )

    async def _finalize_response(
        self,
        websocket: WebSocket,
        session: WorkflowSession,
        response_text: str,
        last_agent_text: str,
        last_author: str | None,
        last_agent_id: str | None,
        saw_done: bool,
        response_completed_emitted: bool,
    ) -> str:
        """Send final response events if needed and return final text."""
        final_text = (
            response_text.strip()
            or last_agent_text.strip()
            or "Sorry, I couldn't produce a final answer this time."
        )

        if not response_completed_emitted:
            completed_type = StreamEventType.RESPONSE_COMPLETED
            comp_category, comp_ui = classify_event(completed_type)
            completed_event = StreamEvent(
                type=completed_type,
                message=final_text,
                author=last_author,
                agent_id=last_agent_id,
                data={"quality_pending": True},
                category=comp_category,
                ui_hint=comp_ui,
                workflow_id=session.workflow_id,
            )
            completed_event.log_line = _log_stream_event(completed_event, session.workflow_id)
            await websocket.send_json(completed_event.to_sse_dict())

        if not saw_done:
            done_type = StreamEventType.DONE
            done_category, done_ui_hint = classify_event(done_type)
            done_event = StreamEvent(
                type=done_type,
                category=done_category,
                ui_hint=done_ui_hint,
                workflow_id=session.workflow_id,
            )
            await websocket.send_json(done_event.to_sse_dict())

        return final_text

    async def _persist_and_evaluate(
        self,
        workflow: Any,
        session: WorkflowSession,
        conversation_id: str | None,
        conversation_manager: Any,
        message: str | None,
        final_text: str,
        last_author: str | None,
        last_agent_id: str | None,
    ) -> None:
        """Persist assistant message and schedule quality evaluation."""
        assistant_message = None
        if conversation_id and final_text:
            assistant_message = conversation_manager.add_message(
                conversation_id,
                MessageRole.ASSISTANT,
                final_text,
                author=last_author,
                agent_id=last_agent_id,
                workflow_id=session.workflow_id,
                quality_pending=True,
            )

        if (
            message
            and final_text
            and hasattr(workflow, "history_manager")
            and workflow.history_manager is not None
        ):
            schedule_quality_evaluation(
                workflow_id=session.workflow_id,
                task=message,
                answer=final_text,
                history_manager=workflow.history_manager,
                conversation_manager=conversation_manager,
                conversation_id=conversation_id,
                message_id=getattr(assistant_message, "id", None),
            )

    async def handle(self, websocket: WebSocket) -> None:
        """Handle a WebSocket chat session end-to-end (simplified orchestration)."""
        # Setup phase: validate, accept, and initialize
        if not _validate_websocket_origin(websocket):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        managers = await self._initialize_managers(websocket)
        if managers is None:
            return
        session_manager, conversation_manager = managers

        workflow = await self._initialize_workflow(websocket)
        if workflow is None:
            return

        request_data = await self._parse_initial_request(websocket)
        if request_data is None:
            return
        (
            is_resume,
            conversation_id,
            message,
            reasoning_effort,
            effective_checkpoint_id,
            enable_checkpointing,
        ) = request_data

        conversation_history, conversation_thread, checkpoint_storage = (
            await self._setup_conversation_context(
                conversation_id,
                message,
                conversation_manager,
                is_resume,
                enable_checkpointing,
            )
        )

        session = await self._create_session(
            websocket, session_manager, message, effective_checkpoint_id, reasoning_effort
        )
        if session is None:
            return

        await self._send_connected_event(
            websocket,
            session,
            conversation_id,
            effective_checkpoint_id,
            is_resume,
            checkpoint_storage,
        )

        # Event streaming phase: main loop with heartbeat and cancel listeners
        cancel_event = asyncio.Event()
        last_event_ts_holder = [datetime.now()]
        stream_start_ts = datetime.now()

        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(websocket, session, last_event_ts_holder)
        )
        cancel_task = asyncio.create_task(
            self._listen_for_cancel(websocket, workflow, session, cancel_event)
        )

        try:
            (
                response_text,
                last_agent_text,
                last_author,
                last_agent_id,
                saw_done,
                response_completed_emitted,
            ) = await self._process_event_stream(
                websocket,
                workflow,
                session,
                session_manager,
                message,
                reasoning_effort,
                cancel_event,
                conversation_thread,
                conversation_history,
                effective_checkpoint_id,
                checkpoint_storage,
                last_event_ts_holder,
                stream_start_ts,
            )

            # Cleanup phase: finalize response and persist
            final_text = await self._finalize_response(
                websocket,
                session,
                response_text,
                last_agent_text,
                last_author,
                last_agent_id,
                saw_done,
                response_completed_emitted,
            )

            await self._persist_and_evaluate(
                workflow,
                session,
                conversation_id,
                conversation_manager,
                message,
                final_text,
                last_author,
                last_agent_id,
            )

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as exc:
            logger.error("WebSocket error: %s", exc, exc_info=True)
            with contextlib.suppress(Exception):
                await self._send_error_and_close(
                    websocket, str(exc), session.workflow_id if session else None
                )
        finally:
            # Task cleanup
            cancel_task.cancel()
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(cancel_task, heartbeat_task)

            # Session status update
            if session and cancel_event.is_set():
                await session_manager.update_status(
                    session.workflow_id,
                    WorkflowStatus.CANCELLED,
                    completed_at=datetime.now(),
                )

            # Close WebSocket
            with contextlib.suppress(Exception):
                await websocket.close()


__all__ = ["ChatWebSocketService"]
