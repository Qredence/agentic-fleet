## .github/copilot-instructions.md — quick agent guide

These short instructions help AI coding agents become productive in this repository.

- Big picture
  - Backend: YAML-driven multi-agent orchestrator in `src/agenticfleet/` (manager/orchestrator + specialist agents). Core runner, workflows and API live here.
  - Frontend: React HaxUI in `src/frontend/` that consumes FastAPI SSE endpoints (`src/agenticfleet/server.py`, `src/agenticfleet/haxui/api.py`).

- Canonical developer workflows
  - Install & sync: `make install` then `uv sync`
  - Run full stack (dev): `make dev` or `uv run agentic-fleet`
  - Backend only: `make backend` or `uv run python -m agenticfleet`
  - Validate YAML configs (CRITICAL after edits): `make test-config` (runs `uv run python tests/test_config.py`)
  - Run tests: `uv run pytest <file or -k pattern>` (tests mock LLMs; avoid real API calls in CI)
  - Quality checks: `make check`, `make format`, `make type-check`

- Project-specific conventions (must follow)
  - uv-first: always prefix Python commands with `uv run` (project uses uv for dependency management; do not use pip/venv directly).
  - YAML-first: behavior, prompts, models and tools are driven by YAML. Edit `src/agenticfleet/agents/<role>/config.yaml` and `src/agenticfleet/config/workflow.yaml` — do not hardcode model IDs or prompts in Python.
  - Tool return contracts: all tools must return Pydantic models defined in `src/agenticfleet/core/code_types.py`. Rely on these types when parsing tool outputs.
  - Approval/HITL: use `src/agenticfleet/core/approval.py` helpers and respect `human_in_the_loop` config in `config/workflow.yaml`. Do not bypass approval gates.
  - Type policy: codebase targets Python 3.12 — use explicit type hints and `Type | None` for optional types.

- Where to change things (concrete files)
  - Add/modify an agent: `src/agenticfleet/agents/<role>/{agent.py,config.yaml,tools/}`; export factory in `src/agenticfleet/agents/__init__.py`.
  - Orchestrator / builder: `src/agenticfleet/fleet/fleet_builder.py` and `src/agenticfleet/magentic_fleet.yaml`.
  - Workflow & limits: `src/agenticfleet/config/workflow.yaml` (max_round_count, max_stall_count, approval rules).
  - Checkpointing/state: `var/checkpoints/` and `src/agenticfleet/persistance/`.
  - SSE / frontend integration: `src/agenticfleet/haxui/api.py`, `src/frontend/src/` types.

- Quick code patterns (examples to copy)
  - Agent factory: returns a ChatAgent wired to an OpenAIResponsesClient using model from YAML — see any `src/agenticfleet/agents/*/agent.py`.
  - Tool implementation: return a Pydantic BaseModel for deterministic downstream parsing (models in `core/code_types.py`).
  - Approval request: use `create_approval_request()` and check `ApprovalDecision` enum from `core/approval.py`.

- Environment & secrets
  - Required env: `OPENAI_API_KEY`, `REDIS_URL`.
  - Optional: `ENABLE_OTEL`, `OTLP_ENDPOINT`, `MEM0_HISTORY_DB_PATH`.
  - `.env` is used by `config/settings.py`; do not commit secrets.

- Tests & CI notes
  - Tests mock external LLM clients — keep mocks when writing tests. CI avoids real API calls.
  - Run focused tests locally (prefer `uv run pytest tests/test_x.py -k name`) rather than entire suite for speed.
  - CI steps reference: `make check`, `make test-config`, `make test`.

- If unsure where to look
  - Start with these files: `src/agenticfleet/AGENTS.md`, root `AGENTS.md`, `config/workflow.yaml`, `src/agenticfleet/agents/`, and `tests/test_config.py`.

If any section needs more file-level examples (agents, tools, approval flow, frontend SSE), tell me which area and I will expand the file with targeted snippets.

# AI Agent Instructions for AgenticFleet

## Quick Context: What This Is

