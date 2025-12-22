"""Tool-related types and serialization for agent_framework."""

from __future__ import annotations

import logging
from typing import Any, cast

from .utils import _ensure_submodule

__all__ = ["patch_tool_types", "patch_serialization_module"]


def patch_tool_types(root: Any) -> None:
    """Patch tool-related types."""
    if not hasattr(root, "ToolProtocol"):

        class ToolProtocol:  # pragma: no cover - shim
            name: str | None = None
            description: str | None = None

            async def run(self, *args: Any, **kwargs: Any) -> Any:
                raise NotImplementedError

        root.ToolProtocol = ToolProtocol  # type: ignore[attr-defined]

    if not hasattr(root, "HostedCodeInterpreterTool"):

        class HostedCodeInterpreterTool(root.ToolProtocol):  # type: ignore[name-defined]
            async def run(self, code: str, **kwargs: Any) -> dict[str, Any]:
                return {"result": f"Executed: {code}", "kwargs": kwargs}

        root.HostedCodeInterpreterTool = HostedCodeInterpreterTool  # type: ignore[attr-defined]


def patch_serialization_module() -> None:
    """Patch serialization module helpers."""
    serialization = cast(Any, _ensure_submodule("agent_framework._serialization"))
    if not hasattr(serialization, "SerializationMixin"):

        class SerializationMixin:  # pragma: no cover - shim
            def to_dict(self, **_: Any) -> dict[str, Any]:
                return {}

        serialization.SerializationMixin = SerializationMixin

    tools_mod = cast(Any, _ensure_submodule("agent_framework._tools"))
    if not hasattr(tools_mod, "_tools_to_dict"):

        def _tools_to_dict(tools: Any):  # pragma: no cover - shim
            items = tools if isinstance(tools, list | tuple) else [tools]
            out = []
            for tool in items:
                if tool is None:
                    continue
                if hasattr(tool, "to_dict"):
                    try:
                        out.append(tool.to_dict())
                        continue
                    except Exception as e:
                        logging.warning("Serialization to dict failed for a tool: %s", e)
                if hasattr(tool, "schema"):
                    try:
                        out.append(tool.schema)
                        continue
                    except Exception as e:
                        logging.warning("Accessing 'schema' attribute failed for a tool: %s", e)
            return out

        tools_mod._tools_to_dict = _tools_to_dict
