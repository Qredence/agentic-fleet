# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Overview

**AgenticFleet** is a multi-agent orchestration system built on Microsoft Agent Framework's Magentic One pattern. It features a manager-executor architecture where specialized agents (orchestrator, researcher, coder, analyst) collaborate on complex tasks through structured planning and dynamic delegation. The system provides three interfaces: a React web frontend (default), a rich CLI, and Jupyter notebooks for experimentation.

## Key Commands

### Setup & Dependencies

```bash
# First-time setup (Python + frontend)
make install && make frontend-install

# Update dependencies after lockfile changes
make sync

# Validate configuration (CRITICAL after any YAML changes)
make test-config
```

### Development

```bash
# Full stack development (backend on :8000, frontend on :5173)
make dev

# Backend only
make haxui-server

# Frontend only
make frontend-dev

# Run the CLI application
uv run fleet
```

### Code Quality

```bash
# Run all quality checks (lint + type-check)
make check

# Individual checks
make lint          # Ruff linting
make format        # Black + Ruff formatting
make type-check    # MyPy strict checks

# Run tests
make test
```

## Architecture Overview

### Core Pattern: Magentic One Workflow

1. **PLAN** - Manager analyzes task, creates structured action plan
2. **EVALUATE** - Progress ledger checks: satisfied? in loop? who acts next?
3. **ACT** - Selected specialist executes with domain-specific tools
4. **OBSERVE** - Manager reviews response, updates context
5. **REPEAT** - Continue until completion or limits reached

### Agent Specialists

- **Orchestrator**: Task planning & result synthesis (`gpt-5`)
- **Researcher**: Information gathering & citations (`gpt-5`)
- **Coder**: Code generation & analysis (`gpt-5-codex`)
- **Analyst**: Data exploration & insights (`gpt-5`)

### Configuration Files

- **Workflow Config**: [`src/agenticfleet/config/workflow.yaml`](src/agenticfleet/config/workflow.yaml) - Global orchestration settings
- **Agent Configs**: [`src/agenticfleet/agents/*/config.yaml`](src/agenticfleet/agents) - Per-agent configuration
- **Frontend Config**: [`src/frontend/package.json`](src/frontend/package.json) - React app dependencies and scripts
- **Project Config**: [`pyproject.toml`](pyproject.toml) - Python dependencies, tool configs, and project metadata

### Technology Stack

- **Backend**: Python 3.12+, Microsoft Agent Framework, FastAPI, Pydantic
- **Frontend**: React 18.3+, TypeScript, Vite, shadcn/ui, Tailwind CSS
- **Package Management**: `uv` for Python, npm for frontend
- **Communication**: Server-Sent Events (SSE) for real-time streaming

## Critical Development Patterns

### uv-First Workflow

ALL Python commands MUST use `uv run` prefix:

- `uv run python -m agenticfleet` (not `python main.py`)
- `uv run pytest` (not `pytest`)
- `uv run python tests/test_config.py`

### Configuration-Driven Architecture

- **YAML is source of truth** - All agent behavior in `agents/<role>/config.yaml`
- **Never hardcode models** - Read from config files
- **Manager instructions** in `config/workflow.yaml` under `fleet.manager`
- **Environment variables** via `.env` for API keys

### Tool Development Pattern

1. Tools live under `agents/<role>/tools/`
2. Return Pydantic models from `core/code_types.py`
3. Enable/disable via agent config `tools` list
4. For sensitive operations, use HITL approval via `approved_tools.py`

### Agent Factory Pattern

```python
def create_<role>_agent() -> ChatAgent:
    config = settings.load_agent_config("<role>")
    return ChatAgent(
        name=config["name"],
        model=config["model"],
        system_prompt=config["system_prompt"],
        client=OpenAIResponsesClient(model_id=config["model"]),
        tools=[...tools from config...],
    )
```

## Configuration Hierarchy

1. **Global settings**: `.env` (API keys, endpoints)
2. **Workflow config**: `config/workflow.yaml` (manager, orchestrator, callbacks)
3. **Agent configs**: `agents/<role>/config.yaml` (prompts, tools, models)
4. **Runtime settings**: Loaded via `config/settings.py`

## Testing Patterns

### Configuration Validation

ALWAYS run after YAML changes:

```bash
uv run python tests/test_config.py
```

This validates env vars, agent structure, tool imports, and factory callables.

### Test Organization

- `tests/test_config.py` - Configuration validation
- `tests/test_magentic_fleet.py` - 14 core orchestration scenarios
- `tests/test_mem0_context_provider.py` - Memory integration
- Mock `OpenAIResponsesClient` to avoid API costs in tests

### Running Specific Tests

```bash
# Run specific test
uv run pytest tests/test_config.py::test_orchestrator_agent -v

# Run with filter
uv run pytest tests/test_magentic_fleet.py -k "test_orchestrator"

# Run end-to-end tests (requires dev server)
make test-e2e

# Run configuration validation only
make test-config
```

