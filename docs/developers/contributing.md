# Contributing Guide

## Development Setup

1. Clone the repository
2. From the repo root, install dependencies: `make install`
3. Install frontend deps (if needed): `make frontend-install`
4. Verify the CLI: `uv run agentic-fleet --help`

## Code Style

- **Formatting**: Use `make format` (Ruff)
- **Linting**: Use `make lint` (Ruff)
- **Type Checking**: Use `ty` (Python 3.12 target; config in `pyproject.toml`)
- **Naming**: snake_case for functions, PascalCase for classes

## Testing

- Run tests: `make test` (or `uv run pytest -v`)
- Run a specific test: `uv run pytest -q tests/workflows/test_supervisor_workflow.py::test_name`
- With coverage: `uv run pytest --cov=src --cov-report=term-missing`
- Tests use `pytest-asyncio` for async tests

## Code Organization

- `src/` - Source code (package root)
- `tests/` - Test files
- `src/agentic_fleet/config/` - Configuration files
- `src/agentic_fleet/data/` - Training data
- `examples/` - Example scripts
- `docs/` - Documentation
- `src/agentic_fleet/scripts/` - Utility scripts

## Import Organization

Follow PEP 8 import order:

1. Standard library imports
2. Third-party imports
3. Local imports

Group with comments:

```python
# Standard library imports
import os
from pathlib import Path

# Third-party imports
import typer
from rich import Console

# Local imports
from agentic_fleet.workflows import SupervisorWorkflow
```

## Adding New Features

### Adding a New Agent

1. Add config in `src/agentic_fleet/config/workflow_config.yaml` under `agents:`
2. Instantiate in `agents/coordinator.py:_create_agent()` using factory method
3. Add to team description in `reasoner.py:get_execution_summary()`
4. Add training examples in `src/agentic_fleet/data/supervisor_examples.json`

### Adding a New DSPy Signature

1. Define in `src/agentic_fleet/dspy_modules/signatures.py`
2. Add ChainOfThought wrapper in `reasoner.py:__init__`
3. Create method to call it (follow pattern of `route_task`, `analyze_task`)

### Adding a New Tool

1. Implement `ToolProtocol` in `src/agentic_fleet/tools/<name>.py`
2. Register in `agents/coordinator.py` when creating agents
3. Tool will be automatically registered in `ToolRegistry`

## Commit Messages

- Use imperative mood: "Add feature" not "Added feature"
- Conventional prefixes optional but encouraged
- Ensure tests pass before committing

## Pull Requests

1. Ensure all tests pass: `make test`
2. Run formatter: `make format`
3. Run linter/type checks: `make check`
4. Update documentation if needed

## Documentation

- Update `README.md` for user-facing changes
- Update `docs/developers/architecture.md` for architectural changes
- Add docstrings to all public functions/classes
- Use Google/NumPy style docstrings
