# AI Agent Instructions for AgenticFleet

## Project Overview

AgenticFleet is a multi-agent orchestration system built on **Microsoft Agent Framework 1.0.0b251007**. It implements the **Magentic workflow pattern** where an Orchestrator delegates tasks to specialized agents (Researcher, Coder, Analyst). Each agent has dedicated tools returning **Pydantic-modeled structured responses** via the **OpenAI Responses API**.

**Critical Architecture**: This is NOT a simple LLM app—it's a framework-coordinated multi-agent system with specific delegation patterns, event streaming, and execution limits enforced by `MagenticBuilder`.

## Essential Commands (ALWAYS use `uv`)

```bash
# Install/sync dependencies
uv sync

# Run application
uv run python main.py

# Validate configuration
uv run python test_config.py

# Run tests with filters
uv run pytest -k researcher

# Format and lint (REQUIRED before commits)
uv run black .
uv run ruff check .
uv run mypy agents config
```

**Never use `pip` or plain `python`—always prefix with `uv run` or work in activated venv.**

## Agent Factory Pattern (Non-Negotiable Structure)

Each agent follows this exact structure at `agents/<role>/`:

```
<role>_agent/
├── __init__.py                    # Exports create_<role>_agent
├── agent.py                       # Factory: create_<role>_agent() -> ChatAgent
├── agent_config.yaml              # model, temperature, system_prompt, tools config
└── tools/                         # Optional tool implementations
    ├── __init__.py
    └── <tool_name>.py             # Functions returning Pydantic models
```

**Factory Function Pattern** (`agent.py`):
```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from config.settings import settings

def create_<role>_agent() -> ChatAgent:
    config = settings.load_agent_config("agents/<role>_agent")
    agent_config = config.get("agent", {})
    
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )
    
    # Import tools conditionally based on config
    enabled_tools = []
    for tool_config in config.get("tools", []):
        if tool_config.get("enabled", True):
            # Import and append tool function
            pass
    
    return ChatAgent(
        name=agent_config.get("name", "<role>"),
        instructions=config.get("system_prompt", ""),
        chat_client=client,
        tools=enabled_tools,  # List of functions, NOT ToolSet
    )
```

**Key Details**:
- Tools are **passed as a list of functions**, not wrapped in containers
- `system_prompt` comes from YAML `system_prompt:` key, not `agent.instructions`
- Load config via `settings.load_agent_config()`, never direct YAML reads
- Temperature is agent-specific: Orchestrator=0.1, Coder/Analyst=0.2, Researcher=0.3

## Tool Implementation Pattern (Pydantic-First)

All tools **must** return Pydantic models for structured responses:

```python
from pydantic import BaseModel, Field

class ToolResponse(BaseModel):
    """Structured output with explicit fields."""
    result: str = Field(..., description="Primary result")
    metadata: dict = Field(default_factory=dict, description="Additional context")

def my_tool(param: str) -> ToolResponse:
    """
    Brief tool description for LLM function calling.
    
    Args:
        param: Description of parameter
        
    Returns:
        ToolResponse: Structured result
    """
    # Implementation
    return ToolResponse(result="...", metadata={})
```

**Why**: OpenAI Responses API requires structured outputs. Models auto-generate JSON schemas.

**Phase 1 Note**: Web search and data analysis tools return **mock data**. Replace with real APIs in Phase 2, but keep the Pydantic model structure unchanged.

## Workflow Coordination (workflows/magentic_workflow.py)

The workflow is the system's **brain**—modifying it impacts all agents:

```python
workflow = (
    MagenticBuilder()
    .participants(
        orchestrator=create_orchestrator_agent(),  # Names are stable IDs
        researcher=create_researcher_agent(),
        coder=create_coder_agent(),
        analyst=create_analyst_agent(),
    )
    .on_event(on_event)  # Event streaming for observability
    .with_standard_manager(
        chat_client=OpenAIResponsesClient(model_id=settings.openai_model),
        max_round_count=10,  # From config/workflow_config.yaml
        max_stall_count=3,
        max_reset_count=2,
    )
    .build()
)
```

**Critical**:
- Participant names (`orchestrator`, `researcher`, etc.) are used for delegation—changing them breaks agent coordination
- `on_event()` handler is the **only** place to add observability/logging without agent framework conflicts
- Execution limits prevent infinite loops but may need tuning for complex tasks

## Configuration Hierarchy

1. **Environment** (`.env`): `OPENAI_API_KEY`, `OPENAI_MODEL` (never commit)
2. **Workflow** (`config/workflow_config.yaml`): Shared execution limits (`max_rounds`, `max_stalls`)
3. **Agent-Specific** (`agents/*/agent_config.yaml`): Per-agent `model`, `temperature`, `system_prompt`, `tools`

