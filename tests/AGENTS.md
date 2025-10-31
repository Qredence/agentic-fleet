# AGENTS.md

## Overview

The `tests/` directory houses backend API, workflow, memory, and integration tests. Suites rely on uv-managed environments and heavy mocking of OpenAI/Mem0 clients. Never call the Pytest CLI directly—use `uv run pytest` (or `make test`) so the correct interpreter and dependency graph load.

## Structure

- `test_api_*.py` — FastAPI endpoints (health, chat, SSE) with HTTPX async clients.
- `test_workflow*.py` — Workflow factory coverage and orchestration behaviour.
- `test_memory_system.py` — Mem0 provider regression tests.
- `test_backend_e2e.py` & `tests/e2e` — Playwright-backed end-to-end checks (require backend/frontend running).
- `test_improvements.py` — Regression tests for bugfixes collected from production issues.

## Running Tests

- Full suite: `uv run pytest -q` (or `make test`).
- Focused module: `uv run pytest tests/test_api_conversations.py -k happy_path`.
- With coverage: `uv run pytest --cov=src/agentic_fleet --cov-report=term-missing`.
- Configuration validation: `uv run python tests/test_config.py` (invoked via `make test-config`).
- Playwright e2e: start stack (`make dev`), then `uv run python tests/e2e/playwright_test_workflow.py` or `make test-e2e`.

## Guidelines

- Mock external services—look at fixtures under `tests/conftest.py` (planned) or existing mocks in individual files.
- Prefer async tests with `@mark.asyncio` (import `mark` from Pytest) when hitting FastAPI routes.
- Keep tests deterministic; avoid time-based sleeps and rely on event polling utilities when needed.
- Every new tool or workflow should ship with validation tests that ensure the YAML-based factory can instantiate it.
- Update this AGENTS file whenever you add a new suite or adjust the runtime assumptions (ports, env vars, etc.).
