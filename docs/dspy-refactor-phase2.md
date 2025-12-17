# DSPy Refactor Phase 2: Integration of Decision Modules into Workflow Execution Paths

## Overview

Phase 2 completes the integration of Phase 1's compiled decision modules by wiring them into the actual workflow execution paths. Instead of using the DSPyReasoner's internal modules, the workflow now uses preloaded, compiled modules from `app.state` for routing, quality assessment, and tool planning.

## Goals Achieved

1. ✅ Extended SupervisorContext to hold decision module references
2. ✅ Added module injection API to DSPyReasoner (`set_decision_modules()`)
3. ✅ Wired decision modules from app.state through workflow initialization
4. ✅ Maintained backward compatibility with existing workflows
5. ✅ Added comprehensive tests for Phase 2 integration

## Architecture

### SupervisorContext Enhancement

**Location**: `src/agentic_fleet/workflows/context.py`

Added three new fields to hold preloaded decision modules:

```python
@dataclass
class SupervisorContext:
    # ... existing fields ...
    
    # Phase 2: Preloaded DSPy decision modules from app.state
    dspy_routing_module: Any | None = None
    dspy_quality_module: Any | None = None
    dspy_tool_planning_module: Any | None = None
```

These fields allow the context to carry decision modules from the API layer down to the workflow executors.

### DSPyReasoner Module Injection

**Location**: `src/agentic_fleet/dspy_modules/reasoner.py`

Added `set_decision_modules()` method to allow external decision modules to override internal ones:

```python
class DSPyReasoner(dspy.Module):
    def set_decision_modules(
        self,
        routing_module: Any | None = None,
        quality_module: Any | None = None,
        tool_planning_module: Any | None = None,
    ) -> None:
        """Inject external decision modules from Phase 2 integration."""
        if routing_module is not None:
            self._router = routing_module
        if quality_module is not None:
            self._quality_assessor = quality_module
        if tool_planning_module is not None:
            self._tool_planner = tool_planning_module
```

This allows preloaded, compiled modules to replace the reasoner's lazily-initialized modules.

### Workflow Initialization Integration

**Location**: `src/agentic_fleet/workflows/supervisor.py`

The `create_supervisor_workflow()` function now:

1. Accepts optional decision module parameters
2. Attaches them to the context
3. Injects them into the DSPy reasoner before building the workflow

```python
async def create_supervisor_workflow(
    *,
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
    mode: str = "standard",
    context: SupervisorContext | None = None,
    dspy_routing_module: Any | None = None,
    dspy_quality_module: Any | None = None,
    dspy_tool_planning_module: Any | None = None,
) -> SupervisorWorkflow:
    # ... initialization ...
    
    # Phase 2: Attach decision modules to context if provided
    if dspy_routing_module is not None:
        context.dspy_routing_module = dspy_routing_module
    # ... (similar for other modules)
    
    # Phase 2: Inject preloaded decision modules into DSPy reasoner
    if context.dspy_routing_module is not None or ...:
        context.dspy_supervisor.set_decision_modules(
            routing_module=context.dspy_routing_module,
            quality_module=context.dspy_quality_module,
            tool_planning_module=context.dspy_tool_planning_module,
        )
```

### FastAPI Lifespan Integration

**Location**: `src/agentic_fleet/api/lifespan.py`

The lifespan now passes preloaded decision modules to workflow creation:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Phase 1: Load compiled artifacts and decision modules
    artifact_registry = load_required_compiled_modules(...)
    quality_module = get_quality_module(artifact_registry.quality)
    routing_module = get_routing_module(artifact_registry.routing)
    tool_planning_module = get_tool_planning_module(artifact_registry.tool_planning)
    
    # Phase 2: Create workflow with preloaded decision modules
    workflow = await create_supervisor_workflow(
        dspy_routing_module=routing_module,
        dspy_quality_module=quality_module,
        dspy_tool_planning_module=tool_planning_module,
    )
    app.state.workflow = workflow
