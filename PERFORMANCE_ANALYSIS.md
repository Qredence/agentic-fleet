# Performance Analysis & Optimization Recommendations

**Date**: 2024-12-22  
**Analysis Tool**: Python Backend Reviewer (complexity, concurrency, duplicates, imports)  
**Files Analyzed**: 168 Python files in `src/agentic_fleet/`

## Executive Summary

Comprehensive static analysis identified **247 complexity issues** across the codebase. The analysis reveals:

- **3 Critical concurrency issues** (false positives - CLI-only code, not shared across requests)
- **6 Warning-level concurrency issues** (1 real issue in `BridgeMiddleware`)
- **122 High-complexity functions** (cyclomatic complexity > 10)
- **125 Long functions** (> 50 lines)
- **No duplicate code blocks found** ✅

### Key Finding

**Most flagged "issues" are acceptable for orchestration/workflow code**. The thresholds used (complexity 10, length 50) are strict software engineering ideals that don't account for:

1. **Orchestration patterns** - Workflows naturally have decision points
2. **Event handling** - WebSocket/SSE handlers process multiple event types
3. **Configuration loading** - Setup code is inherently sequential

**Priority**: Focus on critical-path code (WebSocket/SSE handlers) and shared state mutations.

---

## Critical Priority (Fix Now)

### 1. WebSocket Handler - Extreme Complexity

**File**: `src/agentic_fleet/services/chat_websocket.py:526`  
**Function**: `async def handle(websocket: WebSocket)`  
**Metrics**:
- Cyclomatic complexity: **76** (threshold: 10)
- Maximum nesting depth: **7** (threshold: 4)
- Runs on: **Every WebSocket connection** (critical path)

**Impact**: High - This function handles all WebSocket chat sessions

**Recommendation**: Extract sub-handlers:
```python
# Before: 76 complexity, 300+ lines
async def handle(self, websocket: WebSocket):
    # Validation, setup, message loop, error handling all in one

# After: ~10 complexity per function
async def handle(self, websocket: WebSocket):
    if not await self._validate_and_setup(websocket):
        return
    await self._message_loop(websocket, session_data)

async def _validate_and_setup(self, websocket) -> tuple[bool, dict]:
    # Validation + initialization logic

async def _message_loop(self, websocket, session_data):
    # Main message processing loop

async def _handle_task_message(self, msg_data, session_data):
    # Process task messages

async def _handle_response_message(self, msg_data, session_data):
    # Process HITL responses
```

**Estimated Effort**: 4-6 hours  
**Risk**: Medium (requires careful testing of WebSocket flows)

---

### 2. Event Mapping Function - Massive Size

**File**: `src/agentic_fleet/api/events/mapping.py:385`  
**Function**: `def map_workflow_event(event, accumulated_reasoning)`  
**Metrics**:
- Length: **580 lines** (threshold: 50)
- Runs on: **Every SSE and WebSocket event** (critical path)

**Impact**: High - Called for every event streamed to clients

**Recommendation**: Extract type-specific handlers:
```python
# Before: 580-line function with 15+ event types
def map_workflow_event(event, accumulated_reasoning):
    if isinstance(event, WorkflowStatusEvent):
        # 50 lines
    elif isinstance(event, RequestInfoEvent):
        # 70 lines
    # ... 13 more event types

# After: Dispatch table + focused handlers
_EVENT_HANDLERS = {
    WorkflowStartedEvent: _handle_workflow_started,
    WorkflowStatusEvent: _handle_workflow_status,
    RequestInfoEvent: _handle_request_info,
    ReasoningStreamEvent: _handle_reasoning_stream,
    MagenticAgentMessageEvent: _handle_agent_message,
    # ... etc
}

def map_workflow_event(event, accumulated_reasoning):
    handler = _EVENT_HANDLERS.get(type(event))
    if handler:
        return handler(event, accumulated_reasoning)
    return _handle_unknown_event(event, accumulated_reasoning)
```

**Estimated Effort**: 6-8 hours  
**Risk**: Medium-High (extensive testing needed, affects all streaming)

---

### 3. SSE Stream Handler - High Complexity

**File**: `src/agentic_fleet/services/chat_sse.py:70`  
**Function**: `async def stream_chat(...)`  
**Metrics**:
- Cyclomatic complexity: **37** (threshold: 10)
- Runs on: **Every SSE request** (critical path)

**Impact**: High - Used for all HTTP-based streaming

