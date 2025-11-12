"""Workflow checkpoint persistence utilities."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from agent_framework._workflows import (
    FileCheckpointStorage,
    WorkflowCheckpoint,
    get_checkpoint_summary,
)

from agentic_fleet.models.requests import WorkflowCheckpointMetadata

logger = logging.getLogger(__name__)
_T = TypeVar("_T")


class WorkflowCheckpointService:
    """Wrapper around :class:`FileCheckpointStorage` with convenience helpers."""

    def __init__(self, base_dir: Path | str = Path("var/checkpoints")) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._storage = FileCheckpointStorage(str(self.base_dir))

    @property
    def storage(self) -> FileCheckpointStorage:
        """Expose the underlying storage instance."""

        return self._storage

    async def list_metadata(
        self, workflow_id: str | None = None
    ) -> list[WorkflowCheckpointMetadata]:
        """Return lightweight metadata for stored checkpoints."""

        checkpoints = await self._maybe_await(self._storage.list_checkpoints, workflow_id)
        metadata: list[WorkflowCheckpointMetadata] = []
        for checkpoint in checkpoints:
            summary = get_checkpoint_summary(checkpoint)
            workflow_id, conversation_id = self._extract_ids(summary.checkpoint_id)
            created_at = self._coerce_timestamp(summary.timestamp)

            logger.debug(
                "Checkpoint summary parsed",
                extra={
                    "checkpoint_id": summary.checkpoint_id,
                    "workflow_id": workflow_id,
                    "conversation_id": conversation_id,
                    "created_at": created_at.isoformat(),
                },
            )

            metadata.append(
                WorkflowCheckpointMetadata(
                    checkpoint_id=summary.checkpoint_id,
                    workflow_id=workflow_id,
                    conversation_id=conversation_id,
                    created_at=created_at,
                    path=str(self.base_dir / f"{summary.checkpoint_id}.json"),
                )
            )
        return metadata

    async def load(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        """Load a checkpoint by ID."""

        return await self._maybe_await(self._storage.load_checkpoint, checkpoint_id)

    @staticmethod
    def _extract_ids(checkpoint_id: str) -> tuple[str, str | None]:
        """Extract workflow and conversation identifiers from checkpoint ID."""
        parts = checkpoint_id.split(":", maxsplit=2)
        workflow_id = parts[0]
        conversation_id: str | None = None
        if len(parts) >= 2 and parts[1]:
            conversation_id = parts[1]
        if len(parts) > 2:
            logger.debug(
                "Checkpoint ID contains additional segments",
                extra={"checkpoint_id": checkpoint_id, "segments": parts},
            )
        return workflow_id, conversation_id

    @staticmethod
    def _coerce_timestamp(raw_timestamp: Any) -> datetime:
        """Normalize timestamp values to datetime."""
        if isinstance(raw_timestamp, datetime):
            return raw_timestamp
        if isinstance(raw_timestamp, int | float):
            return datetime.fromtimestamp(raw_timestamp)
        if isinstance(raw_timestamp, str):
            candidate = raw_timestamp.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                logger.debug(
                    "Failed ISO conversion for timestamp",
                    extra={"raw_timestamp": raw_timestamp},
                )
        raise TypeError(f"Unsupported timestamp format: {raw_timestamp!r}")

    async def save(self, checkpoint: WorkflowCheckpoint) -> str:
        """Persist checkpoint to disk and return the assigned identifier."""

        return await self._maybe_await(self._storage.save_checkpoint, checkpoint)

    async def delete(self, checkpoint_id: str) -> None:
        """Delete checkpoint file if it exists."""

        path = self.base_dir / f"{checkpoint_id}.json"
        path.unlink(missing_ok=True)

    async def clear(self) -> None:
        """Remove all checkpoints under the managed directory."""

        for path in self.base_dir.glob("*.json"):
            path.unlink(missing_ok=True)

    @staticmethod
    async def _maybe_await(
        func: Callable[..., Awaitable[_T] | _T],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Call sync or async functions transparently."""
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


__all__ = ["WorkflowCheckpointService"]
