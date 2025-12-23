# DSPy Refactor Phase 1: Compiled Artifact Registry & Typed Decision Modules

## Overview

Phase 1 introduces a centralized registry system for compiled DSPy artifacts with fail-fast enforcement at application startup. This ensures that production deployments always have required compiled modules available, preventing degraded performance from zero-shot fallback behavior.

## Goals Achieved

1. ✅ Added compiled DSPy artifact registry with fail-fast enforcement
2. ✅ Introduced typed, independently-loadable DSPy decision modules
3. ✅ Wired lifespan startup to preload modules and attach them to app state
4. ✅ Maintained WebSocket streaming latency (no blocking quality evaluation)
5. ✅ Preserved existing workflow behavior (no breaking API changes)

## Architecture

### Compiled Artifact Registry

**Location**: `src/agentic_fleet/dspy_modules/compiled_registry.py`

The registry provides centralized loading and validation of compiled DSPy modules:

```python
from agentic_fleet.dspy_modules.compiled_registry import load_required_compiled_modules

# Load all required compiled modules
registry = load_required_compiled_modules(
    dspy_config=config.get("dspy", {}),
    require_compiled=True  # Fail-fast if artifacts missing
)

# Access loaded modules
routing_module = registry.routing
quality_module = registry.quality
tool_planning_module = registry.tool_planning
```

**Key Features**:

- Fail-fast enforcement when `require_compiled=True`
- Path resolution across multiple base directories (repo root, package root, cwd)
- Detailed error messages with instructions for fixing missing artifacts
- Validation helper to check which artifacts are loaded

### Typed Decision Modules

**Location**: `src/agentic_fleet/dspy_modules/decisions/`

Three independently-loadable modules using typed Pydantic signatures (DSPy >= 3.0.3):

#### 1. Routing Decision Module

**File**: `decisions/routing.py`

Handles task routing and agent assignment:

```python
from agentic_fleet.dspy_modules.decisions import get_routing_module

module = get_routing_module(compiled_module)
result = module.forward(
    task="User task",
    team="Available agents",
    context="Execution context",
    current_date="2025-01-01",
    available_tools="Tool1, Tool2"
)
```

#### 2. Tool Planning Module

**File**: `decisions/tool_planning.py`

Generates tool usage plans:

```python
from agentic_fleet.dspy_modules.decisions import get_tool_planning_module

module = get_tool_planning_module(compiled_module)
result = module.forward(
    task="Task requiring tools",
    available_tools="Tool1, Tool2",
    context="Optional context"
)
```

#### 3. Quality Assessment Module

**File**: `decisions/quality.py`

Evaluates answer quality:

```python
from agentic_fleet.dspy_modules.decisions import get_quality_module

module = get_quality_module(compiled_module)
result = module.forward(
    task="Original task",
    result="Agent's answer"
)
```

### FastAPI Lifespan Integration

**Location**: `src/agentic_fleet/api/lifespan.py`

The lifespan context manager now:

1. Loads workflow configuration
2. Attempts to load all required compiled artifacts
3. Fails fast if `require_compiled=True` and artifacts are missing
4. Attaches loaded artifacts and decision modules to `app.state` for reuse
5. Cleans up resources on shutdown

**App State Variables**:

- `app.state.dspy_artifacts` - ArtifactRegistry instance
- `app.state.dspy_quality_module` - Quality assessment module
- `app.state.dspy_routing_module` - Routing decision module
- `app.state.dspy_tool_planning_module` - Tool planning module

## Configuration

**Location**: `src/agentic_fleet/src/agentic_fleet/config/workflow_config.yaml`

New configuration keys added under `dspy:`:

```yaml
dspy:
  # Existing config
  compiled_reasoner_path: .var/cache/dspy/compiled_reasoner.json
  require_compiled: false # Set to true for production

  # Phase 1: Compiled artifact paths for decision modules
  compiled_routing_path: .var/cache/dspy/compiled_routing.json
  compiled_tool_planning_path: .var/cache/dspy/compiled_tool_planning.json
  compiled_quality_path: .var/logs/compiled_answer_quality.pkl
```

## Behavior Changes

### Before Phase 1

- Missing compiled artifacts → Warning logged + fallback to zero-shot/heuristic
- No centralized artifact management
- No fail-fast enforcement

### After Phase 1

- Missing required artifacts + `require_compiled=True` → Application fails to start with clear error message
- Centralized artifact registry tracks all loaded modules
- Fail-fast enforcement prevents production deployments with missing artifacts
- Decision modules preloaded and available via `app.state`

## Migration Guide

### For Development

No changes required. The default `require_compiled: false` allows the application to start without compiled artifacts (using fallback behavior).

### For Production

1. Compile DSPy modules: `agentic-fleet optimize`
2. Enable fail-fast: Set `dspy.require_compiled: true` in `workflow_config.yaml`
3. Deploy with confidence that compiled artifacts are present

### For Testing

Tests can mock the registry:

```python
from unittest.mock import MagicMock
from agentic_fleet.dspy_modules.compiled_registry import ArtifactRegistry

mock_registry = ArtifactRegistry(
    routing=MagicMock(),
    quality=MagicMock(),
    tool_planning=MagicMock()
)
```

## Performance Considerations

### Latency

- ✅ No impact on WebSocket streaming latency
- ✅ Background quality evaluation remains async (uses `asyncio.to_thread()`)
- ✅ Decision modules loaded once at startup (not per-request)
- ✅ Routing cache in reasoner continues to work

### Memory

- Minimal: Decision modules loaded once and cached
- Registry holds references to ~3-4 modules (negligible overhead)

## Testing

### Test Coverage

- **Registry Loading**: `tests/dspy_modules/test_compiled_registry.py`
  - Tests fail-fast behavior
  - Tests lenient mode (require_compiled=False)
  - Tests path resolution

- **Decision Modules**: `tests/dspy_modules/test_decisions.py`
  - Tests module initialization
  - Tests forward passes
  - Tests caching behavior

- **Lifespan Integration**: `tests/api/test_lifespan_registry.py`
  - Tests successful artifact loading
  - Tests fail-fast on missing artifacts
  - Tests error handling

### Running Tests

```bash
# Run all Phase 1 tests
make test

# Run specific test files
pytest tests/dspy_modules/test_compiled_registry.py -v
pytest tests/dspy_modules/test_decisions.py -v
pytest tests/api/test_lifespan_registry.py -v
```

## Troubleshooting

### Application fails to start: "Required compiled DSPy artifacts not found"

**Cause**: `require_compiled=true` but compiled artifacts are missing

**Solution**:

1. Run `agentic-fleet optimize` to compile modules
2. OR set `dspy.require_compiled: false` in config (not recommended for production)

### Quality evaluation using heuristic fallback

**Cause**: Quality module not compiled or failed to load

**Check**:

1. Verify `compiled_quality_path` exists
2. Check application logs for loading errors
3. Run compilation: `agentic-fleet gepa-optimize`

### Path resolution issues

**Cause**: Compiled artifact paths are not being found

**Solution**:

1. Use absolute paths in config
2. OR ensure artifacts are in one of the searched base directories:
   - Repository root
   - Package root
   - Module directory
   - Current working directory

## Future Phases

Phase 1 establishes the foundation for:

- **Phase 2**: Integration of decision modules into workflow execution
- **Phase 3**: Compilation pipeline improvements
- **Phase 4**: Advanced caching and optimization strategies

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
