"""Utility functions for agent_framework module patching."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

__all__ = [
    "_reexport_public_api",
    "_import_or_stub",
    "_ensure_submodule",
    "_maybe_define",
]


def _reexport_public_api(root: Any, module_name: str) -> None:
    """Best-effort re-export of a submodule's public API onto ``agent_framework`` root."""

    try:  # pragma: no cover - depends on optional dependency versions
        module = importlib.import_module(module_name)
    except Exception:
        return

    public_names = getattr(module, "__all__", None)
    if not isinstance(public_names, (list, tuple)):
        return

    for name in public_names:
        if not isinstance(name, str):
            continue
        if hasattr(root, name):
            continue
        if not hasattr(module, name):
            continue
        setattr(root, name, getattr(module, name))


def _import_or_stub(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module

    try:  # pragma: no cover - best effort import
        module = importlib.import_module(name)
        return module
    except Exception:
        module = types.ModuleType(name)
        module.__dict__.setdefault("__path__", [])
        sys.modules[name] = module
        return module


def _ensure_submodule(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module

    try:  # pragma: no cover - passthrough when dependency is installed
        module = importlib.import_module(name)
    except Exception:  # pragma: no cover - fallback shim path
        module = types.ModuleType(name)
        module.__dict__.setdefault("__path__", [])

    sys.modules[name] = module
    return module


def _maybe_define(module: types.ModuleType, attr: str, factory: Any) -> None:
    if not hasattr(module, attr):
        setattr(module, attr, factory)