**Recommendation**: Extract setup and teardown:
```python
# Before: 37 complexity
async def stream_chat(self, conversation_id, message, ...):
    # History loading
    # Checkpointing setup
    # Thread hydration
    # Session creation
    # Streaming loop
    # Cleanup

# After: ~10 complexity each
async def stream_chat(self, conversation_id, message, ...):
    context = await self._setup_stream_context(conversation_id, message, ...)
    try:
        async for event in self._stream_events(context):
            yield event
    finally:
        await self._cleanup_stream(context)
```

**Estimated Effort**: 2-3 hours  
**Risk**: Low-Medium

---

## High Priority (Performance Impact)

### 4. Agent Framework Shims - Complexity 34

**File**: `src/agentic_fleet/utils/agent_framework_shims.py:79`  
**Function**: `def ensure_agent_framework_shims()`  
**Metrics**: Cyclomatic complexity: 34

**Impact**: Medium - Called during initialization (not per-request)

**Recommendation**: Extract platform-specific patchers:
```python
def ensure_agent_framework_shims():
    _patch_azure_openai()
    _patch_async_client()
    _patch_agent_attributes()

def _patch_azure_openai():
    # Azure OpenAI patching logic

def _patch_async_client():
    # Async client patching logic
```

**Estimated Effort**: 2 hours  
**Risk**: Low (initialization only)

---

### 5. Workflow Executors - All > 100 Lines

**Files**:
- `workflows/executors/analysis.py:89` - `handle_task()` - 167 lines
- `workflows/executors/routing.py:45` - `handle_analysis()` - 231 lines  
- `workflows/executors/execution.py:34` - `handle_routing()` - 138 lines
- `workflows/executors/progress.py:42` - `handle_execution()` - 100 lines
- `workflows/executors/quality.py:42` - `handle_progress()` - 140 lines

**Impact**: Medium - Core workflow orchestration (called per workflow execution)

**Recommendation**: These are **acceptable as-is** for orchestration code. They represent the 5-phase pipeline and breaking them up would reduce clarity. Consider:

1. **Extract validation logic** to separate functions
2. **Add guard clauses** to reduce nesting
3. **Document decision points** with comments

**Alternative**: Only refactor if profiling shows actual performance issues.

**Estimated Effort**: 8-12 hours (if pursued)  
**Risk**: High (core workflow logic)

---

### 6. DSPy Service - get_predictor_prompts (Complexity 25, Nesting 5)

**File**: `src/agentic_fleet/services/dspy_service.py:32`  
**Function**: `def get_predictor_prompts(predictor)`  
**Metrics**: 
- Cyclomatic complexity: 25
- Maximum nesting depth: 5

**Impact**: Low - Admin/debugging endpoint only

**Recommendation**: Extract recursion into helper:
```python
def get_predictor_prompts(predictor):
    return _extract_prompts_recursive(predictor, depth=0, max_depth=10)

def _extract_prompts_recursive(obj, depth, max_depth):
    if depth > max_depth:
        return []
    # Recursion logic here
```

**Estimated Effort**: 1 hour  
**Risk**: Very Low

---

## Medium Priority (Secondary Paths)

### 7. Long Initialization Functions

**Files**:
- `agents/coordinator.py:633` - `_resolve_instructions()` - 70 lines
- `agents/base.py:41` - `__init__()` - 55 lines
- `utils/infra/tracing.py:69` - `initialize_tracing()` - 177 lines

**Impact**: Low - Called during startup only

**Recommendation**: Extract configuration sections:
```python
# Example for initialize_tracing
def initialize_tracing():
    config = _load_tracing_config()
    _setup_otlp_exporter(config)
    _setup_azure_monitor(config)
    _configure_instrumentation()
```

**Estimated Effort**: 3-4 hours total  
**Risk**: Very Low

---

### 8. CLI Commands - Long Functions

**Files**:
- `cli/commands/run.py:73` - `run()` - 195 lines
- `cli/commands/optimize.py:27` - `gepa_optimize()` - 183 lines
- `cli/commands/handoff.py:19` - `handoff()` - 121 lines

**Impact**: Very Low - CLI only, not performance-critical

**Recommendation**: **Defer** - These are command handlers with setup/teardown logic. They're acceptable as-is.

---

## Concurrency Issues

### Real Issue: BridgeMiddleware Shared State

**File**: `src/agentic_fleet/api/middleware.py:186`  
**Class**: `BridgeMiddleware`  
**Issue**: Mutating `self.execution_data` in async methods

**Root Cause**: 
- `SupervisorWorkflow` is shared across requests (cached in `app.state.supervisor_workflow`)
- `BridgeMiddleware` instances are attached to the shared workflow
- Multiple concurrent requests would share the same `execution_data` dict

