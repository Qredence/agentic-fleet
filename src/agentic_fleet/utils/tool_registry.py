"""
Tool Registry for managing tool metadata and capabilities.

Provides a centralized registry that tracks available tools, their schemas,
descriptions, and which agents have access to them. This enables DSPy modules
to make tool-aware routing and analysis decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, cast, runtime_checkable

from ..utils.cache import CacheStats, TTLCache  # type: ignore
from ..workflows.exceptions import ToolError

logger = logging.getLogger(__name__)


@runtime_checkable
class RunnableTool(Protocol):
    """Protocol for tools that expose an async ``run`` coroutine.

    This aligns with how tools are used by the registry in practice, without
    depending directly on the concrete agent-framework ``ToolProtocol`` type
    (which may be stubbed differently in tests).
    """

    async def run(self, **kwargs: Any) -> Any:  # pragma: no cover - structural
        """Execute the tool asynchronously."""
        ...


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    description: str
    schema: dict[str, Any]
    agent: str
    tool_instance: RunnableTool | None = None
    available: bool = True
    capabilities: set[str] = field(default_factory=set)
    use_cases: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    # Efficiency hints
    latency_cost_hint: str = "medium"  # low|medium|high
    concise_description: str = ""


class ToolRegistry:
    """
    Central registry for managing tool metadata and capabilities.

    Tracks which tools are available, which agents have them, and provides
    formatted descriptions for DSPy modules to use in their prompts.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, ToolMetadata] = {}
        self._agent_tools: dict[str, list[str]] = {}
        # Reverse indices for O(1) lookups (optimization)
        self._alias_index: dict[str, str] = {}  # alias -> canonical tool name
        self._capability_index: dict[str, set[str]] = {}  # capability -> set of tool names
        # Simple result cache for tool calls to avoid repeated network usage
        self._tool_result_cache: TTLCache[str, str] = TTLCache(ttl_seconds=300)

    def register_tool(
        self,
        name: str,
        tool: RunnableTool,
        agent: str,
        capabilities: list[str] | None = None,
        use_cases: list[str] | None = None,
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            name: Unique name for the tool (e.g., "TavilySearchTool")
            tool: Tool instance implementing ToolProtocol
            agent: Name of agent that has access to this tool
            capabilities: List of capability tags (e.g., ["web_search", "real_time"])
            use_cases: List of use case descriptions
        """
        schema: dict[str, Any] = getattr(tool, "schema", {}) or {}
        description: str = getattr(tool, "description", "No description")

        # Infer capabilities from tool name/description if not provided
        inferred_capabilities = self._infer_capabilities(name, description)
        if capabilities:
            inferred_capabilities.update(capabilities)

        # Derive alias list (canonical class name if different from primary name)
        class_name = tool.__class__.__name__
        aliases: list[str] = []
        if class_name != name:
            aliases.append(class_name)

        metadata = ToolMetadata(
            name=name,
            description=description,
            schema=schema,
            agent=agent,
            tool_instance=tool,
            available=True,
            capabilities=inferred_capabilities,
            use_cases=use_cases or [],
            aliases=aliases,
            latency_cost_hint=self._infer_latency_hint(inferred_capabilities),
            concise_description=self._to_concise_description(description),
        )

        self._tools[name] = metadata

        # Update reverse indices for O(1) lookups
        for alias in aliases:
            self._alias_index[alias] = name
        for cap in inferred_capabilities:
            cap_lower = cap.lower()
            if cap_lower not in self._capability_index:
                self._capability_index[cap_lower] = set()
            self._capability_index[cap_lower].add(name)

        if aliases:
            logger.info(
                "Registered tool '%s' with aliases %s (capabilities=%s)",
                name,
                aliases,
                sorted(inferred_capabilities),
            )
        else:
            logger.info(
                "Registered tool '%s' (capabilities=%s)",
                name,
                sorted(inferred_capabilities),
            )

        # Track which tools each agent has
        if agent not in self._agent_tools:
            self._agent_tools[agent] = []
        if name not in self._agent_tools[agent]:
            self._agent_tools[agent].append(name)

    def register_tool_by_agent(self, agent_name: str, tool: Any | None) -> None:
        """
        Register a tool from an agent's tool configuration.

        Args:
            agent_name: Name of the agent
            tool: Tool instance (None if agent has no tool). Can also be a list/tuple of tools or dict.
        """
        if tool is None:
            return

        if isinstance(tool, dict):
            # Accept OpenAI function-style dicts or minimal dict specs
            try:
                if "function" in tool:
                    fn = tool["function"] or {}
                    name = fn.get("name") or "anonymous_tool"
                    description = fn.get("description") or "No description"
                    schema = {"type": "function", "function": fn}
                else:
                    # Minimal fallback: expect 'name' at top-level
                    name = tool.get("name") or "anonymous_tool"
                    description = tool.get("description") or "No description"
                    schema = tool

                class _DictToolAdapter:
                    def __init__(self, nm: str, desc: str, sch: dict[str, Any]) -> None:
                        self.name = nm
                        self.description = desc
                        self.schema = sch

                    async def run(self, **_: Any) -> Any:
                        raise NotImplementedError(
                            f"Dict-based tool '{self.name}' is metadata-only and cannot be executed"
                        )

                    def to_dict(self, **__: Any) -> dict[str, Any]:
                        return self.schema

                adapter = _DictToolAdapter(name, description, schema)
                self.register_tool(
                    name=name,
                    tool=cast(RunnableTool, adapter),
                    agent=agent_name,
                    capabilities=list(self._infer_capabilities(name, description)),
                    use_cases=[],
                )
            except Exception as e:
                logger.debug(f"Skipping dict tool config for {agent_name}: {e}")
                return

        # Support list/tuple of tools (future multi-tool agents)
        if isinstance(tool, list | tuple):
            for single in tool:
                if single:  # guard against None entries
                    self.register_tool_by_agent(agent_name, single)
            return

        # Extract tool name from explicit .name or fallback to class name
        tool_name = getattr(tool, "name", None) or tool.__class__.__name__
        logger.debug(
            "Registering tool instance for agent '%s': raw_name=%s class=%s has_schema=%s",
            agent_name,
            tool_name,
            tool.__class__.__name__,
            hasattr(tool, "schema"),
        )

        # Infer capabilities and use cases based on tool type
        # Cast to RunnableTool for type checker since we've already validated it's not a dict/list
        tool_instance = cast(RunnableTool, tool)
        capabilities = self._infer_capabilities_from_tool(tool_instance)
        use_cases = self._infer_use_cases_from_tool(tool_instance)

        self.register_tool(
            name=tool_name,
            tool=tool_instance,
            agent=agent_name,
            capabilities=capabilities,
            use_cases=use_cases,
        )

    def get_tool(self, name: str) -> ToolMetadata | None:
        """
        Get metadata for a specific tool.

        Args:
            name: Tool name

        Returns:
            ToolMetadata if found, None otherwise
        """
        meta = self._tools.get(name)
        if meta:
            return meta
        # O(1) alias resolution via reverse index
        canonical_name = self._alias_index.get(name)
        if canonical_name:
            return self._tools.get(canonical_name)
        return None

    def get_agent_tools(self, agent_name: str) -> list[ToolMetadata]:
        """
        Get all tools available to a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of ToolMetadata for tools available to the agent
        """
        tool_names = self._agent_tools.get(agent_name, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tool_descriptions(self, agent_filter: str | None = None) -> str:
        """
        Get formatted tool descriptions for DSPy prompts.

        Args:
            agent_filter: If provided, only return tools for this agent

        Returns:
            Formatted string describing available tools
        """
        tools = self.get_agent_tools(agent_filter) if agent_filter else list(self._tools.values())

        if not tools:
            return "No tools are currently available."

        descriptions = []
        for tool in tools:
            if not tool.available:
                continue

            alias_part = f" | aliases: {', '.join(tool.aliases)}" if tool.aliases else ""
            desc = f"- {tool.name}{alias_part} (available to {tool.agent})"
            hint = f" [Latency: {tool.latency_cost_hint}]"
            summary = tool.concise_description or tool.description
            desc += f": {summary}{hint}"

            if tool.capabilities:
                caps = ", ".join(sorted(tool.capabilities))
                desc += f" [Capabilities: {caps}]"

            if tool.use_cases:
                desc += f" Use cases: {', '.join(tool.use_cases[:3])}"

            descriptions.append(desc)

        return "\n".join(descriptions)

    def get_available_tools(self) -> dict[str, Any]:
        """
        Get a dictionary representation of all available tools.

        Returns:
            Dictionary mapping tool names to their metadata
        """
        return {
            name: {
                "description": meta.description,
                "agent": meta.agent,
                "available": meta.available,
                "capabilities": list(meta.capabilities),
                "use_cases": meta.use_cases,
            }
            for name, meta in self._tools.items()
            if meta.available
        }

    def get_tools_by_capability(self, capability: str) -> list[ToolMetadata]:
        """
        Get all tools that have a specific capability.

        Args:
            capability: Capability tag to search for

        Returns:
            List of ToolMetadata with the specified capability
        """
        # O(1) lookup via capability index, then filter for availability
        tool_names = self._capability_index.get(capability.lower(), set())
        return [
            self._tools[name]
            for name in tool_names
            if name in self._tools and self._tools[name].available
        ]

    def can_execute_tool(self, tool_name: str) -> bool:
        """
        Check if a tool can be executed (has instance and is available).

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool can be executed
        """
        tool = self._tools.get(tool_name)
        return tool is not None and tool.available and tool.tool_instance is not None

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> str:
        """
        Execute a tool directly.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments to pass to tool.run()

        Returns:
            Tool execution result as a string

        Raises:
            ToolError: If tool not found, unavailable, or execution fails
        """
        meta = self._tools.get(tool_name)
        if not meta:
            raise ToolError(
                f"Tool '{tool_name}' not found in registry",
                tool_name=tool_name,
                tool_args=kwargs,
            )
        if meta.tool_instance is None:
            raise ToolError(
                f"Tool '{tool_name}' has no executable instance (metadata-only)",
                tool_name=tool_name,
                tool_args=kwargs,
            )
        if not meta.available:
            raise ToolError(
                f"Tool '{tool_name}' is currently unavailable",
                tool_name=tool_name,
                tool_args=kwargs,
            )

        tool_instance = meta.tool_instance

        try:
            # Cache by tool + args signature
            cache_key = self._tool_cache_key(tool_name, kwargs)
            cached = self._tool_result_cache.get(cache_key)
            if cached is not None:
                return cached
            result = await tool_instance.run(**kwargs)
            result_str = str(result) if result is not None else ""
            # Cache small results to prevent excessive memory
            if len(result_str) <= 5000:
                self._tool_result_cache.set(cache_key, result_str)
            return result_str
        except ToolError:
            # Re-raise ToolError as-is to preserve context
            raise
        except Exception as e:
            raise ToolError(
                f"Tool '{tool_name}' execution failed: {e!s}",
                tool_name=tool_name,
                tool_args=kwargs,
            ) from e

    def get_tool_cache_stats(self) -> CacheStats:
        """Expose cache statistics for tool result caching."""
        return self._tool_result_cache.get_stats()

    def _tool_cache_key(self, tool_name: str, kwargs: dict[str, Any]) -> str:
        """Build a stable cache key for a tool invocation."""
        try:
            # Sort kwargs for stable hashing
            items = sorted((k, str(v)) for k, v in kwargs.items())
            arg_sig = "|".join(f"{k}={v}" for k, v in items)
        except Exception:
            arg_sig = str(kwargs)
        return f"{tool_name}:{arg_sig}"

    def _infer_capabilities(self, name: str, description: str) -> set[str]:
        """Infer capabilities from tool name and description."""
        capabilities = set()
        name_lower = name.lower()
        desc_lower = description.lower()

        # Check for common capability keywords
        if "search" in name_lower or "search" in desc_lower:
            capabilities.add("web_search")
        if "code" in name_lower or "code" in desc_lower or "interpreter" in name_lower:
            capabilities.add("code_execution")
        if "real-time" in desc_lower or "real_time" in desc_lower:
            capabilities.add("real_time")
        if "web" in desc_lower or "internet" in desc_lower:
            capabilities.add("web_access")
        if "tavily" in name_lower:
            capabilities.add("web_search")
            capabilities.add("real_time")
            capabilities.add("citations")

        return capabilities

    def _infer_capabilities_from_tool(self, tool: RunnableTool) -> list[str]:
        """Infer capabilities from tool instance."""
        name = getattr(tool, "name", "") or tool.__class__.__name__
        description = getattr(tool, "description", "") or ""
        return list(self._infer_capabilities(name, description))

    def _infer_use_cases_from_tool(self, tool: RunnableTool) -> list[str]:
        """Infer use cases from tool type."""
        name = getattr(tool, "name", "") or tool.__class__.__name__
        name_lower = name.lower()

        use_cases = []
        if "tavily" in name_lower or "search" in name_lower:
            use_cases.extend(
                [
                    "Finding up-to-date information",
                    "Researching current events",
                    "Gathering facts with citations",
                ]
            )
        if "code" in name_lower or "interpreter" in name_lower:
            use_cases.extend(
                [
                    "Data analysis and computation",
                    "Running Python code",
                    "Creating visualizations",
                ]
            )

        return use_cases

    def _infer_latency_hint(self, capabilities: set[str]) -> str:
        """Rudimentary latency/cost hint from capabilities."""
        caps_lower = {c.lower() for c in capabilities}
        if "code_execution" in caps_lower:
            return "high"
        if "real_time" in caps_lower:
            return "high"
        if "web_search" in caps_lower:
            return "medium"
        return "medium"

    def _to_concise_description(self, description: str, max_len: int = 200) -> str:
        """Clamp long descriptions for prompt efficiency."""
        if not description:
            return ""
        if len(description) <= max_len:
            return description
        return description[: max_len - 1].rstrip() + "…"

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._agent_tools.clear()
        self._alias_index.clear()
        self._capability_index.clear()
