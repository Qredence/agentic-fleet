"""Checkpoint storage utilities for AgenticFleet."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from agent_framework import FileCheckpointStorage

from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)


class AgenticFleetFileCheckpointStorage(FileCheckpointStorage):
    """File-based checkpoint storage with listing support."""

    def __init__(self, storage_path: str | Path) -> None:
        super().__init__(storage_path)
        self._storage_path = Path(storage_path)

    async def list_checkpoints(self) -> list[dict[str, Any]]:  # type: ignore[override]
        """Return serialized checkpoint metadata sorted by newest first."""

        return await asyncio.to_thread(self._load_checkpoints)

    def _load_checkpoints(self) -> list[dict[str, Any]]:
        checkpoints: list[dict[str, Any]] = []

        for checkpoint_file in sorted(self._storage_path.glob("*.json"), reverse=True):
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


__all__ = ["AgenticFleetFileCheckpointStorage"]
