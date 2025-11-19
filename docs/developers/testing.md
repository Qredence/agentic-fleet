# Testing Guide

## Overview

The DSPy-Enhanced Agent Framework uses pytest with async support for comprehensive testing. Tests are organized by module and include unit tests, integration tests, and edge case coverage.

## Running Tests

### Basic Test Execution

```bash
# Run all tests (with PYTHONPATH for proper module resolution)
PYTHONPATH=. uv run pytest -q tests/

# Run with verbose output
PYTHONPATH=. uv run pytest -v tests/

# Run specific test file
PYTHONPATH=. uv run pytest tests/workflows/test_supervisor_workflow.py

# Run specific test
PYTHONPATH=. uv run pytest tests/workflows/test_supervisor_workflow.py::test_run_falls_back_to_available_agent
```

### With Coverage

```bash
# Run tests with coverage report
PYTHONPATH=. uv run pytest --cov=src --cov-report=term-missing tests/

# Generate HTML coverage report
PYTHONPATH=. uv run pytest --cov=src --cov-report=html tests/
# View: open htmlcov/index.html
```

### Test Categories

**Unit Tests**:

- `tests/dspy_modules/` - DSPy module tests
- `tests/utils/` - Utility function tests

**Integration Tests**:

- `tests/workflows/` - Full workflow tests

**Comprehensive Tests**:

- `tests/workflows/test_supervisor_workflow_comprehensive.py` - Edge cases and error scenarios

## Test Structure

### Test Organization

```
tests/
├── conftest.py                 # Shared fixtures and stubs
├── dspy_modules/
│   └── test_tool_aware_supervisor.py
├── utils/
│   ├── test_config_loader.py
│   └── test_tool_registry.py
└── workflows/
    ├── test_supervisor_workflow.py
    ├── test_supervisor_enhancements.py
    └── test_supervisor_workflow_comprehensive.py
```

### Test Fixtures

Key fixtures from `conftest.py`:

**Stubs** (for testing without full dependencies):

- `ChatAgent`: Stub agent that doesn't require external API
- `DSPySupervisor`: Stub supervisor for controlled testing
- `OpenAI`: Stub OpenAI client
- `dspy`: Stub DSPy module

**Usage**:

```python
from tests.workflows.test_supervisor_workflow import DummyAgent, StubDSPySupervisor

@pytest.mark.asyncio
async def test_my_feature():
    workflow = SupervisorWorkflow()
    workflow.agents = {"Writer": DummyAgent("Writer")}
    workflow.dspy_supervisor = StubDSPySupervisor(routing={...})

    result = await workflow.run("test task")
    assert result is not None
```

## Writing Tests

### Test Template

```python
import pytest
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

@pytest.mark.asyncio
async def test_feature_name():
    """Test that feature works correctly."""
    # Arrange
    workflow = await create_supervisor_workflow(compile_dspy=False)

    # Act
    result = await workflow.run("test task")

    # Assert
    assert result is not None
    assert "expected" in str(result)
```

### Testing Async Code

All workflow tests must be marked as async:

```python
@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality."""
    workflow = await create_supervisor_workflow(compile_dspy=False)

    result = await workflow.run("task")
    assert result is not None
```

### Testing Streaming

```python
@pytest.mark.asyncio
async def test_streaming():
    """Test streaming functionality."""
    # Set up with DummyAgent to avoid NotImplementedError (requires mocking _create_agents or similar)
    # For simple template, we just show usage:
    workflow = await create_supervisor_workflow(compile_dspy=False)

    # Inject dummy agents if needed for offline testing
    # workflow.agents = {"Writer": DummyAgent("Writer")}

    events = []
    async for event in workflow.run_stream("task"):
        events.append(event)

    assert len(events) > 0
    assert hasattr(events[-1], "data")
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_error_handling():
    """Test that errors are handled correctly."""
    from agentic_fleet.workflows.exceptions import AgentExecutionError
    from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

    workflow = await create_supervisor_workflow(compile_dspy=False)

    # This assumes _execute_delegated is accessible or testing public API failure
    # For public API testing:
    # await workflow.run("Trigger Failure")
```

### Testing Configuration

```python
def test_config_validation():
    """Test configuration validation."""
    from src.utils.config_schema import validate_config
    from src.workflows.exceptions import ConfigurationError

    invalid_config = {"dspy": {"temperature": 5.0}}  # Out of range

    with pytest.raises(ConfigurationError):
        validate_config(invalid_config)
```

## Test Coverage Goals

- **Overall**: 60%+ coverage
- **Core workflows**: 80%+ coverage
- **Utilities**: 70%+ coverage
- **Edge cases**: All critical error paths tested

## Continuous Integration

Tests run automatically on:

- Every push to main branch
- Every pull request
- Multiple Python versions (3.10, 3.11, 3.12)

See `.github/workflows/ci.yml` for CI configuration.

## Test Best Practices

1. **Use stubs** from conftest.py to avoid external API calls
2. **Mock history saves** to avoid file I/O: `workflow.history_manager.save_execution = lambda x: "test.jsonl"`
3. **Test one thing** per test function
4. **Use descriptive names**: `test_feature_behavior_expected_outcome`
5. **Include docstrings** explaining what is being tested
6. **Clean up** after tests (restore original state)
7. **Avoid sleep()** in async tests (use proper await patterns)

## Debugging Failed Tests

### View detailed output

```bash
PYTHONPATH=. uv run pytest -vv tests/failing_test.py
```

### Run with logging

```bash
PYTHONPATH=. uv run pytest tests/failing_test.py --log-cli-level=DEBUG
```

### Use pytest debugger

```bash
PYTHONPATH=. uv run pytest --pdb tests/failing_test.py
```

### Check test isolation

```bash
# Run test in isolation
PYTHONPATH=. uv run pytest tests/specific_test.py::test_name

# Run with fresh state
PYTHONPATH=. uv run pytest --cache-clear tests/
```

## Common Test Patterns

### Testing Task Validation

```python
def test_validate_task_empty():
    from src.workflows.supervisor_workflow import _validate_task

    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_task("")
```

### Testing Routing Normalization

```python
@pytest.mark.asyncio
async def test_routing_normalization():
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    invalid_routing = {"assigned_to": ["Invalid"], "mode": "wrong"}
    normalized = workflow._normalize_routing_decision(invalid_routing, "task")

    assert normalized["mode"] in ["parallel", "sequential", "delegated"]
    assert all(agent in workflow.agents for agent in normalized["assigned_to"])
```

### Testing Tool Registry

```python
def test_tool_registration():
    from src.utils.tool_registry import ToolRegistry

    registry = ToolRegistry()
    # Test registration logic
    assert registry is not None
```
