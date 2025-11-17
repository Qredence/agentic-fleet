# Contributing Guide

## Development Setup

1. Clone the repository
2. (Optional) Create virtual environment: `uv python -m venv venv && source venv/bin/activate`
3. From the repo root, install dependencies via uv: `uv sync`
4. Verify the CLI: `uv run agentic-fleet --help`

## Code Style

- **Formatting**: Use `black` with the project config (`pyproject.toml`)
- **Linting**: Use `ruff` (configured in `pyproject.toml`)
- **Type Checking**: Use `mypy` (Python 3.12 target; config in `pyproject.toml`)
- **Naming**: snake_case for functions, PascalCase for classes

## Testing

- Run tests: `make test` (or `uv run pytest -v`)
- Run a specific test: `uv run pytest -q tests/workflows/test_supervisor_workflow.py::test_name`
- With coverage: `uv run pytest --cov=src --cov-report=term-missing`
- Tests use `pytest-asyncio` for async tests

## Code Organization

- `src/` - Source code (package root)
- `tests/` - Test files
- `config/` - Configuration files
- `data/` - Training data
- `examples/` - Example scripts
- `docs/` - Documentation
- `scripts/` - Utility scripts

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
from src.workflows.supervisor_workflow import SupervisorWorkflow
```

## Adding New Features

### Adding a New Agent

1. Add config in `config/workflow_config.yaml` under `agents:`
2. Instantiate in `supervisor_workflow.py:_create_agents()` using factory method
3. Add to team description in `_get_supervisor_instructions()`
4. Add training examples in `data/supervisor_examples.json`

### Adding a New DSPy Signature

1. Define in `src/dspy_modules/signatures.py`
2. Add ChainOfThought wrapper in `supervisor.py:__init__`
3. Create method to call it (follow pattern of `route_task`, `analyze_task`)

### Adding a New Tool

1. Implement `ToolProtocol` in `src/tools/<name>.py`
2. Register in `supervisor_workflow.py:_create_agents()` when creating agents
3. Tool will be automatically registered in `ToolRegistry`

## Commit Messages

- Use imperative mood: "Add feature" not "Added feature"
- Conventional prefixes optional but encouraged
- Ensure tests pass before committing

## Pull Requests

1. Ensure all tests pass: `PYTHONPATH=. uv run pytest -q`
2. Run formatter: `uv run black --line-length 100 .`
3. Run linter: `uv run flake8`
4. Run type checker: `uv run mypy`
5. Update documentation if needed

## Documentation

- Update `README.md` for user-facing changes
- Update `docs/developers/architecture.md` for architectural changes
- Add docstrings to all public functions/classes
- Use Google/NumPy style docstrings
