# AI Agent Instructions for AgenticFleet

## Project Overview

AgenticFleet is a **multi-agent orchestration system** built on Microsoft Agent Framework (official Python SDK). It implements a **sequential coordination pattern** where an Orchestrator agent delegates tasks to specialized agents (Researcher, Coder, Analyst). Each agent is a `ChatAgent` instance with dedicated tools that return **Pydantic-modeled structured responses**.

**Critical Architecture Note**: This uses the official Microsoft Agent Framework Python implementation (`ChatAgent` + `OpenAIResponsesClient`)—NOT Azure AI Foundry's `AgentsClient` or .NET's `MagenticBuilder`.

### Agent Specializations & Configuration

| Agent            | Temperature | Model       | Tools                                                 | Purpose                                     |
| ---------------- | ----------- | ----------- | ----------------------------------------------------- | ------------------------------------------- |
| **Orchestrator** | 0.1         | gpt-5       | None                                                  | Task planning, delegation, result synthesis |
| **Researcher**   | 0.3         | gpt-4o      | `web_search_tool`                                     | Information gathering, web research         |
| **Coder**        | 0.2         | gpt-5-codex | `code_interpreter_tool`                               | Code writing, execution, debugging          |
| **Analyst**      | 0.2         | gpt-4o      | `data_analysis_tool`, `visualization_suggestion_tool` | Data analysis, insights                     |

**Temperature rationale**: Lower = deterministic (orchestration, code), Higher = creative (research synthesis)

## Essential Commands (ALWAYS use `uv`)

```bash
# Install/sync dependencies - run this first
uv sync

# Validate configuration before running (checks .env, YAML configs, imports)
uv run python test_config.py    # Must pass 6/6 tests

# Run application
uv run python main.py

# Format and lint (REQUIRED before commits)
uv run black .
uv run ruff check .

# Quick agent factory validation (smoke test)
uv run python -c "from agents.orchestrator_agent.agent import create_orchestrator_agent; create_orchestrator_agent()"
```

**⚠️ CRITICAL**: Never use `pip` or plain `python`—always prefix with `uv run` or activate `.venv` first. This ensures dependency isolation and correct Python version (3.12+).

## Official Framework APIs Reference

### ❌ DO NOT USE (Wrong SDK or non-existent)

- `MagenticBuilder()` — .NET only, not in Python
- `from agent_framework.core import ChatAgent` — wrong import path
- `from azure.ai.agents import AgentsClient` — separate Azure AI SDK
- `context_provider=` parameter on ChatAgent — not in official API
- `OpenAIChatClient` — deprecated for this use case

### ✅ CORRECT PATTERNS (Official Python Agent Framework)

```python
# Agent creation pattern (see agents/*/agent.py for examples)
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

client = OpenAIResponsesClient(
    model_id="gpt-4o"  # model_id is the only required param
)

agent = ChatAgent(
    chat_client=client,
    instructions="Your system prompt here",
    name="agent_name",
    temperature=0.2,              # Optional
    tools=[function1, function2]  # Plain Python functions
)

# Execution
result = await agent.run("user query")
response_text = result.content if hasattr(result, "content") else str(result)
```

**Key points**:

- `OpenAIResponsesClient` (not `OpenAIChatClient`) for structured responses
- Tools are **plain Python functions** with type hints (auto-converted to tool schemas)
- `OPENAI_API_KEY` must be in environment (`.env` file)
- Temperature can be set on agent or overridden per-call

## Configuration Architecture

### Two-Tier Config Pattern

1. **Workflow-level** (`config/workflow_config.yaml`): Execution limits shared across all agents

   ```yaml
   workflow:
     max_rounds: 10 # Max orchestration cycles
     max_stalls: 3 # Max identical responses before abort
     timeout_seconds: 300 # Overall task timeout
   ```

2. **Agent-level** (`agents/*/agent_config.yaml`): Agent-specific behavior
   ```yaml
   agent:
     name: "researcher"
     model: "gpt-4o"
     temperature: 0.3
   system_prompt: |
     Your instructions with {memory} placeholder
   tools:
     - name: "web_search_tool"
       enabled: true
   ```

**Loading pattern** (see `config/settings.py`):

```python
from config.settings import settings

# Workflow config
max_rounds = settings.workflow_config.get("workflow", {}).get("max_rounds", 10)

# Agent-specific config
config = settings.load_agent_config("agents/researcher_agent")
model = config["agent"]["model"]
```

## Tool Development Pattern

All tools return **Pydantic models** for type safety. Example structure:

```python
# In agents/*/tools/*.py
from pydantic import BaseModel, Field

class ToolResponse(BaseModel):
    """Response schema with validation."""
    field1: str = Field(..., description="Purpose")
    field2: float = Field(..., description="Metric")

def my_tool(query: str) -> ToolResponse:
    """
    Tool description for LLM function calling.

    Args:
        query: User input description

    Returns:
        ToolResponse: Structured result
    """
    # Implementation
    return ToolResponse(field1="result", field2=0.95)
```

**Enable in agent config**:

```yaml
tools:
  - name: "my_tool"
    enabled: true
    max_results: 10 # Tool-specific params
```

**Register in agent factory** (`agents/*/agent.py`):

```python
from .tools.my_tools import my_tool

enabled_tools = []
for tool_config in config.get("tools", []):
    if tool_config.get("name") == "my_tool" and tool_config.get("enabled", True):
        enabled_tools.append(my_tool)

return ChatAgent(..., tools=enabled_tools)
```