**Load with**: `settings.load_agent_config("agents/<role>_agent")` for agent configs, `settings.workflow_config` for workflow config.

**When to modify**:
- Workflow limits: Performance tuning or handling complex multi-step tasks
- Agent temperature: Balancing creativity (higher) vs determinism (lower)
- System prompts: Adjusting agent behavior, delegation rules, or response style

## Testing Strategy

**Always run `python test_config.py` after**:
- Adding/modifying agent configs
- Creating new tools
- Changing workflow parameters
- Environment changes

**For new tools/agents**:
```python
# Add to test_config.py
def test_new_tool_import():
    from agents.new_agent.tools.new_tool import new_tool_function
    assert callable(new_tool_function)
```

**Mock API clients** in real tests to avoid costs:
```python
from unittest.mock import patch

@patch('agent_framework.openai.OpenAIResponsesClient')
def test_agent_creation(mock_client):
    agent = create_my_agent()
    assert agent.name == "my_agent"
```

## Code Style Enforcement

- **Line length**: 100 chars (Black + Ruff configured in `pyproject.toml`)
- **Docstrings**: Google style (see `agents/coder_agent/agent_config.yaml` reference)
- **Naming**: `create_<role>_agent()` for factories, `<action>_tool()` for tools, `snake_case` for YAML keys
- **YAML**: Never use tabs, always 2-space indents

**Pre-commit checklist**:
```bash
uv run black .      # Auto-format
uv run ruff check . # Catch issues
uv run mypy agents config  # Type checking
uv run python test_config.py  # Validate configs
```

## Common Pitfalls

1. **"ModuleNotFoundError for agents"**: You're not in project root or venv isn't active. Run `source .venv/bin/activate` from AgenticFleet directory.

2. **"OPENAI_API_KEY not found"**: Copy `.env.example` to `.env` and add your key. `settings.py` raises ValueError if missing.

3. **Agent delegation not working**: Check `system_prompt` in orchestrator's `agent_config.yaml` includes correct agent names (`researcher`, `coder`, `analyst`) and delegation_rules.

4. **Tool not called by agent**: Verify tool is listed in agent's `tools` config and `enabled: true`. Check function signature matches OpenAI function calling requirements.

5. **Workflow stalls**: Increase `max_stalls` in `config/workflow_config.yaml` or improve agent prompts to be more directive.

## Adding New Agents

1. Create directory structure: `agents/new_agent/{__init__.py,agent.py,agent_config.yaml,tools/}`
2. Implement factory following pattern above
3. Register in workflow: `.participants(new_agent=create_new_agent(), ...)`
4. Update orchestrator's `system_prompt` to include new agent in delegation rules
5. Add tests to `test_config.py`

## Adding New Tools

1. Define Pydantic response model first
2. Implement function with docstring (LLM reads this for function calling)
3. Add to agent's `tools/` directory
4. Enable in agent's `agent_config.yaml` under `tools: [{name: "tool_name", enabled: true}]`
5. Import and append conditionally in agent factory
6. Test with `python test_config.py` and manual run

## Phase 1 vs Phase 2 Considerations

**Current (Phase 1)**: Mock tools, Python-only code execution, no persistence
**Planned (Phase 2)**: Real APIs, multi-language support, conversation history, Docker deployment

**When modifying tools**: Keep Pydantic model structure—swap implementation under the hood. Agent code shouldn't need changes when switching from mock to real APIs.

## Documentation Standards

- **Modules**: Docstring at top explaining purpose, key classes/functions
- **Functions**: Google-style with Args, Returns, Raises
- **Agents**: `system_prompt` in YAML is self-documentation—keep it updated
- **Configs**: Inline YAML comments for non-obvious settings

## Debugging Workflow Issues

1. Check event stream: `on_event()` in `workflows/magentic_workflow.py` logs all interactions
2. Validate configs: `uv run python test_config.py`
3. Test agent in isolation: `uv run python -c "from agents.researcher_agent.agent import create_researcher_agent; create_researcher_agent()"`
4. Enable verbose logging: Add `import logging; logging.basicConfig(level=logging.DEBUG)` in `main.py`

## Key Files to Know

- `main.py`: Entry point with REPL loop—modify for new UIs
- `config/settings.py`: Single source of truth for config loading—extend here
- `workflows/magentic_workflow.py`: Multi-agent coordination—changes affect all agents
- `agents/orchestrator_agent/agent_config.yaml`: Delegation rules—update when adding agents
- `pyproject.toml`: Dependencies and tool configs—sync after changes with `uv sync`

---

**When in doubt**: Run `uv run python test_config.py` first. It validates the entire configuration chain and imports all agents/tools. If tests pass but execution fails, issue is likely in agent prompts or delegation logic, not code structure.
