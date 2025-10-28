# AGENTS.md

> README for AI coding agents working on **AgenticFleet**. This complements human-oriented `README.md` and provides actionable commands, conventions, and technical context. For detailed module guidance, see nested AGENTS.md files in subprojects.

---

## Project Overview

AgenticFleet is a **multi-agent orchestration system** built on Microsoft Agent Framework's "Magentic One" pattern. It features:

- **Architecture**: Manager (orchestrator) + specialist agents (researcher, coder, analyst)
- **Backend**: FastAPI with OpenAI Responses API compatibility, SSE streaming
- **Frontend**: React + Vite + TypeScript + shadcn/ui with real-time streaming UI
- **Key Features**: HITL approval gates, checkpointing, Mem0 memory, OpenTelemetry tracing
- **Languages**: Python 3.12+ (backend), TypeScript (frontend)
- **Package Manager**: **uv** for Python (NEVER use pip/venv directly), npm for frontend

**CRITICAL**: All Python commands must use `uv run` prefix. Configuration is YAML-first (never hardcode models/prompts in code).

---

## Quick Start for Agents

**Most common commands you'll need:**

```bash
# Setup (first time)
make install && make frontend-install

# Run full application (frontend + backend)
uv run agentic-fleet
# OR
make dev

# Run CLI only
uv run fleet

# Validate configuration (CRITICAL before commits)
make test-config

# Run tests
make test              # All tests
uv run pytest -k "test_name" -v  # Specific test

# Code quality checks (run before PR)
make check             # Lint + format + type-check
```

**Before any PR:**

1. Run `make test-config` to validate all configurations
2. Run `make check` to ensure code quality
3. Run relevant tests with `uv run pytest -k "relevant" -v`
4. Run `make validate-agents` to check documentation

---

## Quick Directory Map

```
AgenticFleet/
├── AGENTS.md               # This file - agent instructions
├── README.md               # User documentation
├── Makefile                # All dev commands (wraps uv)
├── pyproject.toml          # Python dependencies & config
├── src/
│   ├── agenticfleet/       # Core Python package
│   │   └── AGENTS.md       # Python package details
│   └── frontend/           # React UI
│       └── AGENTS.md       # Frontend details
├── tests/                  # Test suite
│   └── AGENTS.md          # Testing guide
├── config/                 # YAML configuration
└── var/                    # Runtime state (checkpoints, logs)
```

**Nested AGENTS.md files**:

- `src/agenticfleet/AGENTS.md` - Python package development
- `src/frontend/AGENTS.md` - Frontend development
- `tests/AGENTS.md` - Testing patterns

---

## Setup Commands

**Prerequisites**:

- Python 3.12+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 18+ (for frontend)
- OpenAI API key

**First-time setup**:

```bash
# Clone repo
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# Create .env file
echo "OPENAI_API_KEY=sk-YOUR-KEY-HERE" > .env

# Install backend
make install

# Install frontend
make frontend-install
```

**Environment variables** (`.env`):

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
ENABLE_OTEL=true                      # Enable OpenTelemetry
OTLP_ENDPOINT=http://localhost:4317   # OTLP collector
MEM0_HISTORY_DB_PATH=./var/mem0       # Memory storage
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

---

## Development Commands

**Always use Makefile targets** - they handle `uv run` correctly.

### Running the Application

```bash
# Primary commands
uv run agentic-fleet  # Full stack: backend (8000) + frontend (5173)
uv run fleet          # CLI/REPL only

# Alternative/component commands
make dev              # Same as agentic-fleet
make haxui-server     # Backend only (FastAPI + SSE)
make frontend-dev     # Frontend only (Vite)
```

### Testing

```bash
make test-config      # CRITICAL: Validate config after changes
make test             # Run all tests (slow)
make test-e2e         # End-to-end tests (requires make dev)

# Focused testing (faster)
uv run pytest tests/test_magentic_fleet.py -v
uv run pytest tests/test_config.py::test_researcher_agent -v
uv run pytest -k "orchestrator" -v
```

