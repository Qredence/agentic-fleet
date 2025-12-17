"""CLI utility functions."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from ..utils.cfg import env_config, load_config

logger = logging.getLogger(__name__)


def init_tracing() -> dict[str, Any]:
    """Initialize tracing (idempotent). Returns loaded config."""
    cfg = load_config()
    # Optional MLflow DSPy autologging behind env flag
    try:
        if env_config.mlflow_dspy_autolog:
            import mlflow  # type: ignore

            # Minimal autolog setup; users can point MLflow to a tracking URI externally
            with contextlib.suppress(Exception):
                # Older mlflow may not have dspy namespace; ignore silently
                mlflow.dspy.autolog(log_compiles=True, log_evals=True, log_traces=True)  # type: ignore
    except Exception as exc:
        logger.debug(f"MLflow autologging not enabled: {exc}")
    try:
        from ..utils.tracing import initialize_tracing

        initialize_tracing(cfg)
    except Exception as exc:  # pragma: no cover - tracing optional
        logger.debug(f"Tracing initialization skipped: {exc}")
    return cfg


def resolve_resource_path(path_like: str | Path) -> Path:
    """Resolve a resource path from CWD or fall back to packaged data.

    Looks for the provided path relative to current working directory. If it
    doesn't exist, tries to resolve it relative to the installed package root
    (i.e., alongside this file).
    """
    p = Path(path_like)
    if p.exists():
        return p
    pkg_root = Path(__file__).resolve().parent.parent.parent
    candidate = pkg_root / p
    return candidate if candidate.exists() else p
