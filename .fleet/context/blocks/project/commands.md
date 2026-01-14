---
label: project-commands
description: Build, test, lint, and dev commands for this project. Reference for all development tasks.
limit: 3000
scope: project
updated: 2024-12-29
---

# Project Commands

## Development

```bash
# Start full dev environment (backend :8000 + frontend :5173)
make dev

# Backend only
make backend

# Frontend only
make frontend-dev

# Run CLI
make run
```

## Testing

```bash
# Full test suite
make test

# Config smoke test
make test-config

# Frontend tests
make test-frontend

# E2E tests (requires dev servers running)
make test-e2e
```

## Quality

```bash
# Lint and format check
make lint

# Auto-format
make format

# Type check
make type-check

# All quality checks
make check
```

## Build

```bash
# Build frontend
make build-frontend

# Install all dependencies
make install

# Install frontend deps
make frontend-install

# Install pre-commit hooks
make pre-commit-install
```

## Cache & Cleanup

```bash
# Clear DSPy cache
make clear-cache
```

## Python Commands

Always use `uv run` prefix:

```bash
uv run python -m agentic_fleet
uv run pytest tests/
uv run ruff check src/
```
