from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


async def health() -> dict[str, str]:
    return {"status": "ok"}


router.get("/health")(health)