```

## Data Flow

### Before Phase 2

1. API startup: Load compiled artifacts into `app.state.dspy_*_module`
2. Workflow creation: Creates DSPyReasoner with internal modules
3. Execution: RoutingExecutor/QualityExecutor call `reasoner.route_task()` / `reasoner.assess_quality()`
4. These methods use the reasoner's internal modules (may be uncompiled/zero-shot)

### After Phase 2

1. API startup: Load compiled artifacts into `app.state.dspy_*_module`
2. Workflow creation: 
   - Creates DSPyReasoner
   - Injects preloaded modules via `set_decision_modules()`
3. Execution: RoutingExecutor/QualityExecutor call `reasoner.route_task()` / `reasoner.assess_quality()`
4. These methods now use **preloaded, compiled modules** from Phase 1

## Behavior Changes

### Before Phase 2
- Decision modules loaded at startup but not used by workflow
- Workflow used reasoner's internal modules (potentially zero-shot)
- Disconnect between preloaded modules and execution

### After Phase 2
- Decision modules loaded at startup **and** injected into workflow
- Workflow uses preloaded, compiled modules for decisions
- Consistent use of compiled artifacts throughout execution

## Benefits

1. **Performance**: Compiled modules from Phase 1 are now actually used during execution
2. **Consistency**: Single source of truth for decision modules (app.state)
3. **Fail-fast**: Phase 1's fail-fast enforcement now impacts actual execution
4. **Testing**: Decision modules can be easily mocked via context
5. **Observability**: Clear injection point for monitoring module usage

## Backward Compatibility

Phase 2 is fully backward compatible:

- If no decision modules are provided, workflow uses default behavior
- Existing workflows without Phase 1 artifacts continue to work
- API can run with `require_compiled: false` for development

## Testing

### Test Coverage

**File**: `tests/workflows/test_phase2_integration.py`

Tests cover:
- ✅ DSPyReasoner accepts and stores injected modules
- ✅ SupervisorContext holds decision module references
- ✅ `create_supervisor_workflow()` accepts module parameters
- ✅ Decision modules are properly injected into reasoner
- ✅ Backward compatibility without modules
- ✅ Partial module injection (only some modules provided)

### Running Tests

```bash
# Run Phase 2 integration tests
uv run pytest tests/workflows/test_phase2_integration.py -xvs

# Run all DSPy-related tests
uv run pytest tests/dspy_modules/ tests/api/test_lifespan_registry.py -xv
```

## Migration Guide

### For Development

No changes required. The system works with or without compiled artifacts:

1. Start API: `make backend`
2. Workflow uses zero-shot modules if no compiled artifacts exist
3. Workflow uses compiled modules if Phase 1 artifacts are present

### For Production

1. Ensure Phase 1 artifacts are compiled: `agentic-fleet optimize`
2. Enable fail-fast: Set `dspy.require_compiled: true` in config
3. Deploy with confidence that compiled modules are used end-to-end

### For Testing

Mock decision modules via context:

```python
from unittest.mock import MagicMock
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

mock_routing = MagicMock()
mock_quality = MagicMock()

workflow = await create_supervisor_workflow(
    dspy_routing_module=mock_routing,
    dspy_quality_module=mock_quality,
)
```

## Performance Considerations

### Latency
- ✅ No additional latency added - modules were already loaded in Phase 1
- ✅ Eliminates lazy initialization overhead during first execution
- ✅ Consistent performance across all requests

### Memory
- ✅ No additional memory - modules already in app.state from Phase 1
- ✅ Single instance per module shared across all requests
- ✅ Reduced memory compared to per-request module creation

## Future Phases

Phase 2 completes the core integration. Potential future enhancements:

- **Phase 3**: Advanced caching strategies for decision outputs
- **Phase 4**: Hot-swapping compiled modules without restart
- **Phase 5**: Multi-model routing with module versioning

## References

- [Phase 1 Documentation](./dspy-refactor-phase1.md)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
