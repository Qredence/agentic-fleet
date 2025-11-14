"""
Tool Registry for managing tool metadata and capabilities.

Provides a centralized registry that tracks available tools, their schemas,
descriptions, and which agents have access to them. This enables DSPy modules
to make tool-aware routing and analysis decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from agent_framework import ToolProtocol

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    description: str
    schema: dict[str, Any]
    agent: str
    tool_instance: ToolProtocol | None = None
    available: bool = True
    capabilities: set[str] = field(default_factory=set)
    use_cases: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


class ToolRegistry:
    """
    Central registry for managing tool metadata and capabilities.

    Tracks which tools are available, which agents have them, and provides
    formatted descriptions for DSPy modules to use in their prompts.
    """

    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: dict[str, ToolMetadata] = {}
        self._agent_tools: dict[str, list[str]] = {}

    def register_tool(
        self,
        name: str,
        tool: ToolProtocol,
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
        schema: dict[str, Any] = tool.schema if hasattr(tool, "schema") else {}  # type: ignore[attr-defined]
        description: str = (
            tool.description if hasattr(tool, "description") else "No description"  # type: ignore[attr-defined]
        )

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
        )

        self._tools[name] = metadata
        if aliases:
            logger.info(
                "Registered tool '%s' with aliases %s (capabilities=%s)",
                name,
                aliases,
                sorted(list(inferred_capabilities)),
            )
        else:
            logger.info(
                "Registered tool '%s' (capabilities=%s)",
                name,
                sorted(list(inferred_capabilities)),
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
            # Handle dict tool config - for now, skip as not implemented
            logger.debug(f"Skipping dict tool config for {agent_name}: {tool}")
            return

        # Support list/tuple of tools (future multi-tool agents)
        if isinstance(tool, (list, tuple)):
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
        capabilities = self._infer_capabilities_from_tool(tool)
        use_cases = self._infer_use_cases_from_tool(tool)

        self.register_tool(
            name=tool_name,
            tool=tool,
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
        # Alias resolution: scan metadata for matching alias
        for m in self._tools.values():
            if name in m.aliases:
                return m
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
            desc += f": {tool.description}"

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
        return [
            tool
            for tool in self._tools.values()
            if capability.lower() in {c.lower() for c in tool.capabilities} and tool.available
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

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> str | None:
        """
        Execute a tool directly.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Arguments to pass to tool.run()

        Returns:
            Tool execution result, or None if tool not found/unavailable
        """
        tool = self._tools.get(tool_name)
        if not tool or not tool.available or not tool.tool_instance:
            return None

        try:
            result = await tool.tool_instance.run(**kwargs)  # type: ignore[attr-defined]
            return str(result)
        except Exception as e:
            return f"Error executing tool {tool_name}: {e!s}"

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

    def _infer_capabilities_from_tool(self, tool: ToolProtocol) -> list[str]:
        """Infer capabilities from tool instance."""
        name = getattr(tool, "name", "") or tool.__class__.__name__
        description = getattr(tool, "description", "") or ""
        return list(self._infer_capabilities(name, description))

    def _infer_use_cases_from_tool(self, tool: ToolProtocol) -> list[str]:
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

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._agent_tools.clear()