## Workflow Orchestration Pattern

The workflow (`workflows/magentic_workflow.py`) implements **sequential delegation**:

1. User input → Orchestrator analyzes request
2. Orchestrator decides: provide answer OR delegate to specialist
3. Specialist executes task with tools, returns result
4. Orchestrator synthesizes final response or continues iteration

**Delegation protocol** (parsed from orchestrator response):

```
DELEGATE: <agent_name> - <task_description>
```

**Termination conditions**:

- Orchestrator provides `FINAL_ANSWER:` prefix
- `max_rounds` reached (configured in `workflow_config.yaml`)
- `max_stalls` identical responses (anti-loop protection)

## Critical Error Patterns & Fixes

### Issue 1: Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'agent_framework'`
**Fix**: Run `uv sync` and verify `.venv` activated

### Issue 2: API Key Missing

**Symptom**: `ValueError: OPENAI_API_KEY environment variable is required`
**Fix**: Create `.env` from `.env.example` and add valid OpenAI key

### Issue 3: YAML Parse Errors

**Symptom**: `yaml.scanner.ScannerError` during config load
**Fix**: Validate YAML syntax with `python -c "import yaml; yaml.safe_load(open('path/to/file.yaml'))"`

### Issue 4: Agent Factory Fails

**Symptom**: `FileNotFoundError: agent_config.yaml`
**Fix**: Ensure `agent_config.yaml` exists in `agents/<role>/` directory

**Always run `uv run python test_config.py` first** — it validates all common issues (6 test categories).

## File Organization Rules

```
agents/<role>/
├── __init__.py              # Exports factory function
├── agent.py                 # Factory: create_<role>_agent()
├── agent_config.yaml        # Role-specific config
└── tools/
    ├── __init__.py
    └── <tool_name>.py       # Pydantic models + functions
```

**Naming conventions**:

- Factories: `create_<role>_agent()` (imperative, returns `ChatAgent`)
- Tools: `<action>_tool(args) -> PydanticModel` (descriptive function name)
- Config files: snake_case keys (`max_rounds`, `analysis_types`)
- Models: PascalCase (`WebSearchResponse`, `CodeExecutionResult`)

## Testing & Validation Strategy

### Pre-Commit Checks

```bash
uv run python test_config.py  # Validates env, configs, imports, factories
uv run black .                # Format code
uv run ruff check .           # Lint (100-char limit, Python 3.12 target)
```

### Configuration Test Categories (from `test_config.py`)

1. Environment (`.env` file, `OPENAI_API_KEY`)
2. Workflow config (`max_rounds`, `max_stalls`, `max_resets`)
3. Agent configs (all 4 agents: name, model, temperature)
4. Tool imports (all 4 tools can be imported)
5. Agent factories (all 4 factories are callable)
6. Workflow import (`MultiAgentWorkflow` instantiates)

**All must pass** before deployment.

## Mem0 Context Provider Integration

**Purpose**: Persistent memory across conversations using Azure AI Search vector store.

**Configuration** (see `context_provider/mem0_context_provider.py`):

```python
from context_provider.mem0_context_provider import Mem0ContextProvider

provider = Mem0ContextProvider()  # Auto-configures from settings

# Usage in workflow
memory_context = provider.get(user_query)
provider.add(agent_response)
```

**Required environment variables** (in `.env`):

```bash
AZURE_AI_PROJECT_ENDPOINT=your-azure-endpoint
AZURE_AI_SEARCH_ENDPOINT=your-search-endpoint
AZURE_AI_SEARCH_KEY=your-search-key
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME=text-embedding-ada-002
```

**System prompts** use `{memory}` placeholder (replaced at runtime).

## Common Workflow Patterns

### Adding a New Agent

1. Create directory: `agents/new_agent/`
2. Add `agent_config.yaml` with `agent`, `system_prompt`, `tools` sections
3. Create `agent.py` with `create_new_agent()` factory
4. Implement tools in `agents/new_agent/tools/`
5. Register in `workflows/magentic_workflow.py`
6. Add tests in `test_config.py`

### Adding a New Tool

1. Define Pydantic response model in `agents/<role>/tools/<tool_name>.py`
2. Implement function: `def my_tool(args) -> MyToolResponse:`
3. Enable in `agents/<role>/agent_config.yaml` tools list
4. Register in `agents/<role>/agent.py` factory tool loading logic
5. Document in agent's system prompt

### Debugging Workflow Stalls

**Symptom**: Workflow exits with "Workflow stalled after X identical responses"
**Cause**: Orchestrator returning same text repeatedly (potential loop)
**Fix**:

- Check orchestrator system prompt for clear termination instructions
- Verify `FINAL_ANSWER:` or `DELEGATE:` prefixes in responses
- Review `max_stalls` in `workflow_config.yaml` (default: 3)

## Documentation References

- **Architecture overview**: `README.md`
- **Agent conventions**: `docs/AGENTS.md`
- **Implementation status**: `docs/IMPLEMENTATION_SUMMARY.md`
- **Mem0 integration**: `docs/MEM0_INTEGRATION.md`
- **Bug fixes history**: `docs/FIXES.md`
- **Quick reference**: `docs/QUICK_REFERENCE.md`

## Framework Documentation

- **Official SDK**: [Microsoft Agent Framework Python](https://learn.microsoft.com/en-us/agent-framework/)
- **Examples**: [GitHub microsoft/agent-framework/python/examples](https://github.com/microsoft/agent-framework/tree/main/python/examples)
