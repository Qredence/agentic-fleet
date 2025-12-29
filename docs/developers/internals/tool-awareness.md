# Tool Awareness System

## Overview

The tool awareness system enables intelligent routing decisions based on available tool capabilities. DSPy modules can see which tools are available to which agents and make routing decisions accordingly.

## Key Components

### Tool Registry

Centralized registry tracking all available tools, their capabilities, and which agents have access to them.

**Features:**

- Multi-tool support per agent
- Automatic capability inference from tool names/descriptions
- Tool aliasing (runtime name + class name)
- Formatted descriptions for DSPy prompts

### Tool Metadata Structure

```python
ToolMetadata(
    name="tavily_search",
    description="Search the web for real-time information...",
    schema={...},
    agent="Researcher",
    tool_instance=<TavilySearchTool object>,
    available=True,
    capabilities={"web_search", "real_time", "citations", "web_access"},
    use_cases=["Finding up-to-date information", ...],
    aliases=["TavilySearchTool"]
)
```

## How It Works

### Tool Registration Flow

```
1. Agent creation (_create_agents)
   ↓
2. Tool extraction (chat_options.tools or fallback)
   ↓
3. Registry population (register_tool_by_agent)
   ↓
4. Metadata inference (capabilities, use cases, aliases)
   ↓
5. Reasoner attachment (set_tool_registry)
   ↓
6. DSPy compilation (with tool visibility)
```

### DSPy Integration

**Tool-Aware Signatures:**

1. **ToolAwareTaskAnalysis**: Receives `available_tools` input field
2. **TaskRouting**: Includes `available_tools` and outputs `tool_requirements`
3. **Reasoner forward()**: Conditionally uses tool-aware analyzer
4. **Reasoner instructions**: Embeds tool catalog in system prompt

**Tool Visibility in Prompts:**

```
Available tools:
- tavily_search | aliases: TavilySearchTool (available to Researcher): Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. [Capabilities: citations, real_time, web_access, web_search] Use cases: Finding up-to-date information, Researching current events, Gathering facts with citations
- HostedCodeInterpreterTool | aliases: HostedCodeInterpreterAdapter (available to Analyst): Execute Python code snippets in an isolated sandbox environment for analysis, data transformation, and quick computation. [Capabilities: code_execution] Use cases: Data analysis and computation, Running Python code, Creating visualizations
```

## Example Tool-Aware Routing

```python
# Task requiring web search → automatically routed to Researcher
await workflow.run("What are the latest AI breakthroughs this week?")
# DSPy sees: TavilySearchTool available to Researcher, routes accordingly

# Task requiring computation → automatically routed to Analyst
await workflow.run("Calculate compound interest for $10,000 at 5% over 10 years")
# DSPy sees: HostedCodeInterpreterTool available to Analyst, routes accordingly

# Task requiring both → sequential routing: Researcher then Analyst
await workflow.run("Find current Bitcoin price and calculate profit from $1000 investment")
# DSPy sees: web_search + code_execution needed, routes sequentially
```

## Tool Capability Inference

The registry automatically infers capabilities from tool names and descriptions:

- Tools with "search" in name/description → `web_search` capability
- Tools with "code" or "interpreter" → `code_execution` capability
- Tavily tools → `web_search`, `real_time`, `citations` capabilities

## Web Search Detection

### Enhanced Detection

The framework includes enhanced web search detection for queries requiring current information:

**When to trigger search:**

- Current events, recent news
- Latest data, future predictions
- Real-time information
- Facts beyond model's training cutoff date
- Keywords: "latest", "current", "recent", "today", specific future dates/years

**Enhanced Signature:**

```python
needs_web_search = dspy.OutputField(
    desc="whether task requires web search (yes/no). Say YES for: current events, recent news, latest data, future predictions, real-time information, facts beyond model's training cutoff date, or when user asks about 'latest', 'current', 'recent', 'today', specific future dates/years"
)
```

**Training Examples:**

The framework includes training examples for current-event detection:

