"""Application lifecycle management for the AgenticFleet FastAPI app."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentic_fleet.core.conversation_store import ConversationStore
from agentic_fleet.core.settings import get_settings
from agentic_fleet.dspy_modules.compiled_registry import load_required_compiled_modules
from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
from agentic_fleet.services.optimization_jobs import OptimizationJobManager
from agentic_fleet.utils.cfg import load_config
from agentic_fleet.utils.tracing import initialize_tracing
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

    # Phase 1: Load and validate compiled DSPy artifacts with fail-fast enforcement
    try:
        # Load workflow config to get DSPy settings
        config = load_config(validate=False)
        # Store YAML config in app.state for reuse by WebSocket sessions
        app.state.yaml_config = config

        # Initialize tracing early using YAML config so `tracing.enabled: true`
        # works without requiring environment flags.
        initialize_tracing(config)
        dspy_config = config.get("dspy", {})
        require_compiled = dspy_config.get("require_compiled", False)

        logger.info("Loading compiled DSPy artifacts (require_compiled=%s)...", require_compiled)

        # Load all required compiled modules using the registry
        artifact_registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=require_compiled,
        )

        # Attach registry to app state for use by workflow and services
        app.state.dspy_artifacts = artifact_registry

        # Log loaded artifacts
        from agentic_fleet.dspy_modules.compiled_registry import validate_artifact_registry

        loaded_status = validate_artifact_registry(artifact_registry)
        logger.info("DSPy artifacts loaded: %s", loaded_status)

        # Initialize decision modules from preloaded artifacts
        from agentic_fleet.dspy_modules.decisions import (
            get_quality_module,
            get_routing_module,
            get_tool_planning_module,
        )

        # Set up decision modules using preloaded artifacts
        quality_module = get_quality_module(artifact_registry.quality)
        routing_module = get_routing_module(artifact_registry.routing)
        tool_planning_module = get_tool_planning_module(artifact_registry.tool_planning)

        # Attach decision modules to app state for easy access
        app.state.dspy_quality_module = quality_module
        app.state.dspy_routing_module = routing_module
        app.state.dspy_tool_planning_module = tool_planning_module

        logger.info("DSPy decision modules initialized successfully")

        # Phase 2: Create workflow with preloaded decision modules
        workflow = await create_supervisor_workflow(
            dspy_routing_module=routing_module,
            dspy_quality_module=quality_module,
            dspy_tool_planning_module=tool_planning_module,
        )
        app.state.workflow = workflow
        logger.info("Workflow initialized with Phase 2 decision modules")

    except RuntimeError as e:
        # Fail-fast: Required compiled artifacts missing
        logger.error("Failed to load required compiled DSPy artifacts: %s", e)
        raise
    except Exception as e:
        # Unexpected error during artifact loading
        logger.error("Unexpected error loading DSPy artifacts: %s", e, exc_info=True)
        # In production with require_compiled=True, we should fail-fast
        config = load_config(validate=False)
        dspy_config = config.get("dspy", {})
        if dspy_config.get("require_compiled", False):
            raise RuntimeError(
                f"Failed to initialize DSPy artifacts (require_compiled=True): {e}"
            ) from e
        # Otherwise, log warning and continue with degraded functionality
        logger.warning(
            "Continuing with degraded DSPy functionality due to artifact loading error: %s", e
        )

        # Ensure YAML config is stored even in fallback path
        if not hasattr(app.state, "yaml_config"):
            app.state.yaml_config = config

        # Create workflow without preloaded decision modules (fallback)
        workflow = await create_supervisor_workflow()
        app.state.workflow = workflow
        logger.info("Workflow initialized without Phase 2 decision modules (fallback mode)")

    # Initialize managers with settings-aware configuration and attach to app state
    app.state.session_manager = WorkflowSessionManager(
        max_concurrent=settings.max_concurrent_workflows
    )
    app.state.conversation_manager = ConversationManager(
        ConversationStore(settings.conversations_path)
    )
    app.state.optimization_jobs = OptimizationJobManager()

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
    app.state.optimization_jobs = None
    app.state.dspy_artifacts = None
    app.state.dspy_quality_module = None
    app.state.dspy_routing_module = None
    app.state.dspy_tool_planning_module = None
    app.state.yaml_config = None
