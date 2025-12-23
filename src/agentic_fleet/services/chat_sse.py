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

from agentic_fleet.api.events.mapping import map_workflow_event
from agentic_fleet.dspy_modules.answer_quality import score_answer_with_dspy
from agentic_fleet.evaluation.background import schedule_quality_evaluation
from agentic_fleet.models import (
    MessageRole,
    StreamEventType,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.services.chat_helpers import (
    ResponseState,
    _get_or_create_thread,
    _hydrate_thread_from_conversation,
    _log_stream_event,
    _message_role_value,
    _prefer_service_thread_mode,
    _thread_has_any_messages,
    create_checkpoint_storage,
    create_stream_event,
)
from agentic_fleet.utils.infra.logging import setup_logger

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

    async def _setup_stream_context(
        self,
        conversation_id: str,
        message: str,
        enable_checkpointing: bool,
    ) -> tuple[list[Any], Any, Any]:
        """Setup streaming context with history, thread, and checkpointing.

        Returns:
            Tuple of (conversation_history, conversation_thread, checkpoint_storage)
        """
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
        checkpoint_storage = create_checkpoint_storage(enable_checkpointing, is_resume=False)

        # Get or create conversation thread
        conversation_thread = await _get_or_create_thread(conversation_id)
        _prefer_service_thread_mode(conversation_thread)

        # Hydrate thread if needed
        if conversation_history and not _thread_has_any_messages(conversation_thread):
            await _hydrate_thread_from_conversation(conversation_thread, conversation_history)

        return conversation_history, conversation_thread, checkpoint_storage

    async def _create_and_setup_session(
        self,
        message: str,
        reasoning_effort: str | None,
        cancel_event: asyncio.Event,
    ) -> WorkflowSession:
        """Create session and register cancellation tracking.

        Raises:
            RuntimeError: If session creation fails.
        """
        # Persist user message happens before this in stream_chat

        # Create session
        session = await self.session_manager.create_session(
            task=message,
            reasoning_effort=reasoning_effort,
        )

        if session is None:
            raise RuntimeError(
                f"Session creation failed for task={message[:50]}..., "
                f"reasoning_effort={reasoning_effort}"
            )

        # Store cancel event for this workflow
        workflow_id = session.workflow_id
        self._cancel_events[workflow_id] = cancel_event
        self._pending_responses[workflow_id] = asyncio.Queue()

        return session

    def _emit_sse_event(self, event: Any) -> str:
        """Convert StreamEvent to SSE format string."""
        return f"data: {json.dumps(event.to_sse_dict())}\n\n"

    async def _finalize_stream(
        self,
        workflow_id: str,
        conversation_id: str,
        message: str,
        response_state: ResponseState,
        cancel_event: asyncio.Event,
    ) -> None:
        """Finalize stream by persisting message, scheduling evaluation, and updating status."""
        final_text = response_state.get_final_text()

        # Persist assistant message
        assistant_message = None
        if final_text:
            assistant_message = self.conversation_manager.add_message(
                conversation_id,
                MessageRole.ASSISTANT,
                final_text,
                author=response_state.last_author,
                agent_id=response_state.last_agent_id,
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
            # Setup phase: load history, create thread, setup checkpointing
            (
                conversation_history,
                conversation_thread,
                checkpoint_storage,
            ) = await self._setup_stream_context(conversation_id, message, enable_checkpointing)

            # Persist user message
            self.conversation_manager.add_message(
                conversation_id,
                MessageRole.USER,
                message,
                author="User",
            )

            # Create session and setup tracking
            session = await self._create_and_setup_session(message, reasoning_effort, cancel_event)
            workflow_id = session.workflow_id

            # Emit connected event
            connected_event = create_stream_event(
                StreamEventType.CONNECTED,
                workflow_id=workflow_id,
                message="Connected",
                data={
                    "conversation_id": conversation_id,
                    "checkpointing_enabled": checkpoint_storage is not None,
                },
            )
            yield self._emit_sse_event(connected_event)

            # Streaming phase: process workflow events
            accumulated_reasoning = ""
            response_state = ResponseState()

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

            # Set conversation_id in Langfuse context for session tracking
            # (workflow_id is already set in stream_kwargs and will be used as trace_id)
            try:
                from agentic_fleet.utils.infra.langfuse import set_langfuse_context

                set_langfuse_context(session_id=conversation_id)
            except ImportError:
                pass  # Langfuse not available

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
                    response_state.update_from_event(event_data)
                    yield self._emit_sse_event(se)

            # Emit final response if not already emitted
            final_text = response_state.get_final_text()

            if not response_state.response_completed_emitted:
                # Calculate immediate quality score (heuristic or DSPy if available)
                # This provides instant feedback while background evaluation runs
                try:
                    immediate_metrics = score_answer_with_dspy(message, final_text)
                    immediate_score = max(
                        0.0, min(10.0, round(immediate_metrics.get("quality_score", 0.0) * 10.0, 1))
                    )
                    immediate_flag = immediate_metrics.get("quality_flag")
                except Exception as e:
                    logger.debug("Failed to calculate immediate quality score: %s", e)
                    immediate_score = None
                    immediate_flag = None

                completed_event = create_stream_event(
                    StreamEventType.RESPONSE_COMPLETED,
                    workflow_id=workflow_id,
                    message=final_text,
                    author=response_state.last_author,
                    agent_id=response_state.last_agent_id,
                    quality_score=immediate_score,
                    quality_flag=immediate_flag,
                    data={"quality_pending": True},  # Background evaluation will refine this
                )
                yield self._emit_sse_event(completed_event)

            # Finalization phase: persist message, schedule evaluation, update status
            await self._finalize_stream(
                workflow_id,
                conversation_id,
                message,
                response_state,
                cancel_event,
            )

            # Emit done event
            done_event = create_stream_event(
                StreamEventType.DONE,
                workflow_id=workflow_id,
            )
            yield self._emit_sse_event(done_event)

        except Exception as exc:
            logger.error("SSE stream error: %s", exc, exc_info=True)

            error_event = create_stream_event(
                StreamEventType.ERROR,
                workflow_id=session.workflow_id if session else None,
                error=str(exc),
            )
            yield self._emit_sse_event(error_event)

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
