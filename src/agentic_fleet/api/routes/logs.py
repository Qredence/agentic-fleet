"""Logs API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from agentic_fleet.api.dependencies import Logger
from agentic_fleet.api.models import LogQuery, LogResponse
from agentic_fleet.api.settings import settings

router = APIRouter()
LOG_FILE = Path(settings.LOG_FILE_PATH)


@router.get("/", response_model=LogResponse)
async def view_logs(logger: Logger, query: LogQuery = Depends()):  # noqa: B008
    """View system logs."""
    if not LOG_FILE.exists():
        return LogResponse(logs=[])

    try:
        logs = []
        with open(LOG_FILE) as f:
            for line in f.readlines()[-1000:]:  # Last 1000 lines
                if " - " not in line:
                    continue

                parts = line.strip().split(" - ", 3)
                if len(parts) < 4:
                    continue

                ts, name, level, msg = parts[0], parts[1], parts[2], parts[3]

                if query.level and query.level.upper() != level:
                    continue
                if query.agent_id and query.agent_id not in msg:
                    continue
                if query.run_id and query.run_id not in msg:
                    continue

                logs.append({"timestamp": ts, "level": level, "logger": name, "message": msg})

        return LogResponse(logs=logs)

    except Exception as e:
        logger.error(f"Log read error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