AgenticFleet is a **multi-agent orchestration system** built on Microsoft Agent Framework's Magentic One pattern. A manager agent (the orchestrator) breaks tasks into plans, then dynamically delegates to specialist agents (researcher, coder, analyst) that execute with specific tools. The system now supports **dynamic agent spawning** for on-demand specialist creation, with full observability via callbacks, state persistence through checkpointing, and human control via approval gates.

**Version**: 0.5.5 | **Tech**: Python 3.12+, React 18+, TypeScript | **Package Manager**: uv (Python), npm (frontend)

## Architecture & Orchestration

- **Magentic Fleet Pattern**: AgenticFleet uses Microsoft's Magentic One pattern with intelligent planning via `MagenticFleet` in `src/agenticfleet/fleet/magentic_fleet.py`. The manager creates structured plans, evaluates progress, and dynamically delegates to specialist agents. Run with `agentic-fleet` or call `create_default_fleet()`.
- **Dynamic Agent Spawning**: NEW in v0.5.5 - The `DynamicOrchestrationManager` (`src/agenticfleet/workflows/dynamic_orchestration/`) enables on-demand creation of specialized agents based on task analysis. Supports 6 models (gpt-5, gpt-5-codex, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini) with intelligent model selection for different task types (code generation, security review, research).
- **Fleet structure**: Manager orchestrates specialist agents via `FleetBuilder` in `fleet/fleet_builder.py`. Builder pattern chains `.with_manager()`, `.with_agents()`, `.with_dynamic_orchestration()`, `.with_checkpointing()`, `.with_callbacks()` to construct the workflow.
- **Agent types**: Two categories:
  - **Static agents**: Core specialists (orchestrator, researcher, coder, analyst) defined at startup
  - **Dynamic agents**: Foundation agents (planner, executor, generator, verifier) spawned on-demand with task-specific configurations
- **Agent factories**: Each specialist lives under `src/agenticfleet/agents/*/agent.py`. Factories wrap `ChatAgent` with `OpenAIResponsesClient(model_id=...)` and optional tools. Never use deprecated `OpenAIChatClient`.
- **Configuration hierarchy**: Manager settings in `src/agenticfleet/config/workflow.yaml` under `fleet.manager` (model, instructions). Per-agent configs in `agents/<role>/config.yaml` (name, model, system_prompt, tools). Dynamic orchestration config in `workflow.yaml` under `dynamic_orchestration` (model_pool, foundation_agents, spawn_limits). Global settings (API keys, endpoints) load from `.env` via `config/settings.py`.
- **Entry points**: Three ways to run: (1) `uv run agentic-fleet` (full stack: FastAPI backend + React frontend), (2) `uv run fleet` (CLI/REPL only), (3) `make dev` (full stack development mode with auto-reload).
- **Legacy removed**: Custom `MultiAgentWorkflow` and `workflow_builder.py` have been deleted. The `workflows` module now re-exports `MagenticFleet` and `create_default_fleet()` for compatibility.

## Critical Patterns & Developer Conventions

- **uv-first**: ALL Python commands MUST prefix with `uv run` (e.g., `uv run pytest`, `uv run python -m agenticfleet`). Project uses **uv** for dependency management, not pip/venv. See `Makefile` for canonical commands.
- **Model naming**: Respect per-agent `model` in `agents/<role>/config.yaml`; never hardcode models. Current default is `gpt-5-mini` (orchestrator/researcher/analyst) with model-specific overrides per agent. Preserve preview model names during refactoring.
- **YAML as source of truth**: All configuration is declarative in YAML files, not code. When changing agent behavior, edit `agents/<role>/config.yaml` first (system_prompt, tools list, model, temperature, max_tokens). Never override via factory code.
- **Tool return types**: All tools return Pydantic models (`CodeExecutionResult`, `WebSearchResponse`, `DataAnalysisResponse`, `VisualizationSuggestion`) from `core/code_types.py`. This ensures downstream agents can parse outputs reliably. New tools must follow this pattern.
- **Approval flow design**: When adding approval-required operations (code execution, file ops, sensitive APIs), wrap in `create_approval_request()` helper and check `ApprovalDecision` enum (approve/reject/modify). Never bypass approval checks when configured.
- **Type safety**: Python 3.12+ type hints required everywhere. Use `Type | None` instead of `Optional[Type]`. All function parameters and returns must have explicit types.

