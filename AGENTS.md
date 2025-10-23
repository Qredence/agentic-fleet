# AGENTS.md

> Agent-focused operational guide for the **AgenticFleet** repository. This complements (not duplicates) the human‑oriented `README.md` and the package / test scoped `src/agenticfleet/AGENTS.md` and `tests/AGENTS.md`. Use this file as the single entry point for autonomous / semi‑autonomous coding agents.

---

## 1. Project Overview

AgenticFleet is a **multi‑agent orchestration system** implementing the Microsoft Agent Framework "Magentic One" pattern with: planner/orchestrator + specialist executor agents (researcher, coder, analyst), optional long‑term memory (Mem0), human‑in‑the‑loop approval gates, checkpointed workflow state, a FastAPI backend (OpenAI Responses API compatible), and a modern React (Vite + shadcn/ui + Tailwind CSS) frontend consuming SSE event streams.

Key characteristics:

- Python 3.12+, dependency management with **uv** (DO NOT use pip/venv directly)
- Declarative **YAML-first configuration** for agents & workflow
- Agents use `OpenAIResponsesClient` (Azure/OpenAI Response API format) returning **Pydantic models** for tool outputs
- Human approval (HITL) for sensitive operations (code execution, file access, etc.)
- OpenTelemetry instrumentation & callback observability
- Checkpointing to reduce LLM cost (resume & replay)
- Frontend real-time streaming + approval UI

---

## 2. Quick Directory Map (High Signal Only)

```
├── AGENTS.md                # (this file) agent operational guide
├── README.md                # human overview
├── Makefile                 # canonical dev commands (wraps uv)
├── pyproject.toml           # project + tool config
├── src/
│   ├── agenticfleet/        # core Python package (see src/agenticfleet/AGENTS.md)
│   └── frontend/            # React + Vite + Tailwind UI
├── tests/                   # pytest suite (see tests/AGENTS.md)
├── var/                     # runtime artifacts (checkpoints, logs, memories)
└── docs/ (referenced in README)  # architecture / guides (not fully enumerated here)
```

Supporting per‑area AGENTS docs:

- `src/agenticfleet/AGENTS.md` – deep Python package & module guidance
- `tests/AGENTS.md` – test strategy, execution patterns

---

## 3. Environment & Setup

### 3.1 Prerequisites

- Python 3.12+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 18+ (for frontend)
- OpenAI (or Azure OpenAI) API key in `.env`

### 3.2 Bootstrap

```bash
# Clone
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# Environment file (create if missing)
cp .env.example .env  # add OPENAI_API_KEY=...

# Backend dependencies (wraps uv install path logic via Makefile) – preferred
make install          # or: uv sync

# Frontend dependencies
make frontend-install # or: (cd src/frontend && npm install)
```

If `.env.example` is absent, create `.env` with at minimum:

```bash
OPENAI_API_KEY=sk-REPLACE_ME
```

Optional variables (set only if needed):

