# Performance Optimization Recommendations

This document identifies performance bottlenecks in AgenticFleet and provides actionable optimization recommendations.

## Executive Summary

AgenticFleet is a complex multi-agent orchestration system that combines DSPy for intelligent routing with Microsoft Agent Framework for agent execution. The analysis identified several performance optimization opportunities across configuration loading, file I/O, caching, and async operations.

## Performance Issues Identified

### 1. **Configuration Loading Without Caching** (HIGH PRIORITY)

**Issue:** `load_config()` reads and parses YAML on every call without caching.

**Impact:** File I/O and YAML parsing repeated multiple times during initialization and runtime.

**Current Code:** `src/agentic_fleet/utils/config.py:702`
```python
def load_config(config_path: str | None = None, validate: bool = True) -> dict[str, Any]:
    """Load and validate configuration from YAML file."""
    # ... reads file every time
    with open(config_file) as f:
        config_dict = yaml.safe_load(f)
```

**Called From:**
- `src/agentic_fleet/cli/runner.py:85`
- `src/agentic_fleet/cli/utils.py:17`
- `src/agentic_fleet/cli/commands/optimize.py:98`
- `src/agentic_fleet/dspy_modules/reasoner.py:72`
- `src/agentic_fleet/cli/commands/eval.py:142`

**Recommendation:**
Add `@lru_cache` with file modification time tracking to cache config:

```python
from functools import lru_cache
import os

@lru_cache(maxsize=4)
def _load_config_cached(config_path: str, mtime: float, validate: bool) -> dict[str, Any]:
    """Internal cached config loader."""
    # ... existing load logic

def load_config(config_path: str | None = None, validate: bool = True) -> dict[str, Any]:
    """Load and validate configuration from YAML file with caching."""
    # Resolve config path
    if config_path is None:
        cwd_default = Path("config/workflow_config.yaml")
        pkg_default = _package_root() / "config" / "workflow_config.yaml"
        config_file = cwd_default if cwd_default.exists() else pkg_default
    else:
        config_file = Path(config_path)
    
    # Get modification time for cache invalidation
    mtime = config_file.stat().st_mtime if config_file.exists() else 0
    
    return _load_config_cached(str(config_file), mtime, validate)
```

**Estimated Impact:** 10-50ms saved per config load (4+ calls during typical workflow initialization)

---

### 2. **Linear Scan for Workflow ID Lookup in History** (HIGH PRIORITY)

**Issue:** `get_execution_by_id()` performs O(n) linear scan through entire JSONL/JSON history file.

**Impact:** Slow lookups as history grows; reading entire file for single record retrieval.

**Current Code:** `src/agentic_fleet/utils/history_manager.py:306-334`
```python
def get_execution_by_id(self, workflow_id: str) -> dict[str, Any] | None:
    # ... scans entire JSONL file line by line
    with open(jsonl_file) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("workflowId") == workflow_id:
                return entry  # O(n) lookup
```

**Recommendation:**
Implement an in-memory index for recent executions:

```python
class HistoryManager:
    def __init__(self, ...):
        # ... existing init
        self._recent_executions_index: dict[str, dict[str, Any]] = {}
        self._index_size_limit = 1000
        
    def save_execution(self, execution: dict[str, Any]) -> str:
        workflow_id = execution.get("workflowId")
        
        # Update index
        if workflow_id:
            self._recent_executions_index[workflow_id] = execution
            # Trim index if too large (LRU-style)
            if len(self._recent_executions_index) > self._index_size_limit:
                # Remove oldest 10%
                to_remove = list(self._recent_executions_index.keys())[:100]
                for key in to_remove:
                    del self._recent_executions_index[key]
        
        # ... existing save logic
        
    def get_execution_by_id(self, workflow_id: str) -> dict[str, Any] | None:
        # Check index first (O(1))
        if workflow_id in self._recent_executions_index:
            return self._recent_executions_index[workflow_id]
        
        # Fall back to file scan for older entries
        # ... existing scan logic
```

