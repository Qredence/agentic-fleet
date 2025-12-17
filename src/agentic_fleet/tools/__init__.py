"""Tools package for agent framework integration."""

from agentic_fleet.utils.agent_framework_shims import ensure_agent_framework_shims

ensure_agent_framework_shims()

from .azure_search_provider import AzureAISearchContextProvider  # noqa: E402
from .base import SchemaToolMixin  # noqa: E402
from .base_mcp_tool import BaseMCPTool  # noqa: E402
from .browser_tool import BrowserTool  # noqa: E402
from .hosted_code_adapter import HostedCodeInterpreterAdapter  # noqa: E402
from .mcp_tools import Context7DeepWikiTool, PackageSearchMCPTool, TavilyMCPTool  # noqa: E402
from .tavily_tool import TavilySearchTool  # noqa: E402

__all__ = [
    "AzureAISearchContextProvider",
    "BaseMCPTool",
    "BrowserTool",
    "Context7DeepWikiTool",
    "HostedCodeInterpreterAdapter",
    "PackageSearchMCPTool",
    "SchemaToolMixin",
    "TavilyMCPTool",
    "TavilySearchTool",
]