```bash
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
MEM0_HISTORY_DB_PATH=./var/mem0
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

---

## 4. Core Development Workflow

Always prefer **Makefile targets** (they handle `uv run` correctly).

| Action                | Command (Preferred)     | Notes                                     |
| --------------------- | ----------------------- | ----------------------------------------- |
| Install backend deps  | `make install`          | First-time only; shows next steps         |
| Sync deps             | `make sync`             | Matches lock state                        |
| Install frontend deps | `make frontend-install` | Installs under `src/frontend`             |
| Full stack dev        | `make dev`              | Backend (8000) + Frontend (5173)          |
| Backend only          | `make haxui-server`     | FastAPI + SSE API                         |
| Frontend only         | `make frontend-dev`     | Vite dev server                           |
| Run app (CLI)         | `make run`              | Invokes `python -m agenticfleet`          |
| Config validation     | `make test-config`      | CRITICAL after YAML/env changes           |
| Tests (all)           | `make test`             | Pytest suite (slow; focus tests normally) |
| Lint                  | `make lint`             | Ruff only                                 |
| Format                | `make format`           | Ruff fix + Black                          |
| Type check            | `make type-check`       | mypy (strict-ish)                         |
| All quality           | `make check`            | Lint + type (formatting is non-blocking)  |
| E2E tests             | `make test-e2e`         | Requires dev servers running              |

Manual variants: always prefix Python commands with `uv run` (e.g., `uv run pytest ...`).

---

## 5. Frontend (React + Vite) Workflow

Location: `src/frontend/`

Scripts (from `package.json`):

| Script              | Purpose                                                |
| ------------------- | ------------------------------------------------------ |
| `npm run dev`       | Vite dev server (default port 5173 or 8080 per README) |
| `npm run build`     | Production build to `dist/`                            |
| `npm run build:dev` | Development-mode build (faster, unminified)            |
| `npm run preview`   | Preview built artifacts                                |
| `npm run lint`      | ESLint scan                                            |
| `npm run lint:fix`  | Auto-fix ESLint issues                                 |
| `npm run format`    | Prettier write                                         |

Tech stack: React 18, TypeScript, Tailwind CSS, shadcn/ui, Radix primitives, TanStack Query, SSE streaming integration.

Backend contract: SSE streaming endpoint and approval POST endpoints (FastAPI) — do not alter event shape without updating frontend stream parser.

---

## 6. Agents & Orchestration Essentials

Agents: orchestrator (manager), researcher, coder, analyst.

- **NEVER hardcode model names** in Python – always loaded via `agents/<role>/config.yaml`.
- Tools return Pydantic response types from `agenticfleet.core.code_types`.
- Manager (orchestrator) executes PLAN → EVALUATE → ACT → OBSERVE loop until termination (limits in `config/workflow.yaml`: `max_round_count`, `max_stall_count`, `max_reset_count`).

Adding an agent (summary):

1. Scaffold `src/agenticfleet/agents/<role>/{agent.py,config.yaml,tools/__init__.py}`
2. Implement `create_<role>_agent()` factory with full type hints
3. Register export in `agents/__init__.py` and builder in `fleet/fleet_builder.py`
4. Update manager instructions in `config/workflow.yaml`
5. Add config validation tests in `tests/test_config.py`
6. (Optional) Add orchestration tests in `tests/test_magentic_fleet.py`

Adding a tool:

1. Create `agents/<role>/tools/<tool_name>.py` returning a defined Pydantic model
2. Register in agent `config.yaml` under `tools` with `enabled: true`
3. Reference in agent `system_prompt`
4. Add unit test(s)
5. Run `make test-config`

---

## 7. Configuration Hierarchy

Priority sources:

1. **YAML** (workflow + per-agent) – canonical behavior & prompts
2. **Environment Variables** – secrets, toggles
3. **Code** – only wiring & factories; avoid logic overrides

Key files:

- `config/workflow.yaml` – Manager instructions, callback toggles, HITL settings, checkpointing
- `agents/<role>/config.yaml` – Model, system prompt, tools, runtime flags
- `.env` – Keys & feature flags (never commit secrets)

Validation command (must run after any change):

```bash
make test-config
```

---

## 8. Human‑in‑the‑Loop (HITL) & Approvals

Sensitive operations (e.g., code execution) must route through an `ApprovalHandler` implementation:

- CLI: `core/cli_approval.py`
- Web: `haxui/web_approval.py`

Tool wrappers create `ApprovalRequest` objects; responses can APPROVE / REJECT / MODIFY. **Never bypass approval** when the operation type is listed in workflow config `require_approval_for`.

Agent implementers: use helper utilities (see existing tool patterns) instead of re‑inventing approval flows.

---

## 9. Checkpointing & Memory

Checkpoint storage drastically reduces repeated token spend for retries and resumes.

- Storage: File (`./var/checkpoints`) or In‑Memory (tests)
- Resume parameter: `resume_from_checkpoint=<id>` when invoking fleet run

Memory (Mem0 integration) is optional. When enabled, environment variables (e.g., Mem0 path, embedding model) must be present; memory provider exists in `context/mem0_provider.py`.

---

## 10. Observability & Tracing

- Callbacks (`fleet/callbacks.py`): streaming, plan logging, progress ledger, tool calls, final answer
- Tracing gating env vars: `ENABLE_OTEL`, `OTLP_ENDPOINT`
- Avoid logging secrets — respect `ENABLE_SENSITIVE_DATA` if implemented

When adding new events: ensure shape consistency & update both CLI and frontend stream consumers.

---

## 11. Testing Strategy (Global Summary)

(Deep details in `tests/AGENTS.md`.)

Golden rules:

- Run `make test-config` after modifying YAML / env / tool imports
- Prefer focused pytest invocations (`-k`, single file, single test) for speed
- Mock external LLM/tool network calls (patch `OpenAIResponsesClient`)
- Use `asyncio_mode=auto`; do NOT add `@pytest.mark.asyncio`

Common commands:

```bash
make test               # all tests (slower)
make test-config        # config validation (critical after config or agent changes)
uv run pytest tests/test_magentic_fleet.py -k orchestrator -v
uv run pytest --cov=src/agenticfleet --cov-report=term-missing
```

E2E (requires servers): `make dev` then `make test-e2e`.

Coverage targets (suggested): core >80%, tools >70%, config validation 100% existence.

---

## 12. Code Style & Quality

Backend:

- Formatting: Black (100 char lines) + Ruff (imports, pyupgrade)
- Typing: Python 3.12 syntax (`Type | None`, never `Optional[Type]`)
- Custom exceptions from `core/exceptions.py`
- Logging via `core/logging.get_logger` (no stray prints in production code)
- Tool return schemas must remain stable (Pydantic models in `core/code_types.py`)

Frontend:

- ESLint (+ React hooks & refresh plugins)
- Prettier for formatting (`npm run format`)
- Tailwind + shadcn/ui guidelines (utility-first class merging via `tailwind-merge`)

Quality commands:

```bash
make lint
make format
make type-check
make check
npm run lint
npm run lint:fix
npm run format
```

---

## 13. Build & Deployment (High-Level)

Backend build artifacts are wheel/sdist defined by `hatchling` (see `pyproject.toml`). Frontend builds to `src/frontend/dist/` via Vite.

Typical sequence (conceptual CI):

1. `uv sync` (install)
2. `make test-config`
3. `make check`
4. `make test`
5. Frontend: `npm ci && npm run build`
6. Package backend: `uv build` (or `python -m build` if configured)
7. Publish / containerize (not defined here)

If adding CI steps: use caching (uv / node_modules), matrix Python versions (3.12 / 3.13), and separate lint, type, test jobs.

---

## 14. Security Considerations

- Never commit secrets (`.env` is ignored). Rotate API keys if exposed.
- Enforce approval for code/file/network side‑effects.
- Validate external input through Pydantic models.
- Keep dependency set updated (`make sync` + `uv sync`).
- Consider scanning (Bandit / pip‑audit) if integrating security CI.

Potential sensitive surfaces:

- Code execution tool
- File system access (if future tools added)
- Network requests (research or custom tools)

---

## 15. Adding / Modifying Major Components

### Add a New Workflow Variant

1. Create module under `src/agenticfleet/workflows/`
2. Provide factory or entrypoint function
3. Wire CLI flag or API route (FastAPI)
4. Add tests (API + orchestration)
5. Update docs & config validation if applicable

### Introduce New Observability Callback

1. Add function to `fleet/callbacks.py`
2. Register in `ConsoleCallbacks` / builder
3. Update workflow YAML toggle if new flag needed
4. Extend tests for event triggers
5. Update frontend if event stream shape changes

---

## 16. Troubleshooting (Agent-Centric)

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

## 17. Quick Command Reference (Copy/Paste Friendly)

```bash
# Backend install & validate
make install && make test-config