- "Who won the 2025 New York mayoral election?"
- "What is the current stock price of Tesla?"
- "What are the latest developments in quantum computing?"
- "Who is the next mayor of New York in 2026?"
- "What is today's weather in San Francisco?"

## Configuration

Tool awareness can be controlled via `src/agentic_fleet/config/workflow_config.yaml`:

```yaml
tools:
  enable_tool_aware_routing: true # DSPy considers tools (default)
  pre_analysis_tool_usage: true # Use tools in analysis (default)
  tool_registry_cache: true # Cache tool metadata (default)
  tool_usage_tracking: true # Track usage stats (default)
```

**Disabling Tool Awareness:**

```yaml
tools:
  enable_tool_aware_routing: false # DSPy ignores tools when routing
  pre_analysis_tool_usage: false # DSPy doesn't use tools during analysis
```

## Programmatic Access

```python
# View registered tools
print(workflow.tool_registry.get_tool_descriptions())

# Get tools by capability
search_tools = workflow.tool_registry.get_tools_by_capability("web_search")

# Get agent's tools
researcher_tools = workflow.tool_registry.get_agent_tools("Researcher")

# Check tool availability
if workflow.tool_registry.can_execute_tool("tavily_search"):
    result = await workflow.tool_registry.execute_tool(
        "tavily_search", query="Latest AI news"
    )
```

## Edge Cases Handled

- ✅ Agents with no tools (graceful "No tools available" message)
- ✅ Agents with single tool (original pattern)
- ✅ Agents with multiple tools (list/tuple support)
- ✅ Test stubs with `.tools` attribute (fallback path)
- ✅ Missing TAVILY_API_KEY (tool still registers, fails at runtime)
- ✅ Tool aliasing (primary name + class name)
- ✅ Capability inference from name/description

## Implementation Details

### Multi-Tool Support

Enhanced `register_tool_by_agent()` handles list/tuple of tools:

```python
# Single tool (original pattern)
registry.register_tool_by_agent("Researcher", tavily_tool)

# Multiple tools (new support)
registry.register_tool_by_agent("Researcher", [tavily_tool, other_tool])
```

### Backward Compatibility

- Maintains support for single tool instances
- Test stubs continue to work
- Recursive registration for collections

### Reasoner Instructions

The reasoner's system prompt includes a live tool catalog:

```
Available tools:
- Tool descriptions with capabilities
- Agent assignments
- Use case guidance
```

## Results

### Before Integration

- Tool registry count: **0**
- DSPy analysis: No tool visibility
- Routing: Tool-blind decisions
- Reasoner instructions: Generic team list only

### After Integration

- Tool registry count: **2** (tavily_search, HostedCodeInterpreterTool)
- DSPy analysis: Full tool descriptions with capabilities and use cases
- Routing: Tool-aware decisions with explicit `tool_requirements`
- Reasoner instructions: Rich tool catalog with guidance

## Known Limitations

The `_perform_web_search` method in `reasoner.py` currently tries to execute async tools in a sync context, which may fail silently. The **detection works perfectly** (needs_web_search=True), but actual search execution during the analysis phase may not complete.

**Workaround**: The search will still be executed during agent execution phase when the Researcher agent runs, as the routing correctly assigns the task to the Researcher with TavilySearchTool.

## Future Enhancements

1. **Telemetry**: Surface `tool_requirements` in execution events for richer runtime telemetry
2. **Config-driven tools**: Allow tool list configuration in YAML instead of hard-coded
3. **Tool retry logic**: Add backoff/retry when tool invocations fail
4. **Tool usage analytics**: Track which tools are most effective for different task types
5. **Dynamic tool loading**: Load tools from plugins/extensions at runtime
6. **Fix async tool execution**: Update `_perform_web_search` to properly handle async tools in sync context

## Related Documentation

- [User Guide](../../users/user-guide.md) - Tool integration usage patterns
- [Configuration](../../users/configuration.md) - Tool configuration options
- [API Reference](../api-reference.md) - ToolRegistry API details
