# Code Quality & Architecture Improvements

## Overview

This document describes the code quality improvements and architectural enhancements made to AgenticFleet to improve maintainability, type safety, performance, and developer experience.

## Enhanced Error Handling

### Exception Hierarchy

A comprehensive exception hierarchy has been implemented in `workflows/exceptions.py`:

- **`WorkflowError`** - Base exception with context support
- **`AgentExecutionError`** - Agent execution failures with task context
- **`RoutingError`** - Task routing failures
- **`ConfigurationError`** - Configuration validation errors
- **`HistoryError`** - History operation failures
- **`CompilationError`** - DSPy compilation failures
- **`CacheError`** - Cache operation failures
- **`ValidationError`** - Input validation errors
- **`TimeoutError`** - Operation timeout errors
- **`ToolError`** - Tool execution failures

All exceptions support structured context dictionaries for better debugging:

```python
from agentic_fleet.workflows.exceptions import AgentExecutionError

try:
    result = await agent.run(task)
except Exception as e:
    raise AgentExecutionError(
        agent_name="Researcher",
        task=task,
        original_error=e,
        context={"round": current_round, "attempt": attempt_number}
    )
```

## Type Safety Improvements

### Protocol Definitions

Protocol definitions in `utils/types.py` provide type safety for external dependencies:

- **`DSPySignature`** - Protocol for DSPy signature classes
- **`DSPyModule`** - Protocol for DSPy modules
- **`DSPySettings`** - Protocol for DSPy settings
- **`ChatClient`** - Protocol for chat clients
- **`ToolProtocol`** - Protocol for tools
- **`ProgressCallback`** - Protocol for progress reporting
- **`CacheProtocol`** - Protocol for cache implementations

Usage:

```python
from agentic_fleet.utils.types import DSPyModule, ProgressCallback

def compile_module(module: DSPyModule, callback: ProgressCallback) -> DSPyModule:
    # Type-safe operations
    ...
```

### Type Aliases

Common type patterns are aliased for consistency:

```python
from agentic_fleet.utils.types import AgentDict, EventStream, ExecutionResult

def process_events(stream: EventStream) -> ExecutionResult:
    ...
```

## Caching Improvements

### Enhanced TTLCache

The `TTLCache` in `utils/cache.py` now includes:

- **Hit rate tracking** via `CacheStats`
- **Incremental cleanup** of expired entries
- **Max size support** with LRU eviction
- **Periodic cleanup** to reduce memory usage

Example:

```python
from agentic_fleet.utils.cache import TTLCache

cache = TTLCache(ttl_seconds=300, max_size=1000)

# Use cache
cache.set("key", value)
result = cache.get("key")

# Monitor performance
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Hits: {stats.hits}, Misses: {stats.misses}")
```

### Cache Statistics

`CacheStats` provides metrics for monitoring:

- `hits` - Number of cache hits
- `misses` - Number of cache misses
- `evictions` - Number of evicted entries
- `sets` - Number of cache sets
- `hit_rate` - Cache hit rate (0.0 to 1.0)
- `total_requests` - Total cache requests

## Code Organization

### CLI Module Structure

The CLI has been refactored into focused modules:

- **`cli/runner.py`** - `WorkflowRunner` class managing workflow execution
- **`cli/display.py`** - Display utilities (`display_result`, `show_help`, `show_status`)
- **`cli/app.py`** - Typer entry point
- **`console.py`** - Command definitions

This separation improves:

- Testability (each module can be tested independently)
- Maintainability (clearer responsibilities)
- Reusability (display utilities can be used elsewhere)

### Constants Centralization

Magic numbers and strings are centralized in `utils/constants.py`:

- Task validation limits
- Cache TTL values
- Timeout constants
- Quality thresholds
- Agent names and tool names
- Phase names and status values

Example:

```python
from agentic_fleet.utils.constants import (
    DEFAULT_CACHE_TTL,
    DEFAULT_QUALITY_THRESHOLD,
    AGENT_RESEARCHER,
    PHASE_EXECUTION
)
```

## Performance Optimizations

### Async Compilation

Background DSPy compilation is available via `utils/async_compiler.py`:

```python
from agentic_fleet.utils.async_compiler import AsyncCompiler

compiler = AsyncCompiler()

# Start compilation in background
await compiler.compile_in_background(
    module=supervisor_module,
    examples_path="data/supervisor_examples.json"
)

# Continue with other initialization
# ...

# Wait for compilation when needed
compiled = await compiler.wait_for_compilation(timeout=60.0)
```

Benefits:

- Non-blocking workflow initialization
- Faster startup times
- Better user experience

### Cache Optimization

- **Granular invalidation** using signature and config hashes
- **Periodic cleanup** to prevent memory bloat
- **LRU eviction** when max size is reached
- **Statistics tracking** for optimization

## Best Practices

### Error Handling

1. Use specific exceptions from `workflows/exceptions.py`
2. Include context dictionaries for debugging
3. Preserve original exceptions with `from` clause
4. Log errors with full context server-side

### Type Safety

1. Use protocol definitions from `utils/types.py`
2. Add type hints to all public APIs
3. Use type aliases for common patterns
4. Avoid `type: ignore` comments where possible

### Caching

1. Monitor cache hit rates via `CacheStats`
2. Adjust TTL based on usage patterns
3. Set appropriate max sizes for long-running processes
4. Use cache statistics for optimization

### Code Organization

1. Keep modules focused on single responsibilities
2. Use constants from `utils/constants.py` instead of magic values
3. Separate CLI logic from business logic
4. Document public APIs with type hints

## Migration Guide

### Updating Error Handling

**Before:**

```python
try:
    result = await agent.run(task)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    raise
```

**After:**

```python
from agentic_fleet.workflows.exceptions import AgentExecutionError

try:
    result = await agent.run(task)
except Exception as e:
    raise AgentExecutionError(
        agent_name=agent.name,
        task=task,
        original_error=e,
        context={"round": round_number}
    )
```

### Using Constants

**Before:**

```python
if score >= 8.0:
    # ...
```

**After:**

```python
from agentic_fleet.utils.constants import DEFAULT_QUALITY_THRESHOLD

if score >= DEFAULT_QUALITY_THRESHOLD:
    # ...
```

### Using Enhanced Cache

**Before:**

```python
cache = TTLCache(ttl_seconds=300)
```

**After:**

```python
from agentic_fleet.utils.cache import TTLCache
from agentic_fleet.utils.constants import DEFAULT_CACHE_TTL

cache = TTLCache(ttl_seconds=DEFAULT_CACHE_TTL, max_size=1000)
stats = cache.get_stats()
```

## References

- Exception hierarchy: `src/agentic_fleet/workflows/exceptions.py`
- Type definitions: `src/agentic_fleet/utils/types.py`
- Cache implementation: `src/agentic_fleet/utils/cache.py`
- Constants: `src/agentic_fleet/utils/constants.py`
- Async compiler: `src/agentic_fleet/utils/async_compiler.py`
- CLI modules: `src/agentic_fleet/cli/`
