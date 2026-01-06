---
label: project-commands
description: Build, test, lint, and dev commands for this project. Reference for all development tasks.
limit: 3000
scope: project
updated: 2024-12-30
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

# CLI direct invocation
agentic-fleet run -m "your task"
agentic-fleet optimize
agentic-fleet eval
```

## Testing

```bash
# Full test suite
make test

# Fast tests (parallel, no slow markers)
make test-fast

# Config smoke test
make test-config

# Frontend tests
make test-frontend

# E2E tests (requires dev servers running)
make test-e2e

# Single test
uv run pytest tests/path/test_file.py::test_name
```

## Quality

```bash
# Lint and format check
make lint

# Auto-format
make format

# Type check
make type-check

# All quality checks (fast, run before commits)
make check

# Full QA (lint + format + type + all tests)
make qa
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

# Install enhanced git hooks
make hooks-install

# Install all hooks
make setup-hooks

# Full development setup
make dev-setup
```

## Hooks

```bash
# Install all hooks (pre-commit + enhanced)
make setup-hooks

# Install enhanced git hooks only
make hooks-install

# Update hooks to latest version
make hooks-update

# Remove enhanced git hooks
make hooks-uninstall
```

## DSPy & Optimization

```bash
# Clear DSPy cache (after modifying signatures)
make clear-cache

# Run GEPA optimization
agentic-fleet optimize

# Evaluate history
make evaluate-history
```

## Tracing

```bash
# Start Jaeger tracing (UI at :16686)
make tracing-start

# Stop tracing
make tracing-stop
```

## Python Commands

Always use `uv run` prefix:

```bash
uv run python -m agentic_fleet
uv run pytest tests/
uv run ruff check src/
```