**Fix**: Make execution data request-scoped:
```python
# Before
class BridgeMiddleware(ChatMiddleware):
    def __init__(self, history_manager, dspy_examples_path):
        self.history_manager = history_manager
        self.dspy_examples_path = dspy_examples_path
        self.execution_data: dict[str, Any] = {}  # SHARED!
    
    async def on_start(self, task, context):
        self.execution_data = {...}  # Race condition

# After: Option 1 - Pass through context
class BridgeMiddleware(ChatMiddleware):
    def __init__(self, history_manager, dspy_examples_path):
        self.history_manager = history_manager
        self.dspy_examples_path = dspy_examples_path
    
    async def on_start(self, task, context):
        context["execution_data"] = {...}  # Store in request context
    
    async def on_end(self, result, context):
        execution_data = context.get("execution_data", {})
        # Use execution_data

# After: Option 2 - Use contextvars
from contextvars import ContextVar

_execution_data: ContextVar[dict] = ContextVar("execution_data", default={})

class BridgeMiddleware(ChatMiddleware):
    async def on_start(self, task, context):
        _execution_data.set({...})
```

**Estimated Effort**: 2-3 hours  
**Risk**: Medium (requires testing concurrent requests)

---

### False Positives (Not Real Issues)

1. **WorkflowRunner concurrency warnings** - CLI only, created per command ✅
2. **FoundryHostedAgent mutations** - Per-agent instance, not shared ✅
3. **Module-level constants** (`logger`, `__all__`, `router`) - Never mutated ✅

---

## Optimization Strategy

### Phase 1: Quick Wins (1-2 days)
1. Fix `BridgeMiddleware` concurrency issue
2. Extract `stream_chat()` setup/cleanup helpers
3. Add early-return guards to reduce nesting

### Phase 2: Critical Path (1 week)
4. Refactor `map_workflow_event()` with dispatch table
5. Extract `WebSocket.handle()` sub-handlers
6. Profile real-world usage to validate improvements

### Phase 3: Polish (1 week)
7. Refactor `ensure_agent_framework_shims()`
8. Clean up long initialization functions
9. Add complexity regression tests

---

## Pragmatic Thresholds for This Codebase

| Metric | Strict | Pragmatic | Notes |
|--------|--------|-----------|-------|
| Cyclomatic complexity | 10 | **25** | Orchestrators have natural decision points |
| Function length | 50 lines | **150 lines** | Async flows can be longer |
| Nesting depth | 4 | **5** | Guard clauses help more than extracting |
| God class methods | 20 | **N/A** | OK if it's a façade that delegates |

**Hard limits (always fix)**:
- No functions > 300 lines
- No nesting > 7 levels  
- No shared-state mutation without synchronization

---

## Testing Strategy

Before any refactoring:

1. **Run existing tests**: `make test`
2. **Profile critical paths**: Use `py-spy` or `cProfile` on WebSocket/SSE handlers
3. **Load test**: Use `locust` to test concurrent requests (detect race conditions)
4. **Benchmark**: Measure latency before/after (target: <10% regression)

After refactoring:

1. **Unit tests** for extracted functions
2. **Integration tests** for WebSocket/SSE flows
3. **Concurrency tests** for middleware (pytest-xdist with multiple workers)

---

## Tools & Commands

```bash
# Complexity analysis
python3 .github/skills/python-backend-reviewer/scripts/complexity_analyzer.py src/agentic_fleet/

# Concurrency issues
python3 .github/skills/python-backend-reviewer/scripts/concurrency_analyzer.py src/agentic_fleet/services/ src/agentic_fleet/api/

# Duplicate detection
python3 .github/skills/python-backend-reviewer/scripts/detect_duplicates.py src/agentic_fleet/

# Profiling (install first)
pip install py-spy
py-spy record -o profile.svg -- python -m agentic_fleet run -m "test query"

# Load testing (install first)
pip install locust
locust -f tests/load/websocket_test.py
```

---

## Metrics Baseline

**Current State** (before optimization):
- Functions with complexity > 10: 122
- Functions with length > 50: 125
- Critical path functions: 3 (WebSocket.handle, map_workflow_event, stream_chat)
- Concurrency issues: 1 (BridgeMiddleware)

**Target State** (after Phase 1-2):
- Critical path complexity: < 15 per function
- Concurrency issues: 0
- Performance regression: < 10%

---

## References

- Python Backend Reviewer: `.github/skills/python-backend-reviewer/`
- Best Practices: `.github/skills/python-backend-reviewer/references/best_practices.md`
- Refactoring Patterns: `.github/skills/python-backend-reviewer/references/refactoring_patterns.md`
- Anti-patterns: `.github/skills/python-backend-reviewer/references/python_antipatterns.md`