**Alternative:** Use SQLite for structured history storage with indexed queries.

**Estimated Impact:** O(n) → O(1) for recent executions; 100ms+ saved for large history files

---

### 3. **Synchronous File I/O in Async Context** (MEDIUM PRIORITY)

**Issue:** JSON rotation and history operations use synchronous file I/O in async functions.

**Impact:** Blocks event loop during file operations, reducing concurrency.

**Current Code:** `src/agentic_fleet/utils/history_manager.py:202-228`
```python
def _save_json(self, execution: dict[str, Any]) -> str:
    """Save execution in JSON format (full read/write)."""
    # ... synchronous open/read/write in potentially async context
    with open(history_file) as f:
        existing_history = json.load(f)  # Blocking I/O
```

**Recommendation:**
Use `aiofiles` consistently for all file operations in async paths:

```python
async def _save_json_async(self, execution: dict[str, Any]) -> str:
    """Save execution in JSON format (async)."""
    history_file = self.history_dir / "execution_history.json"
    
    # Load existing history
    existing_history: list[dict[str, Any]] = []
    if history_file.exists():
        try:
            async with aiofiles.open(history_file) as f:
                content = await f.read()
                existing_history = json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to load existing history: {e}")
    
    # Append and rotate
    existing_history.append(execution)
    if self.max_entries and len(existing_history) > self.max_entries:
        existing_history = existing_history[-self.max_entries:]
    
    # Write atomically
    content = json.dumps(existing_history, indent=2, cls=FleetJSONEncoder)
    async with aiofiles.open(history_file, "w") as f:
        await f.write(content)
```

**Estimated Impact:** Prevents event loop blocking; improves concurrent request handling

---

### 4. **Redundant Module Cache Key Construction** (LOW PRIORITY)

**Issue:** DSPy module initialization builds cache keys repeatedly with string operations.

**Impact:** Minor CPU overhead during reasoner initialization (200+ lines of cache key logic).

**Current Code:** `src/agentic_fleet/dspy_modules/reasoner.py:200-300`
```python
def _ensure_modules_initialized(self) -> None:
    # Repeated cache key construction
    cache_key_prefix = f"enhanced{typed_suffix}" if self.use_enhanced_signatures else f"standard{typed_suffix}"
    analyzer_key = f"{cache_key_prefix}_analyzer"
    # ... 10+ similar constructions
```

**Recommendation:**
Pre-compute cache keys once during `__init__`:

```python
class DSPyReasoner:
    def __init__(self, ...):
        # ... existing init
        self._cache_keys = self._compute_cache_keys()
        
    def _compute_cache_keys(self) -> dict[str, str]:
        """Pre-compute all cache keys based on configuration."""
        typed_suffix = "_typed" if self.use_typed_signatures else ""
        cache_key_prefix = (
            f"enhanced{typed_suffix}" if self.use_enhanced_signatures 
            else f"standard{typed_suffix}"
        )
        
        return {
            "analyzer": f"{cache_key_prefix}_analyzer",
            "router": f"{cache_key_prefix}_router",
            "strategy": f"{cache_key_prefix}_strategy",
            "quality_assessor": f"quality_assessor{typed_suffix}",
            "progress_evaluator": f"progress_evaluator{typed_suffix}",
            "tool_planner": f"tool_planner{typed_suffix}",
            "simple_responder": "simple_responder",
            "group_chat_selector": "group_chat_selector",
            "event_narrator": "event_narrator",
        }
    
    def _ensure_modules_initialized(self) -> None:
        # Use pre-computed keys
        if self._analyzer is None:
            analyzer_key = self._cache_keys["analyzer"]
            # ...
```

**Estimated Impact:** Minor CPU savings; cleaner code

---

### 5. **Inefficient Polling in Foundry Agent** (MEDIUM PRIORITY)

**Issue:** Fixed-interval polling with `asyncio.sleep()` for agent status checks.

