"""SSE chat streaming service.

This module provides HTTP SSE (Server-Sent Events) streaming for chat responses.
It reuses the core streaming logic from chat_websocket.py but exposes it via
standard HTTP streaming instead of WebSocket.

Benefits of SSE over WebSocket:
- Built-in auto-reconnect in browsers
- Works through all proxies and CDNs
- Simpler error handling (standard HTTP errors)
- No persistent connection management needed
- Native keep-alive support
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agentic_fleet.api.events.mapping import classify_event, map_workflow_event
from agentic_fleet.models import (
    MessageRole,
    StreamEvent,
    StreamEventType,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.services.background_evaluation import schedule_quality_evaluation
from agentic_fleet.services.chat_websocket import (
    _get_or_create_thread,
    _hydrate_thread_from_conversation,
    _log_stream_event,
    _message_role_value,
    _prefer_service_thread_mode,
    _thread_has_any_messages,
)
from agentic_fleet.utils.logger import setup_logger

if TYPE_CHECKING:
    pass

logger = setup_logger(__name__)


class ChatSSEService:
    """Service for SSE-based chat streaming."""

    def __init__(
        self,
        workflow: Any,
        session_manager: Any,
        conversation_manager: Any,
    ) -> None:
        """Initialize SSE service.

        Args:
            workflow: SupervisorWorkflow instance
            session_manager: WorkflowSessionManager for session tracking
            conversation_manager: ConversationManager for message persistence
        """
        self.workflow = workflow
        self.session_manager = session_manager
        self.conversation_manager = conversation_manager
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._pending_responses: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    async def stream_chat(
        self,
        conversation_id: str,
        message: str,
        *,
        reasoning_effort: str | None = None,
        enable_checkpointing: bool = False,
    ) -> AsyncIterator[str]:
        """Stream chat response as SSE events.

        Args:
            conversation_id: Conversation identifier
            message: User message
            reasoning_effort: Optional reasoning effort level
            enable_checkpointing: Whether to enable checkpointing

        Yields:
            SSE-formatted event strings (data: {...}\\n\\n)
        """
        session: WorkflowSession | None = None
        cancel_event = asyncio.Event()

        try:
            # Load conversation history
            conversation_history: list[Any] = []
            existing = self.conversation_manager.get_conversation(conversation_id)
            if existing is not None and getattr(existing, "messages", None):
                conversation_history = list(existing.messages)

            # Avoid duplicate if last message matches
            if (
                conversation_history
                and _message_role_value(getattr(conversation_history[-1], "role", ""))
                == MessageRole.USER.value
                and str(getattr(conversation_history[-1], "content", "")).strip() == message.strip()
            ):
                conversation_history = conversation_history[:-1]

            # Setup checkpointing
            checkpoint_storage: Any | None = None
            if enable_checkpointing:
                try:
                    from pathlib import Path

                    from agent_framework._workflows import FileCheckpointStorage

                    checkpoint_dir = ".var/checkpoints"
                    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
                    checkpoint_storage = FileCheckpointStorage(checkpoint_dir)
                except Exception:
                    checkpoint_storage = None

            # Get or create conversation thread
            conversation_thread = await _get_or_create_thread(conversation_id)
            _prefer_service_thread_mode(conversation_thread)

            # Hydrate thread if needed
            if conversation_history and not _thread_has_any_messages(conversation_thread):
                await _hydrate_thread_from_conversation(conversation_thread, conversation_history)

            # Persist user message
            self.conversation_manager.add_message(
                conversation_id,
                MessageRole.USER,
                message,
                author="User",
            )

            # Create session
            session = await self.session_manager.create_session(
                task=message,
                reasoning_effort=reasoning_effort,
            )
            # Type narrowing: session is guaranteed non-None after create_session
            assert session is not None, "Session creation failed"
            workflow_id = session.workflow_id

            # Store cancel event for this workflow
            self._cancel_events[workflow_id] = cancel_event
            self._pending_responses[workflow_id] = asyncio.Queue()

            # Emit connected event
            connected_type = StreamEventType.CONNECTED
            connected_category, connected_ui_hint = classify_event(connected_type)
            connected_event = StreamEvent(
                type=connected_type,
                message="Connected",
                data={
                    "conversation_id": conversation_id,
                    "checkpointing_enabled": checkpoint_storage is not None,
                },
                category=connected_category,
                ui_hint=connected_ui_hint,
                workflow_id=workflow_id,
            )
            yield f"data: {json.dumps(connected_event.to_sse_dict())}\n\n"

            # Stream workflow events
            accumulated_reasoning = ""
            response_text = ""
            last_agent_text = ""
            last_author: str | None = None
            last_agent_id: str | None = None
            response_completed_emitted = False

            await self.session_manager.update_status(
                workflow_id,
                WorkflowStatus.RUNNING,
                started_at=datetime.now(),
            )

            stream_kwargs: dict[str, Any] = {
                "reasoning_effort": reasoning_effort,
                "thread": conversation_thread,
                "conversation_history": conversation_history,
                "workflow_id": workflow_id,
                "schedule_quality_eval": False,
            }

            if checkpoint_storage is not None:
                stream_kwargs["checkpoint_storage"] = checkpoint_storage

            async for event in self.workflow.run_stream(message, **stream_kwargs):
                if cancel_event.is_set():
                    logger.info("SSE stream cancelled: workflow_id=%s", workflow_id)
                    break

                stream_event, accumulated_reasoning = map_workflow_event(
                    event, accumulated_reasoning
                )
                if stream_event is None:
                    continue

                events_to_emit = stream_event if isinstance(stream_event, list) else [stream_event]
                for se in events_to_emit:
                    se.workflow_id = workflow_id
                    log_line = _log_stream_event(se, workflow_id)
                    if log_line:
                        se.log_line = log_line

                    event_data = se.to_sse_dict()
                    event_type = event_data.get("type")

                    # Track response content
                    author = event_data.get("author") or event_data.get("agent_id")
                    if author:
                        last_author = event_data.get("author") or last_author or author
                        last_agent_id = event_data.get("agent_id") or last_agent_id

                    if event_type == StreamEventType.RESPONSE_DELTA.value:
                        response_text += event_data.get("delta", "")
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

                    yield f"data: {json.dumps(event_data)}\n\n"

            # Emit final response if not already emitted
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
                    workflow_id=workflow_id,
                )
                completed_event.log_line = _log_stream_event(completed_event, workflow_id)
                yield f"data: {json.dumps(completed_event.to_sse_dict())}\n\n"

            # Persist assistant message
            assistant_message = None
            if final_text:
                assistant_message = self.conversation_manager.add_message(
                    conversation_id,
                    MessageRole.ASSISTANT,
                    final_text,
                    author=last_author,
                    agent_id=last_agent_id,
                    workflow_id=workflow_id,
                    quality_pending=True,
                )

            # Schedule background quality evaluation
            if (
                final_text
                and hasattr(self.workflow, "history_manager")
                and self.workflow.history_manager is not None
            ):
                schedule_quality_evaluation(
                    workflow_id=workflow_id,
                    task=message,
                    answer=final_text,
                    history_manager=self.workflow.history_manager,
                    conversation_manager=self.conversation_manager,
                    conversation_id=conversation_id,
                    message_id=getattr(assistant_message, "id", None),
                )

            # Update session status
            final_status = (
                WorkflowStatus.CANCELLED if cancel_event.is_set() else WorkflowStatus.COMPLETED
            )
            await self.session_manager.update_status(
                workflow_id,
                final_status,
                completed_at=datetime.now(),
            )

            # Emit done event
            done_type = StreamEventType.DONE
            done_category, done_ui_hint = classify_event(done_type)
            done_event = StreamEvent(
                type=done_type,
                category=done_category,
                ui_hint=done_ui_hint,
                workflow_id=workflow_id,
            )
            yield f"data: {json.dumps(done_event.to_sse_dict())}\n\n"

        except Exception as exc:
            logger.error("SSE stream error: %s", exc, exc_info=True)

            error_type = StreamEventType.ERROR
            error_category, error_ui_hint = classify_event(error_type)
            error_event = StreamEvent(
                type=error_type,
                error=str(exc),
                category=error_category,
                ui_hint=error_ui_hint,
                workflow_id=session.workflow_id if session else None,
            )
            yield f"data: {json.dumps(error_event.to_sse_dict())}\n\n"

            if session:
                await self.session_manager.update_status(
                    session.workflow_id,
                    WorkflowStatus.FAILED,
                    completed_at=datetime.now(),
                )

        finally:
            # Cleanup
            if session:
                self._cancel_events.pop(session.workflow_id, None)
                self._pending_responses.pop(session.workflow_id, None)

    async def cancel_stream(self, workflow_id: str) -> bool:
        """Cancel an active stream.

        Args:
            workflow_id: The workflow ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        cancel_event = self._cancel_events.get(workflow_id)
        if cancel_event:
            cancel_event.set()
            logger.info("Cancelled SSE stream: workflow_id=%s", workflow_id)
            return True
        return False

    async def submit_response(
        self,
        workflow_id: str,
        request_id: str,
        response: Any,
    ) -> bool:
        """Submit a human-in-the-loop response.

        Args:
            workflow_id: The workflow ID
            request_id: The request ID from the HITL event
            response: The response payload

        Returns:
            True if submitted, False if workflow not found
        """
        try:
            await self.workflow.send_workflow_responses({str(request_id): response})
            logger.info(
                "Submitted HITL response: workflow_id=%s, request_id=%s",
                workflow_id,
                request_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "Failed to submit HITL response: workflow_id=%s, request_id=%s, error=%s",
                workflow_id,
                request_id,
                exc,
            )
            return False


__all__ = ["ChatSSEService"]
