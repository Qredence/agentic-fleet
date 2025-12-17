"""Application settings for the FastAPI service.

We keep configuration centralized and typed to avoid scattering `os.getenv`
through the codebase. Settings are intentionally lightweight (no extra deps)
and cached for reuse.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return ["http://localhost:5173", "http://localhost:3000"]
    return [o.strip() for o in value.split(",") if o.strip()]


@dataclass(slots=True)
class AppSettings:
    """Typed configuration for the AgenticFleet API."""

    cors_allowed_origins: list[str]
    log_level: str
    log_format: str
    log_json: bool
    max_concurrent_workflows: int
    conversations_path: Path
    ws_allow_localhost: bool
    app_version: str = "0.6.95"
    app_name: str = "AgenticFleet API"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load settings from environment once (process-wide cache)."""

    return AppSettings(
        cors_allowed_origins=_parse_origins(os.getenv("CORS_ALLOWED_ORIGINS")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_format=os.getenv(
            "LOG_FORMAT", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ),
        log_json=_parse_bool(os.getenv("LOG_JSON"), default=True),
        max_concurrent_workflows=int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10")),
        conversations_path=Path(os.getenv("CONVERSATIONS_PATH", ".var/data/conversations.json")),
        ws_allow_localhost=_parse_bool(os.getenv("WS_ALLOW_LOCALHOST"), default=True),
    )


__all__ = ["AppSettings", "get_settings"]
