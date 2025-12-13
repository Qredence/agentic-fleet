"""Application lifecycle management for the AgenticFleet FastAPI app."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentic_fleet.core.conversation_store import ConversationStore
from agentic_fleet.core.settings import get_settings
from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

logger = logging.getLogger(__name__)


def _configure_litellm_retry() -> None:
    """Configure LiteLLM global retry settings.

    Retry is disabled by default to fail fast on rate limits.
    """
    try:
        import litellm

        # Disable retry - fail fast on rate limits
        litellm.num_retries = 0

        logger.info("LiteLLM configured with num_retries=%d (disabled)", litellm.num_retries)
    except ImportError:
        logger.debug("LiteLLM not installed")
    except Exception as e:
        logger.debug("LiteLLM config: %s", e)


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

    # Configure LiteLLM retry settings before workflow initialization
    _configure_litellm_retry()

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

    # Initialize managers with settings-aware configuration and attach to app state
    app.state.session_manager = WorkflowSessionManager(
        max_concurrent=settings.max_concurrent_workflows
    )
    app.state.conversation_manager = ConversationManager(
        ConversationStore(settings.conversations_path)
    )

    logger.info(
        "AgenticFleet API ready: max_concurrent_workflows=%s, conversations_path=%s",
        settings.max_concurrent_workflows,
        settings.conversations_path,
    )
    yield

    # Cleanup
    logger.info("Shutting down AgenticFleet API...")
    app.state.session_manager = None
    app.state.conversation_manager = None
