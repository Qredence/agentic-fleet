"""
Progress reporting utilities for DSPy compilation and workflow execution.

Provides callback interfaces and implementations for reporting progress during
long-running operations like DSPy compilation and agent execution.
"""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for progress reporting callbacks."""

    def on_start(self, message: str) -> None:
        """Called when an operation starts."""
        ...

    def on_progress(
        self, message: str, current: int | None = None, total: int | None = None
    ) -> None:
        """Called to report progress during an operation."""
        ...

    def on_complete(self, message: str, duration: float | None = None) -> None:
        """Called when an operation completes."""
        ...

    def on_error(self, message: str, error: Exception | None = None) -> None:
        """Called when an operation encounters an error."""
        ...


class LoggingProgressCallback:
    """Simple logging-based progress callback implementation."""

    def __init__(self, log_level: int = logging.INFO):
        """Initialize with a logging level."""
        self.log_level = log_level
        self.start_time: float | None = None

    def on_start(self, message: str) -> None:
        """Log operation start."""
        self.start_time = time.perf_counter()
        logger.log(self.log_level, "▶ %s", message)

    def on_progress(
        self, message: str, current: int | None = None, total: int | None = None
    ) -> None:
        """Log progress update."""
        if current is not None and total is not None:
            percentage = (current / total * 100) if total > 0 else 0
            logger.log(
                self.log_level, "  → %s (%d/%d, %.1f%%)", message, current, total, percentage
            )
        else:
            logger.log(self.log_level, "  → %s", message)

    def on_complete(self, message: str, duration: float | None = None) -> None:
        """Log operation completion."""
        if duration is None and self.start_time is not None:
            duration = time.perf_counter() - self.start_time
        if duration is not None:
            logger.log(self.log_level, "✓ %s (took %.2fs)", message, duration)
        else:
            logger.log(self.log_level, "✓ %s", message)
        self.start_time = None

    def on_error(self, message: str, error: Exception | None = None) -> None:
        """Log operation error."""
        if error:
            logger.error("✗ %s: %s", message, error)
        else:
            logger.error("✗ %s", message)
        self.start_time = None


class RichProgressCallback:
    """Rich-based progress callback with progress bars and spinners."""

    def __init__(self, console: Any | None = None):
        """Initialize with an optional Rich console."""
        self._fallback: LoggingProgressCallback = LoggingProgressCallback()
        try:
            from rich.console import Console
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeElapsedColumn,
                TimeRemainingColumn,
            )

            self.Progress: type[Progress] | None = Progress
            self.SpinnerColumn: type[SpinnerColumn] | None = SpinnerColumn
            self.TextColumn: type[TextColumn] | None = TextColumn
            self.BarColumn: type[BarColumn] | None = BarColumn
            self.TimeElapsedColumn: type[TimeElapsedColumn] | None = TimeElapsedColumn
            self.TimeRemainingColumn: type[TimeRemainingColumn] | None = TimeRemainingColumn
            self.console = console or Console()
            self.progress: Progress | None = None
            self.task_id: Any | None = None
            self.start_time: float | None = None
            self._use_logging_only = False
        except ImportError:
            logger.warning("Rich not available, falling back to logging progress")
            self.Progress = None
            self.SpinnerColumn = None
            self.TextColumn = None
            self.BarColumn = None
            self.TimeElapsedColumn = None
            self.TimeRemainingColumn = None
            self.console = None
            self.progress = None
            self.task_id = None
            self.start_time = None
            self._use_logging_only = True

    def _is_live_context_active(self) -> bool:
        return bool(
            self.console
            and hasattr(self.console, "_live_stack")
            and len(getattr(self.console, "_live_stack", [])) > 0
        )

    def on_start(self, message: str) -> None:
        """Start a progress bar or spinner."""
        if self.Progress is None:
            self._use_logging_only = True
            self._fallback.on_start(message)
            return

        # Check if console has active Live context (avoid nested Progress)
        if self._is_live_context_active():
            self._use_logging_only = True
            self.start_time = time.perf_counter()
            logger.info("▶ %s", message)
            return

        self._use_logging_only = False

        self.start_time = time.perf_counter()
        progress_cls = self.Progress
        spinner_cls = self.SpinnerColumn
        text_cls = self.TextColumn
        bar_cls = self.BarColumn
        elapsed_cls = self.TimeElapsedColumn
        remaining_cls = self.TimeRemainingColumn

        if (
            progress_cls is None
            or spinner_cls is None
            or text_cls is None
            or bar_cls is None
            or elapsed_cls is None
            or remaining_cls is None
        ):
            self._use_logging_only = True
            self._fallback.on_start(message)
            return

        if self.progress is None:
            try:
                self.progress = progress_cls(
                    spinner_cls(),
                    text_cls("[progress.description]{task.description}"),
                    bar_cls(),
                    text_cls("[progress.percentage]{task.percentage:>3.0f}%"),
                    elapsed_cls(),
                    remaining_cls(),
                    console=self.console,
                )
                self.progress.start()
                self.task_id = self.progress.add_task(message, total=None)
                self._use_logging_only = False
            except Exception as e:
                # Fallback to logging if Progress creation fails
                logger.warning(f"Failed to create Progress bar: {e}, using logging instead")
                self._use_logging_only = True
                self._fallback.on_start(message)
                self.progress = None

    def on_progress(
        self, message: str, current: int | None = None, total: int | None = None
    ) -> None:
        """Update progress bar."""
        if self._use_logging_only or self.Progress is None:
            self._fallback.on_progress(message, current, total)
            return

        if self.progress is None or self.task_id is None:
            self.on_start(message)
            return

        try:
            if total is not None:
                self.progress.update(
                    self.task_id, total=total, completed=current, description=message
                )
            else:
                self.progress.update(self.task_id, description=message)
        except Exception as e:
            logger.warning(f"Failed to update Progress bar: {e}, using logging instead")
            self._fallback.on_progress(message, current, total)

    def on_complete(self, message: str, duration: float | None = None) -> None:
        """Complete the progress bar."""
        if self._use_logging_only or self.Progress is None:
            self._fallback.on_complete(message, duration)
            self.progress = None
            self.task_id = None
            self.start_time = None
            return

        if self.progress is None or self.task_id is None:
            logger.info("✓ %s", message)
            # Ensure cleanup even if no active progress instance
            self.progress = None
            self.task_id = None
            self.start_time = None
            return

        if duration is None and self.start_time is not None:
            duration = time.perf_counter() - self.start_time

        try:
            total = None
            if self.progress.tasks[self.task_id].total:
                total = 100
            self.progress.update(self.task_id, description=message, completed=total)
            self.progress.stop()
            if self.console is not None:
                if duration is not None:
                    self.console.print(f"[green]✓[/green] {message} (took {duration:.2f}s)")
                else:
                    self.console.print(f"[green]✓[/green] {message}")
            else:
                if duration is not None:
                    logger.info("✓ %s (took %.2fs)", message, duration)
                else:
                    logger.info("✓ %s", message)
        except Exception as e:
            logger.warning(f"Failed to complete Progress bar: {e}, using logging instead")
            if duration is not None:
                logger.info("✓ %s (took %.2fs)", message, duration)
            else:
                logger.info("✓ %s", message)

        # Ensure cleanup regardless of above branches
        self.progress = None
        self.task_id = None
        self.start_time = None

    def on_error(self, message: str, error: Exception | None = None) -> None:
        """Report error and stop progress."""
        if self._use_logging_only or self.Progress is None:
            self._fallback.on_error(message, error)
            self.progress = None
            self.task_id = None
            self.start_time = None
            return

        if self.progress is not None and self.task_id is not None:
            with contextlib.suppress(Exception):
                self.progress.stop()
            self.progress = None
            self.task_id = None

        try:
            if self.console is not None:
                if error:
                    self.console.print(f"[red]✗[/red] {message}: {error}")
                else:
                    self.console.print(f"[red]✗[/red] {message}")
            else:
                if error:
                    logger.error("✗ %s: %s", message, error)
                else:
                    logger.error("✗ %s", message)
        except Exception:
            # Fallback to logging if console print fails
            if error:
                logger.error("✗ %s: %s", message, error)
            else:
                logger.error("✗ %s", message)

        self.start_time = None


class NullProgressCallback:
    """No-op progress callback that does nothing."""

    def on_start(self, message: str) -> None:
        """No-op."""
        pass

    def on_progress(
        self, message: str, current: int | None = None, total: int | None = None
    ) -> None:
        """No-op."""
        pass

    def on_complete(self, message: str, duration: float | None = None) -> None:
        """No-op."""
        pass

    def on_error(self, message: str, error: Exception | None = None) -> None:
        """No-op."""
        pass


def get_default_progress_callback(
    use_rich: bool = True, console: Any | None = None
) -> ProgressCallback:
    """Get a default progress callback based on available libraries.

    Args:
        use_rich: Whether to prefer Rich progress bars (if available)
        console: Optional Rich console instance

    Returns:
        A progress callback implementation
    """
    if use_rich:
        try:
            return RichProgressCallback(console=console)
        except ImportError:
            pass
    return LoggingProgressCallback()