# Full stack dev
make dev

# Focused orchestration test
uv run pytest tests/test_magentic_fleet.py::test_fleet_builder_with_agents -v

# Add + validate new agent after edits
make test-config

# Quality gates
make check && make test

# Frontend build
(cd src/frontend && npm run build)

# Coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Validate AGENTS documentation invariants (presence, required sections, no hardcoded models, proper uv usage)
make validate-agents
```

---

## 18. Invariants (DO NOT VIOLATE)

- All Python execution via `uv run` (including tests & lint)
- No hardcoded model IDs; always load from YAML
- Tool outputs MUST be Pydantic models defined (or added) in `core/code_types.py`
- Approval required operations must respect handler decisions
- Configuration changes require `make test-config` before commit/PR
- Documentation invariants enforced via `make validate-agents`; run before opening a PR to ensure AGENTS docs are up to date and free of anti‑patterns

---

## 19. Extension Roadmap (Agent Hints)

Potential safe automation tasks:

- Generate agent skeleton given a role name
- Auto-update manager instructions when adding agent (append role description)
- Add schema validation for YAML via Pydantic model (future)
- Implement memory injection into prompts (update builder + tests)

---

## 20. References

- Root README: `README.md`
- Package detail: `src/agenticfleet/AGENTS.md`
- Tests detail: `tests/AGENTS.md`
- Architecture docs: `docs/architecture/`
- Features: `docs/features/`
- Contributing: `docs/project/CONTRIBUTING.md`
- Security: `SECURITY.md`

---

**End of AGENTS.md** – Keep this file current; update alongside structural or workflow changes. Autonomous agents should treat missing updates here as a signal to request maintenance.
