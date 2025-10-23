"""Manager-related configuration helpers for the dynamic workflow."""

from __future__ import annotations

from typing import Any

from agenticfleet.config import settings


def get_manager_limits() -> dict[str, int | None]:
    """Return max round, stall, and reset counts for the manager."""
    workflow_cfg = settings.workflow_config.get("workflow", {}) or {}
    return {
        "max_round_count": workflow_cfg.get("max_rounds", 15),
        "max_stall_count": workflow_cfg.get("max_stalls", 3),
        "max_reset_count": workflow_cfg.get("max_resets", 2),
    }


def build_manager_kwargs(
    *,
    chat_client: Any,
    instructions: str,
    progress_ledger_retry_count: int | None = None,
) -> dict[str, Any]:
    """Construct keyword arguments for StandardMagenticManager."""
    limits = get_manager_limits()
    kwargs: dict[str, Any] = {
        "chat_client": chat_client,
        "instructions": instructions,
        "max_round_count": limits["max_round_count"],
        "max_stall_count": limits["max_stall_count"],
        "max_reset_count": limits["max_reset_count"],
    }
    if progress_ledger_retry_count is not None:
        kwargs["progress_ledger_retry_count"] = progress_ledger_retry_count
    return kwargs


__all__ = ["build_manager_kwargs", "get_manager_limits"]