**Impact:** Unnecessary delays and API calls; not adaptive to actual agent response times.

**Current Code:** `src/agentic_fleet/agents/foundry.py:171`
```python
while run.status in ("queued", "in_progress", "requires_action"):
    await asyncio.sleep(self.poll_interval)  # Fixed 1-2 second delay
    run = await agents_client.get_run(...)
```

**Recommendation:**
Implement exponential backoff with configurable max interval:

```python
async def _poll_run_with_backoff(
    self, 
    agents_client, 
    thread_id: str, 
    run_id: str,
    initial_interval: float = 0.5,
    max_interval: float = 5.0,
    backoff_factor: float = 1.5
) -> Any:
    """Poll run status with exponential backoff."""
    interval = initial_interval
    
    while True:
        run = await agents_client.get_run(thread_id=thread_id, run_id=run_id)
        
        if run.status not in ("queued", "in_progress", "requires_action"):
            return run
            
        if run.status == "requires_action":
            # Handle immediately
            logger.warning(...)
            await agents_client.cancel_run(...)
            return run
        
        # Exponential backoff
        await asyncio.sleep(interval)
        interval = min(interval * backoff_factor, max_interval)
```

**Estimated Impact:** Reduced average response time by 20-40% for fast completions; fewer API calls

---

### 6. **JSON Serialization in Hot Path** (LOW PRIORITY)

**Issue:** Repeated `json.dumps()` calls in event streaming and logging.

**Impact:** CPU overhead for serialization, especially with large objects.

**Current Code:** Multiple locations including:
- `src/agentic_fleet/workflows/handoff.py:278` - `json.dumps(artifacts, indent=2)`
- `src/agentic_fleet/utils/history_manager.py:145` - `json.dumps(execution, cls=FleetJSONEncoder)`

**Recommendation:**
1. Cache serialized representations when objects don't change
2. Remove `indent=2` for non-debugging contexts (saves CPU and space)
3. Use orjson for faster JSON serialization:

```python
# In requirements/pyproject.toml
# orjson = "^3.9.0"  # 2-3x faster than stdlib json

import orjson

def fast_json_dumps(obj: Any) -> str:
    """Fast JSON serialization using orjson."""
    return orjson.dumps(obj).decode('utf-8')
```

**Estimated Impact:** 2-3x faster JSON operations; reduced CPU usage in streaming

---

## Additional Recommendations

### 7. **Lazy Import for Heavy Dependencies**

Some modules import heavy dependencies at module level, increasing startup time:

```python
# Current - immediate import
import dspy
from agent_framework import ...

# Recommended - lazy import where appropriate
def get_reasoner():
    import dspy  # Import only when needed
    return dspy.Module(...)
```

**Benefit:** Faster CLI startup for commands that don't need full runtime

---

### 8. **Add Performance Monitoring Utilities**

Create built-in performance profiling tools:

```python
# New file: src/agentic_fleet/utils/profiling.py

import time
from contextlib import contextmanager
from typing import Any
import logging

logger = logging.getLogger(__name__)

@contextmanager
def timed_operation(operation_name: str, threshold_ms: float = 100.0):
    """Context manager to log slow operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > threshold_ms:
            logger.warning(
                f"Slow operation: {operation_name} took {elapsed_ms:.1f}ms "
                f"(threshold: {threshold_ms:.1f}ms)"
            )
        else:
            logger.debug(f"{operation_name} completed in {elapsed_ms:.1f}ms")

# Usage:
# with timed_operation("load_config"):
#     config = load_config()
```

---

### 9. **Database Optimization for History Storage**

For production deployments, consider:

1. **SQLite with indexes** for local history:
   ```sql
   CREATE TABLE executions (
       workflow_id TEXT PRIMARY KEY,
       timestamp INTEGER NOT NULL,
       task TEXT,
       result TEXT,
       metadata TEXT,
       INDEX idx_timestamp ON executions(timestamp)
   );
   ```

