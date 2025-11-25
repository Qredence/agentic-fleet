# AgenticFleet Code Quality Improvement Plan

This document tracks planned code quality improvements identified during codebase analysis.

---

## 🔴 High Priority

### 1. Pydantic V2 Config Migration

**Status**: ✅ Completed
**Files**: `src/agentic_fleet/api/schemas/chat.py`
**Issue**: Using deprecated `class Config` pattern that will break in Pydantic V3.
**Resolution**: Migrated to `model_config = ConfigDict(from_attributes=True)` pattern.

### 2. Missing Async Generator Return Types

**Status**: ✅ Completed
**Files**:

- `src/agentic_fleet/workflows/supervisor.py` (line 303)

**Resolution**: Added `AsyncIterator[WorkflowEvent]` return type and defined `WorkflowEvent` type alias.

### 3. Broad Exception Handling

**Status**: ⚠️ Partially Complete (Documentation Added)
**Files**: ~10 files with `except Exception:` blocks

**Analysis**: The broad exception handling in this codebase is largely **intentional** - it implements a graceful degradation pattern where LLM/DSPy operations that fail for transient reasons (rate limits, network issues, model errors) fall back to heuristic-based alternatives.

**Changes Made**:

- Added documentation comments to all executor exception handlers in `executors.py` explaining the graceful degradation pattern
- Comments clarify that broad exception handling is intentional for system availability

**Remaining Work** (Optional - Low Priority):

- Consider adding structured logging fields for exception types
- Add telemetry/metrics for fallback rate tracking

---

## 🟡 Medium Priority

### 4. Centralize Environment Variable Access

**Status**: ✅ Completed
**Files**:

- `src/agentic_fleet/utils/env.py` (enhanced with `EnvConfig` class and typed helpers)
- `src/agentic_fleet/agents/coordinator.py`
- `src/agentic_fleet/utils/logger.py`
- `src/agentic_fleet/cli/utils.py`
- `src/agentic_fleet/cli/commands/agents.py`
- `src/agentic_fleet/tools/tavily_tool.py`
- `tests/utils/test_logger.py`

**Issue**: Scattered `os.getenv()` calls throughout the codebase with inconsistent defaults and no type safety.
**Resolution**:

- Added `EnvConfig` class with cached, typed properties for all common env vars
- Added `get_env_bool()`, `get_env_int()`, `get_env_float()` helper functions
- Migrated key files to use `env_config` singleton instead of direct `os.getenv()`
- Added `clear_cache()` method for testing scenarios

### 5. Deduplicate `_call_with_retry` Implementations

**Status**: ✅ Completed
**Files**:

- `src/agentic_fleet/utils/resilience.py` (new `async_call_with_retry` function)
- `src/agentic_fleet/workflows/executors.py` (4 methods removed)

**Issue**: Four nearly identical `_call_with_retry` methods in `AnalysisExecutor`, `RoutingExecutor`, `ProgressExecutor`, and `QualityExecutor`.
**Resolution**: Created shared `async_call_with_retry` utility in `resilience.py` using PEP 695 type parameters. All 4 executor methods now use the shared utility with config-driven retry parameters.

### 6. Add Missing Test Coverage

