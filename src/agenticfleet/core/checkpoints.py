"""Checkpoint storage utilities for AgenticFleet."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from agent_framework import FileCheckpointStorage
except ImportError:

    class FileCheckpointStorage:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "agent_framework is required for AgenticFleetFileCheckpointStorage. "
                "Please install agent_framework to use checkpoint storage features."
            )


from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)


def normalize_checkpoint_metadata(
    checkpoint: object,
    *,
    fallback_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Normalize raw checkpoint metadata regardless of source representation.

    Args:
        checkpoint: Raw checkpoint object or dictionary.
        fallback_id: Optional identifier to use when the source does not include one.

    Returns:
        Dictionary containing normalized checkpoint metadata or None if the checkpoint could
        not be interpreted.
    """

    if checkpoint is None:
        return None

    def resolve(source: object, *names: str, default: object = None) -> object:
        for name in names:
            if isinstance(source, dict) and name in source:
                value = source[name]
                if value is not None:
                    return value
            if hasattr(source, name):
                value = getattr(source, name)
                if value is not None:
                    return value
        return default

    checkpoint_id = resolve(checkpoint, "checkpoint_id", "id")
    if checkpoint_id is None:
        checkpoint_id = fallback_id

    workflow_id = resolve(checkpoint, "workflow_id")
    timestamp = resolve(checkpoint, "timestamp")

    metadata_value = resolve(checkpoint, "metadata")
    metadata: dict[str, Any]
    if isinstance(metadata_value, Mapping):
        metadata = dict(metadata_value)
    else:
        metadata = {}

    current_round_value = resolve(checkpoint, "current_round", "round")
    current_round = _coerce_round(current_round_value, checkpoint, metadata)

    normalized = {
        "checkpoint_id": str(checkpoint_id) if checkpoint_id is not None else None,
        "workflow_id": str(workflow_id) if workflow_id is not None else None,
        "timestamp": timestamp,
        "current_round": current_round,
        "metadata": metadata,
    }

    has_identifier = normalized["checkpoint_id"] is not None
    has_workflow = normalized["workflow_id"] is not None
    has_timestamp = normalized["timestamp"] is not None
    has_round_information = (
        isinstance(normalized["current_round"], int) and normalized["current_round"] > 0
    )
    has_metadata = bool(normalized["metadata"])

    if not any(
        (
            has_identifier,
            has_workflow,
            has_timestamp,
            has_round_information,
            has_metadata,
        )
    ):
        # Discard empty checkpoints
        return None

    return normalized


def load_checkpoint_metadata_from_path(
    storage_path: str | Path,
) -> list[dict[str, Any]]:
    """
    Load checkpoint metadata from JSON files stored at ``storage_path``.

    Args:
        storage_path: Directory containing JSON checkpoint files.

    Returns:
        List of normalized checkpoint metadata dictionaries sorted newest first.
    """

    base_path = Path(storage_path).expanduser()
    if not base_path.exists() or not base_path.is_dir():
        logger.debug("Checkpoint directory %s does not exist or is not a directory", base_path)
        return []

    checkpoints: list[dict[str, Any]] = []
    for checkpoint_file in base_path.glob("*.json"):
        try:
            with checkpoint_file.open() as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read checkpoint %s: %s", checkpoint_file, exc)
            continue

        normalized = normalize_checkpoint_metadata(data, fallback_id=checkpoint_file.stem)
        if normalized:
            checkpoints.append(normalized)

    return sort_checkpoint_metadata(checkpoints)


def sort_checkpoint_metadata(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort checkpoint metadata in-place from newest to oldest.

    Args:
        checkpoints: Checkpoint metadata dictionaries.

    Returns:
        Sorted list of checkpoints (same list instance that was passed in).
    """

    checkpoints.sort(key=_checkpoint_sort_key, reverse=True)
    return checkpoints


def _coerce_round(
    candidate_round: object,
    checkpoint: object,
    metadata: Mapping[str, Any],
) -> int:
    if isinstance(candidate_round, int):
        return candidate_round

    executor_states: Mapping[str, Any] | None = None
    if isinstance(metadata, Mapping):
        maybe_states = metadata.get("executor_states")
        if isinstance(maybe_states, Mapping):
            executor_states = maybe_states

    if executor_states is None:
        resolved_states: object
        if isinstance(checkpoint, Mapping):
            resolved_states = checkpoint.get("executor_states")  # type: ignore[index]
        else:
            resolved_states = getattr(checkpoint, "executor_states", None)
        if isinstance(resolved_states, Mapping):
            executor_states = resolved_states

    if isinstance(executor_states, Mapping):
        orchestrator_state = executor_states.get("magentic_orchestrator")
        if isinstance(orchestrator_state, Mapping):
            for key in ("current_round", "plan_review_round", "round"):
                value = orchestrator_state.get(key)
                if isinstance(value, int):
                    return value

    return 0


def _checkpoint_sort_key(checkpoint: Mapping[str, Any]) -> tuple[float, str]:
    timestamp = checkpoint.get("timestamp")
    parsed = _parse_timestamp(timestamp)
    identifier = str(checkpoint.get("checkpoint_id") or "")
    return (parsed, identifier)


def _parse_timestamp(timestamp: object) -> float:
    if timestamp is None:
        return float("-inf")

    if isinstance(timestamp, int | float):
        return float(timestamp)

    if isinstance(timestamp, str):
        iso_value = timestamp
        if iso_value.endswith("Z"):
            iso_value = iso_value[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(iso_value).timestamp()
        except ValueError:
            try:
                return float(iso_value)
            except ValueError as float_error:
                raise ValueError(f"Invalid timestamp value: {timestamp}") from float_error

    raise ValueError(f"Unsupported timestamp type: {type(timestamp).__name__}")


class AgenticFleetFileCheckpointStorage(FileCheckpointStorage):  # type: ignore[misc]
    """File-based checkpoint storage with listing support."""

    def __init__(self, storage_path: str | Path) -> None:
        super().__init__(storage_path)
        self._storage_path = Path(storage_path)

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[dict[str, Any]]:  # type: ignore[override]
        """Return serialized checkpoint metadata sorted by newest first."""

        checkpoints = await asyncio.to_thread(self._load_checkpoints)
        if workflow_id is not None:
            target = str(workflow_id)
            return [cp for cp in checkpoints if cp.get("workflow_id") == target]
        return checkpoints

    def _load_checkpoints(self) -> list[dict[str, Any]]:
        return load_checkpoint_metadata_from_path(self._storage_path)


__all__ = [
    "AgenticFleetFileCheckpointStorage",
    "load_checkpoint_metadata_from_path",
    "normalize_checkpoint_metadata",
    "sort_checkpoint_metadata",
]