## Magentic Workflow Cycle

1. **PLAN**: Manager analyzes task, gathers known facts, identifies gaps, creates action plan with clear steps
2. **EVALUATE**: Manager creates progress ledger (JSON) checking: request satisfied? infinite loop? making progress? Selects next agent and provides specific instruction
3. **ACT**: Selected specialist executes with its tools, returns findings
4. **OBSERVE**: Manager reviews response, updates context, decides next action
5. **REPEAT**: Continues until complete or limits reached: `max_round_count: 30`, `max_stall_count: 3` (triggers replan), `max_reset_count: 2` (complete restart)

Configure limits in `workflow.yaml` under `fleet.orchestrator`. Adjust based on task complexity and cost tolerance.

## Essential Developer Workflows

### Running & Testing

## Copilot / AI agent quick instructions — AgenticFleet (concise)

AgenticFleet is a Magentic One style multi-agent orchestrator (Python backend + React frontend). This file is a compact, actionable guide for AI coding agents to be productive immediately.

Key ideas

- Orchestrator (Magentic) coordinates Plans → Evaluate → Act → Observe. Core code lives under `src/agenticfleet/`.
- Config (YAML) is authoritative: `src/agenticfleet/config/workflow.yaml` and `src/agenticfleet/agents/*/config.yaml` drive models, prompts, tools and runtime flags.
- Python tooling is `uv`-first. Always run Python commands with `uv run` (see Makefile tasks).

Fast entry commands (examples to run or test locally)

- Start full stack (backend + frontend): `uv run agentic-fleet` or `make dev`
- CLI only: `uv run fleet`
- Validate configs after YAML changes: `uv run python tests/test_config.py`
- Run focused tests: `uv run pytest tests/test_magentic_fleet.py -k "orchestrator"`
- Quality checks before commit: `make check` (lint + format + mypy)

Project conventions an agent must respect

- Never hardcode model IDs in Python — read from `agents/<role>/config.yaml`.
- Tools return Pydantic schemas from `src/agenticfleet/core/code_types.py` (tools live in `agents/<role>/tools/`). Keep schemas stable.
- Sensitive operations require HITL approval via `src/agenticfleet/core/approval.py` and `approved_tools.py` wrappers. Do not bypass approval logic.
- Checkpointing persists workflow state to `var/checkpoints/`. Use `FleetBuilder.with_checkpointing()` to wire storage.

Where to change behavior safely

- Prompts, model, tools: edit `src/agenticfleet/agents/<role>/config.yaml` (YAML-first).
- Manager instructions and orchestration flags: `src/agenticfleet/config/workflow.yaml`.
- Add an agent: scaffold `src/agenticfleet/agents/<role>/{agent.py,config.yaml,tools/__init__.py}` and export factory in `agents/__init__.py`.

Quick reference files

- Orchestrator / builder: `src/agenticfleet/fleet/`
- Agent factories and tools: `src/agenticfleet/agents/`
- HITL, approval types: `src/agenticfleet/core/approval.py`
- Pydantic tool types: `src/agenticfleet/core/code_types.py`
- FastAPI SSE endpoints used by frontend: `src/agenticfleet/haxui/api.py`
- Config tests: `tests/test_config.py`

Testing & CI notes

- Tests mock the LLM client (see tests) — avoid hitting real APIs in CI.
- CI uses `make check` + `make test-config` + `make test` (see `.github/workflows/ci.yml`).

If you need to modify code

- Keep changes minimal and type-hinted (Python 3.12). Use `Type | None` for optional types.
- Add or update focused tests in `tests/` and run them with `uv run pytest`.

When unsure, read these docs first: `src/agenticfleet/AGENTS.md`, `AGENTS.md` at repo root, and `docs/features/magentic-fleet.md`.

If this summary misses anything you expect, tell me which area (running, testing, agents, tools, approvals, frontend) and I will expand the section with concrete file-level examples.
