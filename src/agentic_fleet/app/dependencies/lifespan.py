"""Application lifecycle management for AgenticFleet API.

Provides lifespan context manager for FastAPI application startup and shutdown.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentic_fleet.app.conversation_store import ConversationStore
from agentic_fleet.app.settings import get_settings
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

from .managers import ConversationManager, WorkflowSessionManager

logger = logging.getLogger(__name__)

# Global manager instances
_session_manager: WorkflowSessionManager | None = None
_conversation_manager: ConversationManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    Creates and initializes the SupervisorWorkflow on startup,
    and handles cleanup on shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup initialization is complete.
    """
    logger.info("Starting AgenticFleet API...")

    settings = get_settings()
    app.state.settings = settings

    workflow = await create_supervisor_workflow()
    app.state.workflow = workflow

    # Pre-warm the AnswerQualityModule cache (logs warning if not compiled)
    try:
        from agentic_fleet.dspy_modules.answer_quality import _get_answer_quality_module

        aq_module = _get_answer_quality_module()
        if aq_module is None:
            logger.warning(
                "AnswerQualityModule not compiled. Quality scoring will use heuristic fallback. "
                "Run `agentic-fleet gepa-optimize` to compile for better quality scoring."
            )
        else:
            logger.info("AnswerQualityModule loaded from cache")
    except Exception as e:
        logger.warning("Failed to pre-warm AnswerQualityModule: %s", e)

    # Initialize managers with settings-aware configuration
    global _session_manager, _conversation_manager
    _session_manager = WorkflowSessionManager(max_concurrent=settings.max_concurrent_workflows)
    _conversation_manager = ConversationManager(ConversationStore(settings.conversations_path))

    logger.info(
        "AgenticFleet API ready: max_concurrent_workflows=%s, conversations_path=%s",
        settings.max_concurrent_workflows,
        settings.conversations_path,
    )
    yield

    # Cleanup
    logger.info("Shutting down AgenticFleet API...")
    _session_manager = None
    _conversation_manager = None


def get_session_manager() -> WorkflowSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = WorkflowSessionManager()
    return _session_manager


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
