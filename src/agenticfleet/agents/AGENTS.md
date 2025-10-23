# AGENTS.md – Agents Layer

> Agent-focused operational reference for `src/agenticfleet/agents/`. Use this when adding, modifying, or auditing agents and their tools. Complements root `AGENTS.md` and `src/agenticfleet/AGENTS.md` (package-wide view).

---

## 1. Purpose

The `agents/` directory houses **specialized role agents** participating in Magentic workflows (planner/orchestrator + executors). Agents are thin factories binding:

- Declarative YAML config (model, system prompt, tools, runtime flags)
- `OpenAIResponsesClient` (or future compatible client)
- Tool call list (validated at startup)

No business logic, heuristics, or model IDs should be hardcoded here. Everything dynamic must flow from YAML → factory wiring.

---

## 2. Directory Layout

```
agents/
├── __init__.py            # Re-exports create_<role>_agent factories
├── base.py                # (If present) shared base helpers
├── orchestrator/          # Manager / planner agent
├── researcher/            # Web and info retrieval specialist
├── coder/                 # Code interpreter + generation specialist
├── analyst/               # Data analysis / visualization specialist
└── browser-agent/         # (Experimental) browser automation / navigation (if enabled)
```

Each role folder typically contains:

```
<role>/
├── agent.py               # Factory function: create_<role>_agent()
├── config.yaml            # Declarative config (authoritative)
└── tools/                 # Tool implementation modules (Pydantic return types)
```

---

## 3. YAML Configuration Schema (Per-Agent)

Minimal required keys:

```yaml
name: "Researcher Agent"
model: "gpt-5" # NEVER override in Python
system_prompt: |
  You are a specialist...
temperature: 0.3
max_tokens: 4000
runtime:
  stream: true
  checkpoint: true
  store: false
  # Additional runtime flags allowed (do not assume exhaustive list)
tools:
  - name: web_search_tool
    enabled: true
```

**Rules:**

- Omit unused keys rather than leaving empty stubs.
- Removal of a tool from config must also remove references in `system_prompt`.
- If a tool is disabled (`enabled: false`) keep it documented in prompt ONLY if agent should still conceptually know it exists (rare).

---

## 4. Agent Factory Pattern

Canonical structure (simplified):

```python
from agenticfleet.config.settings import settings
from agent_framework import ChatAgent
from agent_framework_azure_ai import OpenAIResponsesClient
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

def create_researcher_agent() -> ChatAgent:
    config = settings.load_agent_config("researcher")

    client = OpenAIResponsesClient(model_id=config["model"])  # DO NOT hardcode

    tools = []
    for tool in config.get("tools", []):
        if tool.get("enabled"):
            # Import lazily to avoid circulars
            if tool["name"] == "web_search_tool":
                from .tools.web_search_tool import web_search_tool
                tools.append(web_search_tool)
            else:
                logger.warning("Unknown tool declared", extra={"tool": tool["name"]})

    return ChatAgent(
        name=config["name"],
        model_client=client,
        system_message=config["system_prompt"],
        tools=tools,
    )
```

**Anti-patterns:**

- ❌ Hardcoding model: `OpenAIResponsesClient(model_id="gpt-4o")`
- ❌ Mutating YAML-derived values (e.g., appending to prompt)
- ❌ Registering tools not declared in YAML

---

## 5. Tool Implementation Contract

All tools MUST:

| Requirement           | Description                                                                |
| --------------------- | -------------------------------------------------------------------------- |
| Pydantic return       | Use types from `agenticfleet.core.code_types` or add new model there first |
| Pure function surface | Deterministic signature; side-effects require HITL approval wrappers       |
| Type hints            | All params + return annotated (Py312 syntax)                               |
| Error capture         | Return `success=False` with `error` set; never raise unhandled exceptions  |
| Docstring             | One-liner + arg/return semantics                                           |

Example (mock search tool):

```python
from agenticfleet.core.code_types import WebSearchResponse, WebSearchResult

def web_search_tool(query: str, limit: int = 5) -> WebSearchResponse:
    """Return mock search results for a query (deterministic)."""
    try:
        results = [
            WebSearchResult(title=f"Result {i+1}", url=f"https://example.com/{i+1}", snippet=f"Snippet for {query}")
            for i in range(limit)
        ]
        return WebSearchResponse(success=True, results=results, message=f"Returned {len(results)} results")
    except Exception as e:
        return WebSearchResponse(success=False, results=[], error=str(e))
```

---

## 6. HITL (Human-in-the-Loop) Integration

Sensitive tools (code exec, file ops, network with side-effects) must:

1. Construct an `ApprovalRequest` (operation_type must match workflow config list)
2. Await handler response (`ApprovalDecision.APPROVE | REJECT | MODIFY`)
3. If MODIFY, replace original payload with `modified_data`
4. Abort cleanly if REJECT

Never bypass or silently proceed on timeout—delegate fallback policy to handler implementation.

---

## 7. Adding a New Agent (Checklist)

