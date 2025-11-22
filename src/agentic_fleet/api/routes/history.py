from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from agentic_fleet.api.dependencies import Logger
from agentic_fleet.api.models import HistoryQuery, HistoryResponse
from agentic_fleet.utils.history_manager import HistoryManager

router = APIRouter()


@router.get("/", response_model=HistoryResponse)
async def get_history(logger: Logger, query: HistoryQuery = Depends()):  # noqa: B008
    """Analyze workflow history."""
    try:
        limit = query.last_n or (None if query.all else 20)
        raw_history = HistoryManager().load_history(limit=limit)

        runs: list[dict[str, Any]] = []
        for item in raw_history:
            run = {
                "run_id": item.get("workflowId") or item.get("run_id", "unknown"),
                "status": "completed",
                "task": item.get("task", ""),
                "result": item.get("result", ""),
            }

            if query.routing:
                run["routing"] = item.get("routing", {})
            if query.agents:
                run["agents"] = item.get("routing", {}).get("assigned_to", [])
            if query.timing:
                run["timing"] = {
                    "total": item.get("total_time_seconds"),
                    "phases": item.get("phase_timings", {}),
                }

            runs.append(run)

        return HistoryResponse(runs=runs)

    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
