"""Checkpoint storage utilities for AgenticFleet."""

from __future__ import annotations

import asyncio
import json
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


class AgenticFleetFileCheckpointStorage(FileCheckpointStorage):  # type: ignore[misc]
    """File-based checkpoint storage with listing support."""

    def __init__(self, storage_path: str | Path) -> None:
        super().__init__(storage_path)
        self._storage_path = Path(storage_path)

    async def list_checkpoints(self, workflow_id: str | None = None) -> list[dict[str, Any]]:  # type: ignore[override]
        """Return serialized checkpoint metadata sorted by newest first."""

        return await asyncio.to_thread(self._load_checkpoints)

    def _load_checkpoints(self) -> list[dict[str, Any]]:
        checkpoints: list[dict[str, Any]] = []

        for checkpoint_file in self._storage_path.glob("*.json"):
            try:
                with checkpoint_file.open() as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to read checkpoint %s: %s", checkpoint_file, exc)
                continue

            checkpoints.append(
                {
                    "checkpoint_id": data.get("checkpoint_id") or data.get("id"),
                    "workflow_id": data.get("workflow_id"),
                    "timestamp": data.get("timestamp"),
                    "current_round": self._extract_current_round(data),
                    "metadata": data.get("metadata", {}),
                }
            )

        checkpoints.sort(key=self._checkpoint_sort_key, reverse=True)

        return checkpoints

    @staticmethod
    def _extract_current_round(data: dict[str, Any]) -> int:
        if "current_round" in data and isinstance(data["current_round"], int):
            return data["current_round"]

        orchestrator_state = data.get("executor_states", {}).get("magentic_orchestrator", {})
        if isinstance(orchestrator_state, dict):
            for key in ("current_round", "plan_review_round", "round"):
                value = orchestrator_state.get(key)
                if isinstance(value, int):
                    return value

        return 0

    @staticmethod
    def _checkpoint_sort_key(checkpoint: dict[str, Any]) -> tuple[float, str]:
        timestamp = checkpoint.get("timestamp")
        parsed = AgenticFleetFileCheckpointStorage._parse_timestamp(timestamp)
        identifier = str(checkpoint.get("checkpoint_id") or "")
        return (parsed, identifier)

    @staticmethod
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
                except ValueError:
                    return float("-inf")

        return float("-inf")


__all__ = ["AgenticFleetFileCheckpointStorage"]