| Step | Action                            | Command / Notes                            |
| ---- | --------------------------------- | ------------------------------------------ |
| 1    | Scaffold directory                | `mkdir -p agents/<role>/tools`             |
| 2    | Create `config.yaml`              | Copy template; fill prompt & model         |
| 3    | Implement `agent.py`              | `create_<role>_agent()` factory            |
| 4    | Add tools (if any)                | Each returns Pydantic model                |
| 5    | Export factory                    | Update `agents/__init__.py`                |
| 6    | Register in fleet builder         | Modify `fleet/fleet_builder.py`            |
| 7    | Update manager instructions       | Edit `config/workflow.yaml` manager prompt |
| 8    | Add config tests                  | Extend `tests/test_config.py` assertions   |
| 9    | Run validation                    | `make test-config`                         |
| 10   | Add orchestration test (optional) | `tests/test_magentic_fleet.py`             |

---

## 8. Adding a New Tool (Checklist)

| Step | Action                                                  |
| ---- | ------------------------------------------------------- |
| 1    | Define Pydantic return (if new) in `core/code_types.py` |
| 2    | Implement function in `agents/<role>/tools/<name>.py`   |
| 3    | Add entry to role `config.yaml` under `tools` list      |
| 4    | Reference tool usage in `system_prompt` contextually    |
| 5    | Write unit test (mock external calls)                   |
| 6    | Run `make test-config` (ensures importability)          |
| 7    | Run focused tests: `uv run pytest -k <tool_name>`       |

---

## 9. Runtime Flags (YAML `runtime:` Block)

| Flag         | Purpose                                  | Typical Value             |
| ------------ | ---------------------------------------- | ------------------------- |
| `stream`     | Enable token streaming feedback          | `true`                    |
| `checkpoint` | Persist intermediate state               | `true` for long workflows |
| `store`      | Persist conversation transcript (future) | `false`                   |

Avoid adding experimental flags unless also supported in orchestration layer.

---

## 10. Common Failure Modes

| Symptom                 | Likely Cause                     | Resolution                                              |
| ----------------------- | -------------------------------- | ------------------------------------------------------- |
| Tool not executed       | Not enabled in YAML              | Ensure `enabled: true` present                          |
| Model mismatch warnings | Hardcoded model in agent factory | Read model from config only                             |
| Schema parse errors     | Tool return shape changed        | Sync with `core/code_types.py` and update all consumers |
| Approval never arrives  | Operation type mismatch          | Align `operation_type` string with workflow config      |
| Infinite plan loop      | Manager lacking new info         | Improve tool output metadata or adjust prompt           |

---

## 11. Testing Agents Quickly

```bash
# Validate config & factory importability
make test-config

# Run only agent orchestration tests
uv run pytest tests/test_magentic_fleet.py -k agent -v

# Focus on one factory
grep -n "create_researcher_agent" -R .
```

---

## 12. Logging & Telemetry

- Use `get_logger(__name__)` from `core.logging`
- Avoid logging sensitive tool payloads (unless guarded by env)
- Tool start/stop often surfaced via callbacks—avoid duplicate noisy logs

---

## 13. Extension Patterns

| Goal                  | Approach                                                                 |
| --------------------- | ------------------------------------------------------------------------ |
| Multi-modal agent     | Add tools returning structured image/vision models (extend `code_types`) |
| Cost-aware agent      | Inject token accounting tool + planner heuristics (external)             |
| Memory-augmented role | Query `mem0_provider` before acting; update prompt template              |
| Auditable agent       | Add tool usage summary append step in manager evaluation                 |

---

## 14. Do / Don't Summary

| ✅ Do                             | ❌ Don't                           |
| --------------------------------- | ---------------------------------- |
| Load all dynamic values from YAML | Hardcode model IDs                 |
| Return Pydantic models            | Return bare dicts/lists            |
| Gate sensitive ops with approval  | Execute code directly              |
| Add tests for each new tool       | Rely on manual runtime validation  |
| Keep factories minimal            | Embed planning logic inside agents |

---

## 15. Quick Scaffold Snippet

```bash
role=newrole
mkdir -p agents/$role/tools
cat > agents/$role/config.yaml <<'YAML'
name: "${role^} Agent"
model: gpt-5
system_prompt: |
  You are the $role specialist.
runtime:
  stream: true
  checkpoint: true
tools: []
YAML
cat > agents/$role/agent.py <<'PY'
from agenticfleet.config.settings import settings
from agent_framework import ChatAgent
from agent_framework_azure_ai import OpenAIResponsesClient

def create_${role}_agent() -> ChatAgent:
    config = settings.load_agent_config("$role")
    client = OpenAIResponsesClient(model_id=config["model"])
    return ChatAgent(
        name=config["name"],
        model_client=client,
        system_message=config["system_prompt"],
        tools=[],
    )
PY
```

---

## 16. Maintenance Checklist

| Task                      | Frequency                      | Command                      |
| ------------------------- | ------------------------------ | ---------------------------- |
| Validate configs          | After any YAML change          | `make test-config`           |
| Review tool schemas       | Adding/changing tools          | Inspect `core/code_types.py` |
| Sync prompts with toolset | After enabling/disabling tools | Manual diff prompt vs config |
| Check for drift (models)  | Weekly / before release        | Search for `model_id="`      |

---

## 17. References

- Root: `../../AGENTS.md`
- Package: `../AGENTS.md`
- Workflow builder: `../fleet/fleet_builder.py`
- Code types: `../core/code_types.py`
- HITL: `../core/approval.py`
- Memory: `../context/mem0_provider.py`

---

**End – Agents Layer AGENTS.md**
