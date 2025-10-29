from __future__ import annotations

from fastapi import APIRouter

from agenticfleet import __version__

router = APIRouter(tags=["system"])


@router.get("/")
async def root() -> dict[str, str]:
    return {"name": "AgenticFleet Minimal API", "version": __version__, "status": "ok"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/api/info")
async def api_info() -> dict[str, str]:
    return {"name": "AgenticFleet", "version": __version__, "mode": "minimal"}
