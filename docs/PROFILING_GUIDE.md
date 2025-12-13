# Performance Profiling Guide

This guide demonstrates how to use AgenticFleet's built-in performance monitoring utilities to track and optimize slow operations.

## Quick Start

```python
from agentic_fleet.utils import timed_operation

# Track a slow operation
with timed_operation("load_config", threshold_ms=50):
    config = load_config()
```

## Available Tools

### 1. `timed_operation` - Context Manager

Track execution time of code blocks. Logs warnings when operations exceed a threshold.

```python
from agentic_fleet.utils import timed_operation

# Basic usage
with timed_operation("database_query"):
    result = database.query("SELECT * FROM users")

# Custom threshold (default: 100ms)
with timed_operation("api_call", threshold_ms=500):
    response = api.get("/data")
```

**Output:**
```
DEBUG: database_query completed in 45.2ms
WARNING: Slow operation: api_call took 623.1ms (threshold: 500.0ms)
```

---

### 2. `@profile_function` - Function Decorator

Automatically profile any function (sync or async).

```python
from agentic_fleet.utils import profile_function

@profile_function(threshold_ms=200)
def process_data(data):
    # expensive processing
    return result

@profile_function(threshold_ms=100)
async def fetch_from_api(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

---

### 3. `PerformanceTracker` - Advanced Statistics

Track multiple operations and generate statistics.

```python
from agentic_fleet.utils import PerformanceTracker

tracker = PerformanceTracker()

# Track operations
with tracker.track("operation1"):
    do_work()

with tracker.track("operation2"):
    do_more_work()

# Get statistics
stats = tracker.get_stats("operation1")
print(f"Average: {stats['avg_ms']:.1f}ms")
print(f"Min: {stats['min_ms']:.1f}ms, Max: {stats['max_ms']:.1f}ms")
print(f"Count: {stats['count']}")

# Log summary
tracker.log_summary()
```

**Output:**
```
INFO: Performance Summary:
INFO:   operation1: avg=125.3ms, min=98.2ms, max=167.8ms, count=5
INFO:   operation2: avg=234.7ms, min=201.1ms, max=289.3ms, count=3
```

---

### 4. Global Tracker - Convenience Functions

Use the global tracker for quick profiling without managing instances.

```python
from agentic_fleet.utils import (
    track_operation,
    get_performance_stats,
    log_performance_summary,
    reset_performance_stats,
)

# Track operations globally
with track_operation("workflow_execution"):
    run_workflow()

with track_operation("agent_processing"):
    process_with_agent()

# Get stats
all_stats = get_performance_stats()
workflow_stats = get_performance_stats("workflow_execution")

# Log summary
log_performance_summary()

# Reset when needed
reset_performance_stats()  # Reset all
reset_performance_stats("workflow_execution")  # Reset specific
```

---

## Practical Examples

### Example 1: Profile Configuration Loading

```python
from agentic_fleet.utils import timed_operation, load_config

def initialize_app():
    with timed_operation("load_config", threshold_ms=50):
        config = load_config()
    
    with timed_operation("initialize_agents", threshold_ms=200):
        agents = initialize_agents(config)
    
    return config, agents
```

### Example 2: Track API Endpoint Performance

```python
from agentic_fleet.utils import PerformanceTracker
from fastapi import FastAPI, Request

app = FastAPI()
tracker = PerformanceTracker()

@app.middleware("http")
async def track_request_performance(request: Request, call_next):
    endpoint = f"{request.method} {request.url.path}"
    
    with tracker.track(endpoint):
        response = await call_next(request)
    
    return response

@app.get("/stats")
async def get_stats():
    """Return performance statistics for all endpoints."""
    return tracker.get_all_stats()
```

### Example 3: Profile DSPy Reasoner Operations

```python
from agentic_fleet.utils import profile_function
from agentic_fleet.dspy_modules import DSPyReasoner

class ProfiledReasoner(DSPyReasoner):
    @profile_function(threshold_ms=300)
    async def analyze_task(self, task: str) -> dict:
        """Profile task analysis."""
        return await super().analyze_task(task)
    
    @profile_function(threshold_ms=500)
    async def route_to_agents(self, task: str, agents: list) -> dict:
        """Profile routing decisions."""
        return await super().route_to_agents(task, agents)
```

### Example 4: Workflow Optimization

```python
from agentic_fleet.utils import track_operation, log_performance_summary

async def run_optimized_workflow(task: str):
    with track_operation("workflow.analysis"):
        analysis = await analyze_task(task)
    
    with track_operation("workflow.routing"):
        routing = await route_task(analysis)
    
    with track_operation("workflow.execution"):
        result = await execute_task(routing)
    
    with track_operation("workflow.quality_check"):
        validated = await check_quality(result)
    
    # Log performance summary at end
    log_performance_summary()
    
    return validated
