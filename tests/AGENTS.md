# AGENTS.md

## Overview

The `tests/` tree exercises FastAPI routers, workflow orchestration, SSE streaming, CLI utilities, and
load scenarios. Run everything through the uv environment (`uv run …`) or the Makefile wrappers (`make
test`, `make load-test-smoke`, etc.) to guarantee consistent dependencies. External calls to OpenAI or
agent-framework services are faked so the suite stays offline and deterministic.

## Suite Map

- **API & SSE**
  - `test_api_health.py`, `test_api_conversations.py`, `test_api_entities.py`, `test_api_sse.py` —
    REST surface verification via HTTPX async clients.
  - `test_api_responses.py`, `test_api_responses_streaming.py`, `test_server_conversations.py` —
    OpenAI Responses compatibility, SSE contract, and streaming edge cases.
- **Workflow & Orchestration**
  - `test_workflow_factory.py`, `test_workflow.py`, `test_magentic_backend_integration.py`,
    `test_magentic_integration.py`, `test_event_bridge.py`, `test_utils_events.py` — YAML resolution,
    agent instantiation, event bridging, and Magentic execution paths.
  - `test_response_aggregator.py` — Aggregator correctness for streaming/non-streaming responses.
  - `test_backward_compatibility.py`, `test_config.py` — Legacy import shims and workflow configuration
    smoke checks.
- **Runtime & Tooling**
  - `test_console.py`, `test_static_file_serving.py`, `test_chat_schema_and_workflow.py`,
    `test_entity_discovery_service.py`, `test_error_handling.py`, `test_improvements.py`,
    `test_improvement_implementation.py`, `test_automation.py`, `validate_test_improvements.py`.
  - Memory integrations: `test_memory_system.py`.
  - Quality reporting docs: `test_quality_analysis_report.md` (documentation-backed assertions).
- **Load Testing**
  - `tests/load_testing/` hosts k6 + Locust harnesses (`run_load_tests.py`, `k6-chat-test.js`, Grafana
    dashboards). Requires a running backend (`make backend` or `make dev`).
- **End-to-End**
  - `test_backend_e2e.py` exercises Playwright scenarios. Both backend and frontend must be running via
    `make dev` before launching `make test-e2e`.

## Running Tests

- Full backend suite: `make test` (wraps `uv run pytest -v`).
- Focus a module: `uv run pytest tests/test_api_responses_streaming.py -k happy_path`.
- Coverage: `uv run pytest --cov=src/agentic_fleet --cov-report=term-missing`.
- Workflow smoke: `make test-config` instantiates `WorkflowFactory` and ensures YAML + imports resolve.
- Load testing:
  1. Start the API (`make backend` or `make dev`).
  2. Execute `make load-test-smoke`, `make load-test-load`, or `make load-test-stress`.
  3. View dashboards with `make load-test-dashboard`.
- Playwright E2E: run `make test-e2e` after both services are up; install Playwright browsers if
  prompted.

## Authoring Guidelines

- Decorate async tests with `@pytest.mark.asyncio` and reuse shared HTTPX fixtures defined per module.
- Stub outbound network I/O. Use in-module fixtures or helper factories to fake OpenAI, Mem0, and tool
  integrations.
- Keep tests deterministic: prefer polling utilities over `sleep`, seed any randomness, and assert on
  structured payloads (never string contains).
- Co-locate fixtures near their usage; avoid monolithic `conftest.py` files.
- New workflows must include tests proving `WorkflowFactory().create_from_yaml(...)` succeeds and that
  `ResponseAggregator` emits the expected events.
- After editing this documentation or adding suites, run `make validate-agents`.

## When to Update This File

- Adding or renaming test modules, fixtures, or load scenarios.
- Adjusting Makefile targets or introducing new commands (e.g. Playwright flags, coverage modes).
- Changing workflow IDs, agent names, or SSE schema that tests cover.
- Updating documentation-backed assertions (`test_quality_analysis_report.md`) or tooling guidance.