2. **Batch writes** instead of individual appends
3. **Periodic vacuum** for JSONL files to remove old entries

---

### 10. **Async Compilation Background Processing**

Current implementation already uses `run_in_executor`, but ensure it's non-blocking:

✅ Good - already implemented in `compiler.py:902`:
```python
self._compilation_task = loop.run_in_executor(None, _compile)
```

---

## Implementation Priority

### High Priority (Implement First)
1. ✅ **Configuration caching** - Most frequent bottleneck
2. ✅ **History index** - Critical for scalability
3. ✅ **Async file I/O** - Improves concurrency

### Medium Priority
4. **Polling optimization** - Better UX and fewer API calls
5. **Performance monitoring utilities** - Essential for tracking improvements

### Low Priority (Nice to Have)
6. Cache key optimization
7. JSON optimization with orjson
8. Lazy imports

---

## Performance Testing Guidelines

### Benchmark Before and After

Use the existing benchmark script with metrics:

```bash
# Baseline measurement
python scripts/benchmark_api.py --url http://localhost:8000/api/v1/workflow/run \
  --concurrency 10 --requests 20

# Measure with profiling
python -m cProfile -o profile.stats scripts/benchmark_api.py
python -m pstats profile.stats
```

### Key Metrics to Track

1. **Latency Metrics:**
   - P50, P95, P99 response times
   - Cold start time (first request)
   - Warm path time (cached config/modules)

2. **Throughput:**
   - Requests per second
   - Concurrent request handling

3. **Resource Usage:**
   - CPU utilization
   - Memory footprint
   - File I/O operations

4. **Cache Efficiency:**
   - Cache hit rate
   - Cache memory usage

---

## Configuration Recommendations

Add performance tuning options to `workflow_config.yaml`:

```yaml
performance:
  # History management
  history_index_size: 1000  # Number of recent executions to index in memory
  history_max_entries: 10000  # Max entries before rotation
  
  # Caching
  config_cache_enabled: true
  module_cache_enabled: true
  
  # File I/O
  use_async_file_io: true
  batch_write_size: 10  # Batch history writes
  
  # Polling
  foundry_poll_interval: 0.5  # Initial poll interval (seconds)
  foundry_poll_max_interval: 5.0  # Max poll interval with backoff
  foundry_poll_backoff_factor: 1.5
```

---

## Monitoring and Observability

### Add Telemetry for Performance Tracking

```python
from opentelemetry import metrics

# Add performance metrics
performance_meter = metrics.get_meter("agentic_fleet.performance")

config_load_counter = performance_meter.create_counter(
    "config_loads",
    description="Number of config load operations"
)

config_load_duration = performance_meter.create_histogram(
    "config_load_duration_ms",
    description="Config load duration in milliseconds"
)

# Usage:
with timed_operation("load_config") as timer:
    config = load_config()
    config_load_counter.add(1, {"cached": timer.was_cached})
    config_load_duration.record(timer.duration_ms)
```

---

## Expected Overall Impact

Implementing high-priority optimizations should yield:

- **Startup time:** 30-50% reduction
- **Average request latency:** 15-25% reduction
- **Concurrent throughput:** 40-60% improvement
- **Memory efficiency:** 10-20% reduction
- **Scalability:** Support for 10x larger history files without degradation

---

## Next Steps

1. Implement configuration caching (1-2 hours)
2. Add history indexing (2-3 hours)
3. Convert file I/O to async (3-4 hours)
4. Add performance monitoring utilities (1-2 hours)
5. Run benchmarks and validate improvements (1 hour)
6. Document performance best practices for contributors

---

## Related Documentation

- [Architecture Overview](../README.md#architecture)
- [Configuration Guide](../README.md#configuration)
- [Development Guide](../CONTRIBUTING.md)
- [OpenTelemetry Tracing](../README.md#observability)

---

*Last Updated: 2025-12-13*
*Analysis Version: 1.0*
