"""Async compilation utilities for DSPy modules.

This module provides background compilation capabilities to avoid
blocking workflow initialization.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .compiler import compile_supervisor
from .progress import NullProgressCallback, ProgressCallback

logger = logging.getLogger(__name__)


class AsyncCompiler:
    """Manages async compilation of DSPy modules."""

    def __init__(self):
        """Initialize async compiler."""
        self._compilation_task: asyncio.Future[Any] | None = None
        self._compiled_module: Any | None = None
        self._compilation_error: Exception | None = None
        self._store_result_task: asyncio.Task[Any] | None = None

    async def compile_in_background(
        self,
        module: Any,
        examples_path: str = "data/supervisor_examples.json",
        use_cache: bool = True,
        optimizer: str = "bootstrap",
        gepa_options: dict[str, Any] | None = None,
        dspy_model: str | None = None,
        agent_config: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Start compilation in background.

        Args:
            module: DSPy module to compile
            examples_path: Path to training examples
            use_cache: Whether to use cache
            optimizer: Optimization strategy
            gepa_options: GEPA optimizer options
            dspy_model: DSPy model identifier
            agent_config: Agent configuration
            progress_callback: Progress callback
        """
        if self._compilation_task and not self._compilation_task.done():
            logger.warning("Compilation already in progress")
            return

        self._compiled_module = None
        self._compilation_error = None

        def _compile() -> Any:
            """Run compilation in thread pool."""
            try:
                return compile_supervisor(
                    module=module,
                    examples_path=examples_path,
                    use_cache=use_cache,
                    optimizer=optimizer,
                    gepa_options=gepa_options,
                    dspy_model=dspy_model,
                    agent_config=agent_config,
                    progress_callback=progress_callback or NullProgressCallback(),
                )
            except Exception as e:
                logger.error(f"Background compilation failed: {e}")
                raise

        loop = asyncio.get_event_loop()
        self._compilation_task = loop.run_in_executor(None, _compile)

        # Store result when done
        async def _store_result() -> None:
            try:
                if self._compilation_task is not None:
                    self._compiled_module = await self._compilation_task
                    logger.info("Background compilation completed successfully")
            except Exception as e:
                self._compilation_error = e
                logger.error(f"Background compilation error: {e}")

        self._store_result_task = asyncio.create_task(_store_result())

    async def wait_for_compilation(self, timeout: float | None = None) -> Any:
        """Wait for compilation to complete.

        Args:
            timeout: Maximum time to wait (None for no timeout)

        Returns:
            Compiled module

        Raises:
            TimeoutError: If compilation doesn't complete in time
            Exception: If compilation failed
        """
        if not self._compilation_task:
            raise RuntimeError("No compilation task started")

        try:
            if timeout:
                self._compiled_module = await asyncio.wait_for(
                    self._compilation_task, timeout=timeout
                )
            else:
                self._compiled_module = await self._compilation_task

            if self._compilation_error:
                raise self._compilation_error

            return self._compiled_module
        except TimeoutError as err:
            raise TimeoutError(f"Compilation did not complete within {timeout}s") from err

    def get_compiled_module(self) -> Any | None:
        """Get compiled module if available.

        Returns:
            Compiled module or None if not ready
        """
        return self._compiled_module

    def is_compiling(self) -> bool:
        """Check if compilation is in progress.

        Returns:
            True if compilation is active
        """
        return self._compilation_task is not None and not self._compilation_task.done()

    def is_ready(self) -> bool:
        """Check if compilation is complete and ready.

        Returns:
            True if compiled module is available
        """
        return self._compiled_module is not None and self._compilation_error is None