## Human-in-the-Loop (HITL)

### Approval System

- Configuration: `workflow.yaml` → `human_in_the_loop.enabled`
- Core interfaces: `core/approval.py` (ApprovalRequest, ApprovalResponse)
- Tools requiring approval: code_execution, file_operations, external_api_calls
- Use `create_approval_request()` helper for approval flows

## State Persistence

### Checkpointing

- Reduces 50-80% retry costs by avoiding redundant LLM calls
- Configure in `workflow.yaml` under `checkpointing`
- Storage types: File (persistent) or InMemory (testing)
- Auto-resume: `resume_from_checkpoint=<id>` in `MagenticFleet.run()`

## Frontend Architecture

### Key Components

- `ChatContainer.tsx` - Main chat UI
- `useFastAPIChat.ts` - SSE streaming hook
- API proxy: Vite config routes `/api/*` to backend `:8000`

### Development Commands

```bash
cd src/frontend
npm run dev        # Development server (port 5173)
npm run build      # Production build
npm run build:dev  # Development build
npm run lint       # ESLint
npm run lint:fix   # ESLint with auto-fix
npm run format     # Prettier formatting
npm run preview    # Preview production build
```

## Production Readiness

### Type Safety Standards

- **100% mypy compliance** required across all code
- Use `Type | None` instead of `Optional[Type]`
- Explicit type annotations for all function parameters and returns
- Use `# type: ignore` sparingly with justification comments

### Code Quality Gates

All quality checks must pass before commits:

```bash
make check          # Lint + format + type-check (all must pass)
make test-config    # Configuration validation (6/6 tests must pass)
make test           # Full test suite
make validate-agents  # Validate AGENTS.md documentation invariants
```

### Production Deployment Checklist

- ✅ All type errors resolved (current: 0 errors across 83 files)
- ✅ Configuration validation passes
- ✅ HITL approval system configured for sensitive operations
- ✅ Checkpointing enabled for cost optimization
- ✅ OpenTelemetry tracing configured
- ✅ Environment variables properly set

## Common Pitfalls to Avoid

❌ **Hardcoding models** - Always read from `agents/<role>/config.yaml`
❌ **Bypassing YAML config** - Move behavior to config, not Python code
❌ **Using `python` directly** - Always use `uv run` prefix
❌ **Skipping config validation** - Run `make test-config` after YAML changes
❌ **Tool schema mismatches** - Ensure Pydantic models match across codebase
❌ **Type safety violations** - Never commit with mypy errors
❌ **Missing HITL approvals** - Configure approval for code execution, file ops

✅ **Before committing** - Run `make check`, `make test-config`, `make test`
✅ **Type safety first** - Fix all mypy errors before PR
✅ **Configuration validation** - Always validate after YAML changes
✅ **Defensive programming** - Use proper type guards and error handling

## Recent v0.5.4 Improvements

### Modular Architecture Patterns

- **Planner-Executor-Verifier-Generator**: Complete modular workflow system
- **Workflow as Agent**: Reflection and retry pattern with Worker/Reviewer agents
- **Type Safety**: 100% mypy compliance with strict typing enforcement
- **Production Patterns**: Error handling, logging, and observability best practices

### New Development Workflows

```bash
# Validate everything before development
make test-config && make check

# Development with type safety
uv run python -m agenticfleet  # Always use uv run

# Test specific components
uv run pytest tests/test_magentic_fleet.py -k "test_orchestrator"

# HITL approval demo
make demo-hitl

# Clean development environment
make clean
```

### Performance Optimizations

- **Checkpointing**: 50-80% cost reduction on retries
- **Streaming**: Real-time SSE responses for better UX
- **Caching**: Intelligent response caching where appropriate
- **Resource Management**: Proper cleanup and resource disposal

## File Structure Reference

### Backend Core

- `src/agenticfleet/fleet/magentic_fleet.py` - Main orchestrator
- `src/agenticfleet/fleet/fleet_builder.py` - Builder pattern
- `src/agenticfleet/config/settings.py` - Configuration management
- `src/agenticfleet/core/` - Core types and utilities

### Frontend Core

- `src/frontend/src/lib/use-fastapi-chat.ts` - SSE integration
- `src/frontend/src/components/ChatContainer.tsx` - Main UI
- `src/frontend/vite.config.ts` - Build configuration

### Configuration

- [`config/workflow.yaml`](src/agenticfleet/config/workflow.yaml) - Global workflow settings
- [`agents/*/config.yaml`](src/agenticfleet/agents) - Per-agent configuration
- [`pyproject.toml`](pyproject.toml) - Python dependencies and tool config
- [`src/frontend/package.json`](src/frontend/package.json) - Frontend dependencies
- [`Makefile`](Makefile) - Development commands and build automation
