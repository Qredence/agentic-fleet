"""Shared SerializationMixin loader for agent-framework tools.

This module centralizes the logic required to obtain ``SerializationMixin`` from
``agent_framework``. The upstream package exposes it from the private
``agent_framework._serialization`` module and, in certain environments (tests,
CI, or when agent-framework is not installed), that module may not exist.

By loading the mixin through this helper both the runtime and the test suite
share the exact same class identity, removing the need for ad-hoc monkeypatches
inside individual tools or tests.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Protocol, TypeVar, cast

__all__ = ["SerializationMixin", "get_serialization_mixin"]


class _SerializationMixinProtocol(Protocol):
    """Protocol describing the required SerializationMixin surface."""

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Return an OpenAI function-call schema representation."""


TSerializationMixin = TypeVar("TSerializationMixin", bound=type[_SerializationMixinProtocol])


def _ensure_agent_framework_package() -> types.ModuleType:
    """Ensure ``agent_framework`` exists in ``sys.modules`` and return it."""

    module = sys.modules.get("agent_framework")
    if module is None:  # pragma: no cover - exercised implicitly in tests
        module = types.ModuleType("agent_framework")
        sys.modules["agent_framework"] = module
    return module


def _ensure_serialization_submodule() -> types.ModuleType:
    """Ensure ``agent_framework._serialization`` exists and expose it."""

    parent = _ensure_agent_framework_package()
    submodule = sys.modules.get("agent_framework._serialization")
    if submodule is None:  # pragma: no cover - exercised implicitly in tests
        submodule = types.ModuleType("agent_framework._serialization")
        sys.modules["agent_framework._serialization"] = submodule
        parent._serialization = submodule  # type: ignore[attr-defined]
    return submodule


def get_serialization_mixin() -> TSerializationMixin:
    """Return the SerializationMixin class, creating a stub if necessary."""

    try:  # pragma: no cover - normal runtime path
        from agent_framework._serialization import SerializationMixin as _SerializationMixin

        return cast(TSerializationMixin, _SerializationMixin)
    except Exception:  # pragma: no cover - only executed in tests/minimal envs
        submodule = _ensure_serialization_submodule()
        if not hasattr(submodule, "SerializationMixin"):
            # Provide a minimal stub that satisfies agent-framework expectations.
            class _ShimSerializationMixin:
                def to_dict(self, **_: Any) -> dict[str, Any]:
                    return {}

            submodule.SerializationMixin = _ShimSerializationMixin  # type: ignore[attr-defined]
        return cast(TSerializationMixin, submodule.SerializationMixin)


SerializationMixin = get_serialization_mixin()