### Code Quality

```bash
make check            # All checks: lint + type-check
make lint             # Ruff linter
make format           # Ruff + Black formatting
make type-check       # mypy type checker
make validate-agents  # Validate AGENTS.md invariants
```

### Dependency Management

```bash
make install          # First-time setup
make sync             # Sync from lockfile
make frontend-install # Frontend deps
```

**CRITICAL**: Always prefix manual Python commands with `uv run`:

```bash
uv run pytest tests/test_config.py
uv run python -m agenticfleet
uv run mypy .
```

---

## Frontend Development

**Location**: `src/frontend/`

**Tech**: React 18 • TypeScript • Vite 7.1.12 • Tailwind CSS • shadcn/ui • Framer Motion 12.23.24 • TanStack Query

**Commands**:

```bash
cd src/frontend
npm run dev          # Dev server (port 5173 or 8080)
npm run build        # Production build
npm run build:dev    # Dev build (unminified)
npm run preview      # Preview built app
npm run lint         # ESLint
npm run lint:fix     # Auto-fix
npm run format       # Prettier
```

**Key Features**:

- Vite 7.x for ultra-fast HMR and builds
- Framer Motion for smooth layout and component animations
- Proper layout structure with MainLayout and ChatLayout
- Type-safe API integration with backend SSE streaming
- shadcn/ui component registry for consistent UI
- Comprehensive hook system for messages, approvals, and SSE

**Backend integration**:

- SSE streaming endpoint for real-time agent responses
- POST endpoints for approval decisions
- Event format follows OpenAI Responses API spec
- Do not change event shape without updating frontend parser

**See `src/frontend/AGENTS.md` for detailed frontend instructions**

---

## Agent System

**Agents**: orchestrator (manager), researcher, coder, analyst

**Key principles**:

- ❌ **NEVER hardcode model names** - always load from `agents/<role>/config.yaml`
- ✅ Tools return Pydantic models from `agenticfleet.core.code_types`
- ✅ Manager executes PLAN → EVALUATE → ACT → OBSERVE loop
- ✅ Limits configured in `config/workflow.yaml`: `max_round_count`, `max_stall_count`, `max_reset_count`

**Adding a new agent**:

1. Scaffold structure:

   ```bash
   mkdir -p src/agenticfleet/agents/<role>/tools
   touch src/agenticfleet/agents/<role>/{agent.py,config.yaml,__init__.py}
   ```

2. Create factory in `agents/<role>/agent.py`:

   ```python
   def create_<role>_agent() -> ChatAgent:
       """Create the <role> agent with tools."""
       settings = Settings()
       config = settings.load_agent_config("<role>")
       client = OpenAIResponsesClient(model_id=config["model"])
       # Load tools from config...
       return ChatAgent(name=config["name"], model_client=client, ...)
   ```

3. Configure in `agents/<role>/config.yaml`:

   ```yaml
   name: "<Role> Agent"
   model: "gpt-5" # NEVER hardcode in Python
   system_prompt: "You are a specialist..."
   tools:
     - name: tool_name
       enabled: true
   ```

4. Register:

   - Export in `agents/__init__.py`
   - Wire into `fleet/fleet_builder.py`
   - Update manager instructions in `config/workflow.yaml`

5. Validate: `make test-config`

**Adding a tool**:

1. Implement in `agents/<role>/tools/<tool>.py` returning Pydantic model
2. Add to `agents/<role>/config.yaml` under `tools`
3. Reference in agent's `system_prompt`
4. Add unit test
5. Run `make test-config`

---

## Configuration Management

**Priority hierarchy**:

1. **YAML** (workflow + per-agent) - canonical behavior & prompts
2. **Environment Variables** (`.env`) - secrets, toggles
3. **Code** - only wiring & factories; avoid logic overrides

**Key files**:

- `config/workflow.yaml` - Manager instructions, callbacks, HITL, checkpointing
- `agents/<role>/config.yaml` - Model, system prompt, tools, runtime flags
- `.env` - API keys & feature flags (never commit secrets)

