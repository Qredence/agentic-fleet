from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


def health() -> dict[str, str]:
    return {"status": "ok"}


router.get("/health")(health)
