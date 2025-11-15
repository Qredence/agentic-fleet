"""DSPy supervisor compilation utilities.

Standalone compilation functions for DSPy supervisor.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..dspy_modules.supervisor import DSPySupervisor
from ..utils.compiler import compile_supervisor
from ..utils.progress import LoggingProgressCallback, NullProgressCallback
from .config import WorkflowConfig

logger = logging.getLogger(__name__)


class CompilationState:
    """State container for DSPy compilation."""

    def __init__(self) -> None:
        """Initialize compilation state."""
        self.compiled_supervisor: DSPySupervisor | None = None
        self.compilation_status: str = "pending"
        self.compilation_task: asyncio.Task[None] | None = None


async def compile_supervisor_async(
    supervisor: DSPySupervisor,
    config: WorkflowConfig,
    agents: dict[str, Any],
    progress_callback: Any | None = None,
    state: CompilationState | None = None,
) -> DSPySupervisor:
    """Compile DSPy supervisor asynchronously in background.

    Args:
        supervisor: DSPy supervisor to compile
        config: Workflow configuration
        agents: Dictionary of agents for config extraction
        progress_callback: Optional progress callback
        state: Optional compilation state container

    Returns:
        Compiled DSPy supervisor
    """
    state = state or CompilationState()

    if state.compilation_status in ("completed", "compiling"):
        if state.compiled_supervisor is not None:
            return state.compiled_supervisor
        return supervisor

    state.compilation_status = "compiling"
    logger.info("Starting DSPy compilation in background...")

    # Get progress callback if available
    # For background compilation running in executor thread, always use logging-based callback
    # to avoid conflicts with main Live context and Progress bar recursion issues
    if progress_callback:
        # Check if it's a RichProgressCallback by checking for the console attribute
        # Always use logging for background compilation to avoid Progress bar conflicts
        if hasattr(progress_callback, "console"):
            progress_callback = LoggingProgressCallback()
            logger.info("DSPy compilation running in background (progress logged)")
    else:
        progress_callback = NullProgressCallback()

    try:
        # Extract agent config for cache invalidation
        agent_config = {}
        if agents:
            for agent_name, agent in agents.items():
                agent_config[agent_name] = {
                    "description": getattr(agent, "description", ""),
                    "tools": [
                        tool.__class__.__name__
                        for tool in (getattr(agent.chat_options, "tools", []) or [])
                    ],
                }

        # Run compilation in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()

        def compile_sync():
            return compile_supervisor(
                supervisor,
                examples_path=config.examples_path,
                optimizer=config.dspy_optimizer,
                gepa_options=config.gepa_options,
                dspy_model=config.dspy_model,
                agent_config=agent_config,
                progress_callback=progress_callback,
            )

        compiled = await loop.run_in_executor(None, compile_sync)
        state.compiled_supervisor = compiled
        state.compilation_status = "completed"
        if progress_callback:
            progress_callback.on_complete("DSPy compilation completed")
        logger.info("✓ DSPy compilation completed in background")
        return compiled
    except Exception as e:
        state.compilation_status = "failed"
        if progress_callback:
            progress_callback.on_error("DSPy compilation failed", e)
        logger.error(f"DSPy compilation failed: {e}")
        # Fall back to uncompiled supervisor
        state.compiled_supervisor = supervisor
        return supervisor


def get_compiled_supervisor(
    supervisor: DSPySupervisor,
    state: CompilationState,
) -> DSPySupervisor:
    """Get compiled supervisor, triggering compilation if needed.

    Args:
        supervisor: Base DSPy supervisor
        state: Compilation state container

    Returns:
        Compiled DSPy supervisor (or uncompiled if compilation failed/skipped)
    """
    # If already compiled, return it
    if state.compiled_supervisor is not None:
        return state.compiled_supervisor

    # If compilation is in progress, wait for it
    if state.compilation_task and not state.compilation_task.done():
        logger.debug("Waiting for background compilation to complete...")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.warning("Compilation still in progress, using uncompiled supervisor")
                return supervisor
            else:
                loop.run_until_complete(state.compilation_task)
        except RuntimeError:
            logger.warning("No event loop available, using uncompiled supervisor")
            return supervisor

    # If compilation completed, use compiled version
    if state.compiled_supervisor is not None:
        return state.compiled_supervisor

    # If compilation failed or was skipped, use uncompiled
    if state.compilation_status in ("failed", "skipped"):
        return supervisor

    # If compilation hasn't started, trigger it synchronously
    if state.compilation_status == "pending":
        logger.info("Triggering synchronous DSPy compilation...")
        try:
            # This should not happen in normal flow, but handle it gracefully
            logger.warning("Synchronous compilation not supported in standalone mode")
            return supervisor
        except Exception as e:
            logger.error(f"Synchronous compilation failed: {e}")
            state.compilation_status = "failed"
            return supervisor

    # Fallback to uncompiled
    return supervisor
