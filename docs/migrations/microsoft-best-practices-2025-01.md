# Microsoft Agent Framework Best Practices Migration

**Date**: 2025-01-14
**Status**: Completed
**Impact**: Low-risk improvements to fleet module

## Overview

Applied Microsoft Agent Framework best practices to improve robustness, observability, and checkpoint stability in the AgenticFleet codebase. All changes follow official patterns from Microsoft Learn documentation and microsoft/agent-framework repository.

## Changes Applied

### 1. Agent Name Validation for Checkpoint Stability

**File**: `src/agenticfleet/fleet/magentic_fleet.py`
**Lines**: 98-108
**Rationale**: Microsoft documentation emphasizes stable participant names for checkpoint compatibility.

```python
# Validate agent names for checkpoint stability (Microsoft best practice)
expected_names = {"researcher", "coder", "analyst"}
if self.checkpoint_storage and not set(agents.keys()).issuperset(expected_names):
    logger.warning(
        "Agent names %s differ from expected %s. "
        "Checkpointing may fail when resuming with mismatched participant names.",
        list(agents.keys()),
        list(expected_names),
    )
```

**Impact**: Prevents silent checkpoint failures when agent names change between runs.

### 2. Exception Handling Wrapper for Callbacks

**File**: `src/agenticfleet/fleet/fleet_builder.py`
**Lines**: 257-272
**Rationale**: Callback exceptions should not break the workflow. Wrap event handling to catch and log errors.

```python
async def unified_callback(event: MagenticCallbackEvent) -> None:
    """
    Route MagenticCallbackEvents to appropriate handlers.
    Wraps event handling in exception handler to prevent callback errors
    from breaking workflow.
    """
    try:
        await _handle_event(event)
    except Exception as exc:
        logger.error(f"Error in unified callback: {exc}", exc_info=True)

async def _handle_event(event: MagenticCallbackEvent) -> None:
    """Internal event handler for routing events to console callbacks."""
    # ... existing routing logic
```

**Impact**: Workflow continues even if console callbacks encounter errors (e.g., formatting issues, IO failures).

### 3. Complete event.kind Handling

**File**: `src/agenticfleet/fleet/fleet_builder.py`
**Lines**: 273-292
**Rationale**: Microsoft documentation shows orchestrator emits multiple event kinds: `task_ledger`, `progress_ledger`, `notice`, `user_task`, `instruction`.

```python
elif event.kind == "user_task" and event.message:
    # Log user task requests
    task_text = str(event.message)
    await self.console_callbacks.notice_callback(
        f"Task received: {task_text[:100]}..."
    )
elif event.kind == "instruction" and event.message:
    # Log manager instructions to agents
    instruction_text = str(event.message)
    await self.console_callbacks.notice_callback(
        f"Manager instruction: {instruction_text[:100]}..."
    )
```

**Impact**: Complete observability for all orchestrator messages, not just plans and progress ledgers.

### 4. Workflow Exception Handler

**File**: `src/agenticfleet/fleet/fleet_builder.py`
**Lines**: 310-316
**Rationale**: Microsoft's official example includes `on_exception` handler for workflow-level errors.

```python
# Add exception handler for workflow errors (Microsoft best practice)
def on_exception(exception: Exception) -> None:
    """Handle exceptions that occur during workflow execution."""
    logger.error(f"Workflow exception occurred: {exception}", exc_info=True)

self.builder = self.builder.on_exception(on_exception)
```

**Impact**: Centralized error logging for workflow execution failures.

### 5. Enhanced Module Documentation

**File**: `src/agenticfleet/fleet/__init__.py`
**Lines**: 1-115
**Rationale**: Comprehensive documentation matching Microsoft patterns helps developers understand architecture.

**Additions**:

- Architecture overview with MagenticManager, MagenticOrchestratorExecutor, MagenticAgentExecutor
- Usage examples for default and custom fleet creation
- Event-driven observability documentation
- Exception handling patterns
- Checkpointing guidelines with stable participant names
- HITL integration notes
- Links to official Microsoft resources

**Impact**: New contributors can quickly understand fleet architecture without reading implementation code.

## Validation

All changes verified with:

```bash
# Type safety
uv run mypy src/agenticfleet/fleet/
# Success: no issues found in 4 source files

# Code quality
uv run ruff check src/agenticfleet/fleet/
# All checks passed!

# Configuration compatibility
uv run python tests/test_config.py
# Overall: 6/6 tests passed
```

## References

- **Microsoft Learn**: https://learn.microsoft.com/en-us/azure/ai-services/agents/
- **Agent Framework GitHub**: https://github.com/microsoft/agent-framework
- **Official Example**: Complete Magentic workflow with all handlers
- **DeepWiki Queries**: MagenticBuilder patterns, streaming events, callback modes

## Migration Notes

**Backwards Compatibility**: ✅ All changes are additive or internal improvements
**Breaking Changes**: None
**Configuration Changes**: None required
**Dependencies**: No new dependencies

## Next Steps

1. Monitor logs for `"Agent names differ"` warnings when using custom agent dictionaries
2. Verify callback exception handling in production workflows
3. Consider exposing `event.kind` filtering in `workflow.yaml` for user customization
4. Document checkpoint resume patterns with stable participant names

## Lessons Learned

1. **Exception isolation**: Wrap all callback and handler logic to prevent cascading failures
2. **Name stability**: Participant names affect checkpoint serialization keys—document this clearly
3. **Complete event handling**: Handle all documented event kinds to avoid silent data loss
4. **Follow official patterns**: Microsoft's examples include non-obvious best practices (e.g., `on_exception`)
5. **Documentation value**: Comprehensive module docs reduce onboarding time significantly
