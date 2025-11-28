"""Tools package for agent framework integration."""

# Provide compatibility shims for agent_framework test stubs so imports succeed
import logging
import sys
import types
from typing import Any

logger = logging.getLogger(__name__)
# Ensure agent_framework._serialization with SerializationMixin exists (shared identity)
_ser_mod_name = "agent_framework._serialization"
if _ser_mod_name not in sys.modules:
    _ser_mod = types.ModuleType(_ser_mod_name)

    class SerializationMixin:  # type: ignore[too-many-ancestors]
        def to_dict(self, **_: Any) -> dict[str, Any]:
            return {}

    _ser_mod.SerializationMixin = SerializationMixin  # type: ignore[attr-defined]
    sys.modules[_ser_mod_name] = _ser_mod

# Ensure agent_framework._tools with _tools_to_dict exists
_tools_mod_name = "agent_framework._tools"
if _tools_mod_name not in sys.modules:
    _tools_mod = types.ModuleType(_tools_mod_name)

    def _tools_to_dict(tools: Any):  # type: ignore[no-redef]
        items = tools if isinstance(tools, list | tuple) else [tools]
        out = []
        for t in items:
            if t is None:
                continue
            if hasattr(t, "to_dict"):
                try:
                    out.append(t.to_dict())
                    continue
                except Exception:
                    logger.exception("Failed to convert tool '%r' to dict:", t)
            if hasattr(t, "schema"):
                try:
                    out.append(t.schema)
                    continue
                except Exception:
                    logger.exception("Failed to get schema from tool '%r':", t)
        return out

    _tools_mod._tools_to_dict = _tools_to_dict  # type: ignore[attr-defined]
    sys.modules[_tools_mod_name] = _tools_mod

# ruff: noqa: E402 - imports must come after sys.modules setup
from .azure_search_provider import AzureAISearchContextProvider
from .base_mcp_tool import BaseMCPTool
from .browser_tool import BrowserTool
from .context7_deepwiki_tool import Context7DeepWikiTool
from .hosted_code_adapter import HostedCodeInterpreterAdapter
from .package_search_mcp_tool import PackageSearchMCPTool
from .tavily_mcp_tool import TavilyMCPTool
from .tavily_tool import TavilySearchTool

__all__ = [
    "AzureAISearchContextProvider",
    "BaseMCPTool",
    "BrowserTool",
    "Context7DeepWikiTool",
    "HostedCodeInterpreterAdapter",
    "PackageSearchMCPTool",
    "TavilyMCPTool",
    "TavilySearchTool",
]