```

**Output:**
```
INFO: Performance Summary:
INFO:   workflow.analysis: avg=234.5ms, min=201.3ms, max=289.7ms, count=1
INFO:   workflow.routing: avg=456.2ms, min=456.2ms, max=456.2ms, count=1
INFO:   workflow.execution: avg=1234.8ms, min=1234.8ms, max=1234.8ms, count=1
INFO:   workflow.quality_check: avg=189.3ms, min=189.3ms, max=189.3ms, count=1
```

---

## Integration with OpenTelemetry

Combine profiling with OpenTelemetry tracing for production observability:

```python
from agentic_fleet.utils import timed_operation
from agentic_fleet.utils.telemetry import optional_span

async def traced_and_profiled_operation(data):
    with optional_span("operation", attributes={"data_size": len(data)}):
        with timed_operation("operation", threshold_ms=200):
            # Operation will be both traced AND profiled
            result = await process(data)
    return result
```

---

## Best Practices

### 1. Set Appropriate Thresholds

Choose thresholds based on operation expectations:

```python
# Fast operations (< 100ms expected)
with timed_operation("cache_lookup", threshold_ms=50):
    cached = cache.get(key)

# Medium operations (100-500ms expected)
with timed_operation("api_call", threshold_ms=300):
    response = api.get(url)

# Slow operations (> 500ms expected)
with timed_operation("model_inference", threshold_ms=1000):
    result = model.predict(input)
```

### 2. Track Related Operations

Group related operations for better insights:

```python
tracker = PerformanceTracker()

# Track each phase
with tracker.track("phase.analysis"):
    analyze()

with tracker.track("phase.routing"):
    route()

with tracker.track("phase.execution"):
    execute()

# Get phase breakdown
for phase in ["analysis", "routing", "execution"]:
    stats = tracker.get_stats(f"phase.{phase}")
    print(f"{phase}: {stats['avg_ms']:.1f}ms")
```

### 3. Reset Appropriately

Reset stats at natural boundaries:

```python
from agentic_fleet.utils import reset_performance_stats

# Reset at application startup
@app.on_event("startup")
async def startup():
    reset_performance_stats()

# Reset per-request in development
@app.middleware("http")
async def dev_reset(request, call_next):
    if settings.environment == "development":
        reset_performance_stats()
    return await call_next(request)
```

### 4. Use Debug Logging

Profile operations only log warnings by default. Enable debug logging to see all timings:

```python
import logging

# Enable debug logging for profiling
logging.getLogger("agentic_fleet.utils.profiling").setLevel(logging.DEBUG)
```

---

## Performance Optimization Workflow

1. **Identify bottlenecks:**
   ```python
   with track_operation("suspect_operation"):
       result = slow_function()
   ```

2. **Measure baseline:**
   ```python
   stats = get_performance_stats("suspect_operation")
   print(f"Baseline: {stats['avg_ms']:.1f}ms")
   ```

3. **Optimize:**
   ```python
   # Add caching, indexing, async operations, etc.
   ```

4. **Verify improvement:**
   ```python
   reset_performance_stats("suspect_operation")
   # Run again
   new_stats = get_performance_stats("suspect_operation")
   improvement = stats['avg_ms'] - new_stats['avg_ms']
   print(f"Improved by {improvement:.1f}ms ({improvement/stats['avg_ms']*100:.1f}%)")
   ```

---

## Debugging Slow Operations

### Finding the Slowest Parts

```python
from agentic_fleet.utils import PerformanceTracker

tracker = PerformanceTracker()

# Profile each subsection
with tracker.track("total"):
    with tracker.track("total.step1"):
        step1()
    
    with tracker.track("total.step2"):
        step2()
    
    with tracker.track("total.step3"):
        step3()

# Find the bottleneck
all_stats = tracker.get_all_stats()
slowest = max(all_stats.items(), key=lambda x: x[1]['avg_ms'])
print(f"Slowest operation: {slowest[0]} ({slowest[1]['avg_ms']:.1f}ms)")
```

### A/B Testing Optimizations

```python
from agentic_fleet.utils import PerformanceTracker

def compare_implementations():
    tracker = PerformanceTracker()
    
    # Test implementation A
    for _ in range(100):
        with tracker.track("impl_a"):
            implementation_a()
    
    # Test implementation B
    for _ in range(100):
        with tracker.track("impl_b"):
            implementation_b()
    
    # Compare
    stats_a = tracker.get_stats("impl_a")
    stats_b = tracker.get_stats("impl_b")
    
    print(f"Implementation A: {stats_a['avg_ms']:.1f}ms")
    print(f"Implementation B: {stats_b['avg_ms']:.1f}ms")
    
    if stats_b['avg_ms'] < stats_a['avg_ms']:
        improvement = (1 - stats_b['avg_ms']/stats_a['avg_ms']) * 100
        print(f"B is {improvement:.1f}% faster!")
```

---

## Related Documentation

- [Performance Optimization Recommendations](./PERFORMANCE_OPTIMIZATION.md)
- [OpenTelemetry Tracing](../README.md#observability)
- [Configuration Guide](../README.md#configuration)

---

*Last Updated: 2025-12-13*