**Status**: 🔲 Not Started
**Priority Files** (DSPy integration tests first—that's where custom logic lives):

1. `src/agentic_fleet/dspy_modules/reasoner.py` (DSPy signatures) — **highest priority**
2. `src/agentic_fleet/agents/base.py` (DSPyEnhancedAgent) — **high priority**
3. `src/agentic_fleet/workflows/executors.py` (6 executor classes)
4. `src/agentic_fleet/utils/resilience.py` (retry logic)

**Approach**: Mock DSPy/LLM calls, test fallback paths, validate typed outputs. Focus on DSPy integration tests since that's where custom logic lives—native edge patterns are already tested upstream.

### 7. Reduce `Any` Type Usage

**Status**: ✅ Completed
**Changes Made**:

- Replaced `dict[str, Any]` with `dict[str, ChatAgent]` for agent dictionaries across workflow files:
  - `workflows/strategies.py` — All execution functions now use typed agent dicts
  - `workflows/helpers.py` — `get_quality_criteria()` and `refine_results()` typed
  - `workflows/context.py` — `SupervisorContext.agents` and `workflow` properly typed
  - `workflows/supervisor.py` — `SupervisorWorkflow.__init__` agents parameter typed
  - `workflows/compilation.py` — `compile_supervisor_async()` agents parameter typed
- Replaced `Any` with `MagenticAgentMessageEvent` in `workflows/execution/streaming_events.py`
- Added `TYPE_CHECKING` imports for `ChatAgent`, `Workflow`, `DSPyReasoner` to avoid circular imports

**Remaining `Any` Usage** (Intentional):

- Exception classes with arbitrary config values (`config_value: Any`, `value: Any`)
- `**_: Any` for ignored kwargs patterns
- `_extract_tool_usage(response: Any)` — responses from diverse agent types
- Loop accumulators that hold mixed types during iteration

---

## 🟢 Low Priority

### 8. Extract Magic Numbers to Configuration

**Status**: ✅ Completed
**Changes Made**:

- Added browser-specific constants (`DEFAULT_BROWSER_TIMEOUT_MS`, `DEFAULT_BROWSER_SELECTOR_TIMEOUT_MS`, `DEFAULT_BROWSER_MAX_TEXT_LENGTH`) to `constants.py`
- Updated `browser_tool.py` to use centralized constants
- Most magic numbers were already centralized in `constants.py`

### 9. Address TODO Comments

**Status**: ✅ Completed
**Changes Made**:

- Converted the single TODO comment in `api/routes/chat.py` to an actionable NOTE explaining:
  - Current stateless workflow behavior
  - Steps needed for future multi-turn conversation support
  - Integration points with `PersistenceManager` and `SupervisorContext`

### 10. Standardize Docstring Format

**Status**: ✅ Completed
**Format**: Google-style docstrings (Args/Returns/Raises/Example sections)

**Files Updated**:

- `src/agentic_fleet/workflows/helpers.py` — Added comprehensive docstrings to routing/quality helpers (`_fallback_analysis`, `_to_analysis_result`, `_is_simple_task`, `_fallback_routing`)
- `src/agentic_fleet/workflows/executors.py` — Added docstrings to `handler` decorator, `_run_judge_phase`, and conversion helpers
- `src/agentic_fleet/workflows/handoff.py` — Added docstrings to private helpers (`_sup`, `_count_handoff_pairs`, `_calculate_avg_handoffs`, `_get_common_handoffs`, `_get_effort_distribution`)
- `src/agentic_fleet/agents/base.py` — Enhanced docstrings for `tools` property, `_get_agent_role_description`, `_build_pot_error_note`, `_apply_note_to_text`, `_create_timeout_response`

**Approach Applied**:

1. Used Google-style format consistently (Args/Returns sections)
2. Focused on public APIs and complex private methods
3. Kept one-liner docstrings for trivial/self-explanatory methods
4. All ruff checks passing

### 11. Migrate to Native `agent_framework_declarative`

**Status**: 🔲 Not Started
**Files**:

- `src/agentic_fleet/agents/coordinator.py` (custom `AgentFactory`)
- `config/workflow_config.yaml` (agent definitions)

**Analysis**: The native `agent_framework_declarative` package (installed in `.venv`) provides:

| Feature                | Native Support                                                                                        | Your Custom Version                   |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------- |
| YAML agent definitions | ✅ `create_agent_from_yaml()`, `create_agent_from_yaml_path()`                                        | Custom `AgentFactory.create_agents()` |
| Multi-provider support | ✅ AzureOpenAI, OpenAI, Anthropic, AzureAI (Chat, Assistants, Responses)                              | OpenAI only                           |
| Tool parsing           | ✅ `FunctionTool`, `WebSearchTool`, `FileSearchTool`, `CodeInterpreterTool`, `McpTool`, `OpenApiTool` | Manual tool resolution                |
| Connection types       | ✅ `ApiKeyConnection`, `ReferenceConnection`, `RemoteConnection`, `AnonymousConnection`               | Direct env var access                 |
| Model options          | ✅ `temperature`, `maxOutputTokens`, `topP`, `seed`, `stopSequences`, `responseFormat`                | Partial                               |
| PowerFx expressions    | ✅ `=Env.OPENAI_API_KEY` syntax for env vars                                                          | Not supported                         |
| Output schemas         | ✅ `outputSchema` with `PropertySchema` → Pydantic model                                              | Manual                                |
| Function bindings      | ✅ `bindings` dict maps YAML tool names to Python callables                                           | `ToolRegistry`                        |

**Native YAML schema** (`kind: Prompt` format):

```yaml
kind: Prompt
name: researcher
description: Research specialist agent
model:
  configuration:
    type: openai
    name: gpt-4.1
    connection:
      type: api_key
      api_key: =Env.OPENAI_API_KEY
  parameters:
    temperature: 0.7
    maxOutputTokens: 4096
instructions: |
  You are a research specialist...
tools:
  - type: function
    name: web_search
  - type: mcp
    name: tavily
    connection:
      type: api_key
      api_key: =Env.TAVILY_API_KEY
```

**Custom additions to preserve** (not in native):

- `DSPyEnhancedAgent` with reasoning strategies (ReAct, PoT, CoT)
- Prompt module resolution (`prompts.researcher` → `get_researcher_instructions()`)
- `ToolRegistry` for capability-based tool discovery
- `cache_ttl` and `timeout` per agent

**Migration steps**:

1. **Phase 1**: Create `DSPyAgentFactory` extending native `AgentFactory`
2. **Phase 2**: Migrate YAML schema to native `kind: Prompt` format
3. **Phase 3**: Use native tool parsing (`FunctionTool`, `McpTool`)
4. **Phase 4**: Keep `DSPyEnhancedAgent` wrapper for reasoning integration
5. **Phase 5**: Remove redundant custom code from `coordinator.py`

**Example refactor pattern**:

```python
from agent_framework_declarative import AgentFactory as NativeAgentFactory

class DSPyAgentFactory(NativeAgentFactory):
    """Extends native factory with DSPy reasoning capabilities."""

    def __init__(self, enable_dspy: bool = True, dspy_config: dict | None = None):
        super().__init__()
        self.enable_dspy = enable_dspy
        self.dspy_config = dspy_config or {}

    def create_agent_from_yaml(self, yaml_str: str, bindings: dict | None = None) -> ChatAgent:
        base_agent = super().create_agent_from_yaml(yaml_str, bindings)
        if self.enable_dspy:
            return DSPyEnhancedAgent.from_chat_agent(base_agent, self.dspy_config)
        return base_agent
```

**Benefits**:

- ~200 LOC reduction in `coordinator.py`
- Native multi-provider support (Azure, Anthropic)
- PowerFx expressions for secure env var handling
- Native MCP tool integration
- Better alignment with Microsoft ecosystem

### 12. Simplify Observability Utilities

**Status**: 🔲 Not Started
**Files**:

- `src/agentic_fleet/utils/tracing.py` → Use native `agent_framework.observability`
- `src/agentic_fleet/utils/telemetry.py` → Keep `PerformanceTracker`, remove redundant `optional_span`
- `src/agentic_fleet/utils/dspy_manager.py` → Simplify, native `dspy.settings` is already thread-safe

**Prerequisite**: Test compatibility with AI Toolkit extension and Foundry tracing **before** removing custom code. Native edge runners emit OpenTelemetry spans automatically—verify these integrate correctly.

**Steps**:

1. Enable native `agent_framework.observability` alongside custom tracing
2. Verify spans appear in AI Toolkit / Foundry
3. Remove redundant custom spans incrementally

### 13. Consolidate Small Utility Files

**Status**: ✅ Completed
**Changes Made**:

- Moved `is_simple_task()` from `utils/task_utils.py` → `workflows/helpers.py`
- Merged `AsyncCompiler` class from `utils/async_compiler.py` → `utils/compiler.py`
- Merged workflow utilities from `workflows/utils.py` → `workflows/helpers.py` (including `synthesize_results`, `extract_artifacts`, `estimate_remaining_work`, `derive_objectives`, `create_openai_client_with_store`)
- Deleted the following files:
  - `utils/task_utils.py`
  - `utils/async_compiler.py`
  - `workflows/utils.py`
- Updated all import statements in dependent files
- `utils/gepa_optimizer.py` kept in place (circular import prevention with other utils modules)

**Files Reduced**: 3 files removed from codebase

### 14. Adopt Native Edge Patterns for Execution Strategies

**Status**: 🔲 Not Started
**Files**:

- `src/agentic_fleet/workflows/strategies.py` (custom parallel/sequential execution)

**Analysis**: Native `agent_framework` provides edge patterns that handle message orchestration:

| Custom Implementation                 | Native Replacement                                             |
| ------------------------------------- | -------------------------------------------------------------- |
| Parallel execution in `strategies.py` | `FanOutEdgeGroup` + `FanOutEdgeRunner` with `asyncio.gather()` |
| Sequential/delegated mode             | `SingleEdgeGroup` chain or `SwitchCaseEdgeGroup`               |
| Result aggregation                    | `FanInEdgeGroup` with buffering                                |
| Post-routing dispatch                 | `SwitchCaseEdgeGroup` with condition lambdas                   |

**Key insight**: Keep DSPy for _intelligent routing decisions_ (`DSPyReasoner.route_task()`), use native edge patterns for _message delivery mechanics_.

**Migration steps**:

1. **Phase 1**: Replace custom parallel execution with `FanOutEdgeGroup`
2. **Phase 2**: Use `SwitchCaseEdgeGroup` for post-routing dispatch
3. **Phase 3**: Use `FanInEdgeGroup` for aggregating parallel results before quality assessment
4. **Phase 4**: Remove redundant code from `strategies.py` (~100-150 LOC reduction)

**Benefits**:

- Native OpenTelemetry spans for all edge transitions
- Built-in error handling and retry semantics
- Proper trace context propagation
- Less custom code to maintain

---

## 🚀 Optimal Execution Order

The following linear sequence minimizes rework and maximizes efficiency by respecting dependencies:

```
Phase A: Foundation (No Dependencies)
├── #13 Consolidate small utility files     ← Reduces file count before other changes
├── #8  Extract magic numbers to config     ← Makes subsequent code cleaner
└── #9  Address TODO comments               ← Cleans up before major refactors

Phase B: Observability (Requires Phase A)
├── #12 Simplify observability utilities    ← Test AI Toolkit/Foundry first
│       └── Prerequisite: Verify tracing compatibility
└── #10 Standardize docstrings              ← Clean docs before tests

Phase C: Type Safety (Parallel with Phase B)
└── #7  Reduce `Any` type usage             ← Improves test type coverage

Phase D: Test Coverage (Requires Phase A-C)
└── #6  Add missing tests                   ← Tests validated code
        ├── 1. dspy_modules/reasoner.py     (DSPy signatures)
        ├── 2. agents/base.py               (DSPyEnhancedAgent)
        ├── 3. workflows/executors.py       (6 executor classes)
        └── 4. utils/resilience.py          (retry logic)

Phase E: Architecture Refactors (Requires Phase D)
├── #14 Adopt native edge patterns          ← Simplifies strategies.py
└── #11 Migrate to native declarative       ← Simplifies coordinator.py
```

### Estimated Effort

| Phase         | Items       | LOC Impact   | Time Estimate   |
| ------------- | ----------- | ------------ | --------------- |
| A ✅ Complete | #13, #8, #9 | -100 LOC     | ~2 hours        |
| B             | #12, #10    | -50 LOC      | 2-3 hours       |
| C             | #7          | ~0 LOC       | 1-2 hours       |
| D             | #6          | +400-600 LOC | 4-6 hours       |
| E             | #14, #11    | -250-350 LOC | 4-6 hours       |
| **Total**     |             | **~0 net**   | **13-20 hours** |

---

## Summary Table

| #   | Issue                                | Priority  | Status            |
| --- | ------------------------------------ | --------- | ----------------- |
| 1   | Pydantic V2 Config migration         | 🔴 High   | ✅ Completed      |
| 2   | Missing async generator return types | 🔴 High   | ✅ Completed      |
| 3   | Broad exception handling             | 🔴 High   | ⚠️ Partial (Docs) |
| 4   | Centralize env var access            | 🟡 Medium | ✅ Completed      |
| 5   | Deduplicate `_call_with_retry`       | 🟡 Medium | ✅ Completed      |
| 6   | Add missing tests                    | 🟡 Medium | 🔲 Not Started    |
| 7   | Reduce `Any` usage                   | 🟡 Medium | ✅ Completed      |
| 8   | Extract magic numbers                | 🟢 Low    | ✅ Completed      |
| 9   | Address TODO comments                | 🟢 Low    | ✅ Completed      |
| 10  | Standardize docstrings               | 🟢 Low    | ✅ Completed      |
| 11  | Migrate to native declarative        | 🟢 Low    | 🔲 Not Started    |
| 12  | Simplify observability utilities     | 🟢 Low    | 🔲 Not Started    |
| 13  | Consolidate small utility files      | 🟢 Low    | ✅ Completed      |
| 14  | Adopt native edge patterns           | 🟢 Low    | 🔲 Not Started    |

---

## 🎯 Expected Outcomes

Upon completion of all phases, AgenticFleet will achieve:

### Code Quality

- **~30% fewer files** in `utils/` and `workflows/` through consolidation
- **100% type coverage** on public APIs (no `Any` in signatures)
- **Consistent docstrings** following Google/NumPy format
- **Zero deprecated patterns** (Pydantic V3 ready)

### Test Coverage

- **>80% coverage** on DSPy integration layer (`dspy_modules/`, `agents/base.py`)
- **>70% coverage** on workflow executors with mocked LLM calls
- **Fallback paths tested** for graceful degradation scenarios

### Architecture Alignment

- **Native `agent_framework_declarative`** for agent YAML parsing (~200 LOC removed from `coordinator.py`)
- **Native edge patterns** (`FanOutEdgeGroup`, `SwitchCaseEdgeGroup`) for execution strategies (~150 LOC removed from `strategies.py`)
- **DSPy-only custom code** — AgenticFleet's value is in intelligent routing/reasoning, not message orchestration

### Observability

- **Single tracing path** via native `agent_framework.observability` + AI Toolkit/Foundry
- **`PerformanceTracker`** retained for DSPy-specific metrics
- **Automatic spans** for all edge transitions (no manual instrumentation)

### Maintainability

- **Clear separation**: DSPy = reasoning, agent_framework = execution
- **Config-driven thresholds** — no magic numbers in Python
- **Addressed TODOs** — no stale comments or dead code paths

### Metrics Summary

| Metric                         | Before | After |
| ------------------------------ | ------ | ----- |
| Files in `utils/`              | 26     | ~22   |
| Files in `workflows/`          | 15     | ~13   |
| Custom LOC in `strategies.py`  | ~300   | ~150  |
| Custom LOC in `coordinator.py` | ~250   | ~50   |
| Test coverage (DSPy layer)     | ~20%   | >80%  |
| `Any` type annotations         | ~15    | 0     |

---

_Last updated: 2025-11-25_