**CRITICAL**: Run after ANY configuration change:

```bash
make test-config
```

---

## Human-in-the-Loop (HITL)

**Purpose**: Approval gates for sensitive operations (code execution, file ops, etc.)

**Handlers**:

- CLI: `core/cli_approval.py` (terminal prompts)
- Web: `haxui/web_approval.py` (SSE events + POST endpoint)

**Tool pattern**:

```python
from agenticfleet.core.approval import ApprovalRequest, ApprovalDecision

request = ApprovalRequest(
    operation_type="code_execution",
    description="Execute Python code",
    details={"code": "print('hello')"},
    timeout_seconds=300
)

response = await approval_handler.request_approval(request)

if response.decision == ApprovalDecision.APPROVE:
    # Execute
    ...
```

**Rule**: Never bypass approval checks when operation is in `require_approval_for` list in workflow config.

---

## Checkpointing & Memory

**Checkpointing**: Saves workflow state to resume/replay (reduces LLM costs 50-80%)

- Storage: File (`./var/checkpoints`) or In-Memory (tests)
- Resume: `resume_from_checkpoint=<id>` in fleet run
- Enable via `FleetBuilder.with_checkpointing(storage)`

**Memory (Mem0)**: Optional long-term memory via Azure AI Search + embeddings

- Provider: `context/mem0_provider.py`
- Requires: `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_OPENAI_*` env vars
- Status: Exported but not yet wired into prompts

---

## Observability

**Callbacks** (`fleet/callbacks.py`):

- `streaming_agent_response_callback` - Stream agent outputs
- `plan_creation_callback` - Log manager plans
- `progress_ledger_callback` - Track progress evaluations
- `tool_call_callback` - Monitor tool executions
- `final_answer_callback` - Capture results

**OpenTelemetry tracing**:

- Enable: `ENABLE_OTEL=true`
- Endpoint: `OTLP_ENDPOINT=http://localhost:4317`
- Sensitive data: `ENABLE_SENSITIVE_DATA=true` (captures prompts/completions)

**Rule**: When adding events, ensure shape consistency & update CLI and frontend consumers.

---

## Testing

**Test files**:

- `tests/test_config.py` - Configuration validation (CRITICAL after config changes)
- `tests/test_magentic_fleet.py` - 14 core orchestration tests
- `tests/test_haxui_api.py` - FastAPI endpoint tests
- `tests/test_*.py` - Other unit/integration tests
- `tests/e2e/` - Playwright end-to-end tests

**Common commands**:

```bash
# CRITICAL: After config/YAML changes
make test-config

# All tests (slow)
make test

# Focused testing (PREFERRED)
uv run pytest tests/test_magentic_fleet.py -v
uv run pytest tests/test_config.py::test_researcher_agent -v
uv run pytest -k "orchestrator" -v

# Coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# E2E (requires `make dev` running)
make test-e2e
```

**Testing rules**:

- Run `make test-config` after modifying YAML / env / tool imports
- Prefer focused pytest invocations (`-k`, single file, single test) for speed
- Mock external LLM/tool network calls (patch `OpenAIResponsesClient`)
- Use `asyncio_mode=auto`; do NOT add `@pytest.mark.asyncio`
- Coverage targets: core >80%, tools >70%, config validation 100%

**See `tests/AGENTS.md` for detailed testing guidance**

---

## Code Quality

**Backend standards**:

- Formatting: Black (100 char lines) + Ruff (imports, pyupgrade)
- Typing: Python 3.12 syntax (`Type | None`, never `Optional[Type]`)
- Custom exceptions from `core/exceptions.py`
- Logging via `core/logging.get_logger` (no stray prints in production code)
- Tool return schemas must remain stable (Pydantic models in `core/code_types.py`)

**Frontend standards**:

- ESLint (+ React hooks & refresh plugins)
- Prettier for formatting
- Tailwind + shadcn/ui guidelines (utility-first class merging)

**Commands**:

```bash
# Backend
make lint        # Ruff linter
make format      # Ruff fix + Black
make type-check  # mypy
make check       # All checks (lint + type)

# Frontend
cd src/frontend
npm run lint
npm run lint:fix
npm run format
```

**Before committing**: Run `make check` and `make test-config`

---

## Build & Deployment

**Backend**: Wheel/sdist via `hatchling` (see `pyproject.toml`)
**Frontend**: Vite builds to `src/frontend/dist/`

**Typical CI sequence**:

1. `uv sync` (install)
2. `make test-config`
3. `make check`
4. `make test`
5. Frontend: `npm ci && npm run build`
6. Package: `uv build`

**CI considerations**: Cache uv / node_modules, matrix Python 3.12/3.13, separate lint/type/test jobs

---

## Security

**Critical practices**:

- Never commit secrets (`.env` is ignored). Rotate API keys if exposed.
- Enforce approval for code/file/network side-effects
- Validate external input through Pydantic models
- Keep dependencies updated (`make sync` + `uv sync`)
- Consider scanning (Bandit / pip-audit) in CI

**Sensitive surfaces**:

- Code execution tool
- File system access (if future tools added)
- Network requests (research or custom tools)

---

## Troubleshooting

| Symptom                    | Likely Cause                  | Action                                                                             |
| -------------------------- | ----------------------------- | ---------------------------------------------------------------------------------- |
| Agent config test failing  | Missing key in YAML           | Compare with working agent YAML & rerun `make test-config`                         |
| Model mismatch / hardcoded | Hardcoded model in factory    | Replace with YAML-driven value                                                     |
| Tool output parsing errors | Schema drift                  | Align tool return with `core/code_types.py`                                        |
| Infinite loop suspicion    | Manager not terminating       | Inspect progress ledger callback, adjust `max_round_count` / improve plan criteria |
| Frontend not streaming     | SSE endpoint mismatch or CORS | Verify FastAPI logs & network tab; ensure backend at expected port                 |
| Approval events ignored    | Handler not passed to fleet   | Confirm builder `.with_approval_handler()` invocation                              |
| Checkpoint not resuming    | Wrong ID or path              | List checkpoint files in `var/checkpoints` & pass correct ID                       |

---

## Quick Command Reference

```bash
# Setup
make install && make frontend-install

# Run application
uv run agentic-fleet  # Full stack (frontend + backend)
uv run fleet          # CLI/REPL only
make dev              # Same as agentic-fleet

# Component-specific
make haxui-server     # Backend only
make frontend-dev     # Frontend only

# Config validation (CRITICAL after changes)
make test-config

# Focused test
uv run pytest tests/test_magentic_fleet.py::test_fleet_builder_with_agents -v

# Quality checks
make check && make test

# Frontend build
cd src/frontend && npm run build

# Coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Validate AGENTS docs
make validate-agents
```

---

## Invariants (DO NOT VIOLATE)

**Critical rules**:

- All Python execution via `uv run` (including tests & lint)
- No hardcoded model IDs; always load from YAML
- Tool outputs MUST be Pydantic models from `core/code_types.py`
- Approval required operations must respect handler decisions
- Configuration changes require `make test-config` before commit/PR
- Run `make validate-agents` before opening PR to ensure docs are up to date

---

## Extension Ideas

Potential safe automation tasks:

- Generate agent skeleton given a role name
- Auto-update manager instructions when adding agent
- Add schema validation for YAML via Pydantic model
- Implement memory injection into prompts

---

## References

- **Root README**: `README.md` - User documentation
- **Package detail**: `src/agenticfleet/AGENTS.md` - Python package development
- **Frontend detail**: `src/frontend/AGENTS.md` - Frontend development
- **Tests detail**: `tests/AGENTS.md` - Testing patterns
- **Architecture**: `docs/architecture/` - System design
- **Features**: `docs/features/` - Feature guides
- **Contributing**: `docs/project/CONTRIBUTING.md`
- **Security**: `SECURITY.md`

---

**Keep this file current** – Update alongside structural or workflow changes. Autonomous agents should treat missing updates here as a signal to request maintenance.
