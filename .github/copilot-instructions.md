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

- **Run application**: `uv run python -m agenticfleet` or `uv run fleet` (console script entry)
- **Validate configuration**: `uv run python tests/test_config.py` after ANY change to YAML or agent factories. This is critical—it validates env vars, agent structure, tool imports, and factory callables in one go.
- **Run tests**: Run only related tests, not the entire suite. Example: `uv run pytest tests/test_magentic_fleet.py -k "test_orchestrator"` (specific filter). Do NOT use `@pytest.mark.asyncio` on new tests.
- **Code quality pre-commit**: `make check` chains lint + format + type checks. Individual commands: `make lint`, `make format`, `make type-check`. Format only changed files, not the entire codebase.
- **Resolve before executing**: Before running commands to execute or test code, ensure all problems, compilation errors, and warnings are resolved. Use `uv run mypy .` to catch type issues early.
- **All test suites**: `tests/test_magentic_fleet.py` (14 core orchestration tests), `tests/test_config.py` (configuration validation), `tests/test_mem0_context_provider.py` (memory integration)
- **Debug information**: Use `print()` statements as needed during debugging, but remove them when testing is complete.

### Adding or Modifying Agents

1. **Scaffold agent**: Create `src/agenticfleet/agents/<new_role>/` with `agent.py`, `config.yaml`, `tools/` package, `__init__.py`
2. **Factory pattern**: Load YAML via `settings.load_agent_config(name)`, instantiate `OpenAIResponsesClient(model_id=...)`, collect tools from YAML `tools` list, return `ChatAgent`. Always specify parameter types and return type: `def create_<role>_agent() -> ChatAgent:`
3. **Register**: Export factory in `agents/__init__.py`, wire into `FleetBuilder.with_agents()` in `fleet_builder.py`
4. **Update manager**: Edit manager instructions in `workflow.yaml` under `fleet.manager.instructions` to document new agent's capabilities and delegation rules
5. **Test**: Extend `tests/test_config.py` to validate new agent's config and tool imports. Run only the new test: `uv run pytest tests/test_config.py::test_<new_role>_agent -v`. Review existing agent tests to match coding style.
6. **Extend workflow tests**: Add test cases to `tests/test_magentic_fleet.py` for new agent participation in the workflow

### Adding Tools

1. **Tool implementation**: Create `agents/<role>/tools/<name>.py` returning Pydantic response model. Always specify parameter and return types: `def my_tool(param: str) -> MyToolResponse:`. Do not use `Optional[Type]`; use `Type | None` instead.
2. **Enable in config**: Add to `agents/<role>/config.yaml` under `tools` list with `name: <tool_name>` and `enabled: true`
3. **Approval integration**: For sensitive ops (code execution, file writes), wrap in `approved_tools.py` checks using `create_approval_request()` helper
4. **Update prompt**: Document tool in agent's `system_prompt` in config.yaml so agent understands when to use it
5. **Unit tests**: Mock external calls; verify tool returns correct Pydantic schema for downstream agents to parse. Run only related test: `uv run pytest tests/agents/<role>/test_<tool_name>.py -v`
6. **Review samples**: When adding tools, check existing tool implementations for consistent coding style and patterns

## Event-Driven Callbacks

Magentic Fleet uses callbacks in `fleet/callbacks.py` for real-time observability:

- **streaming_agent_response_callback**: Stream agent output as it's generated (improves UX, shows progress)
- **plan_creation_callback**: Log manager's structured plans (debug planning logic)
- **progress_ledger_callback**: Track JSON progress evaluations (detect stalls/loops early)
- **tool_call_callback**: Monitor tool executions (audit safety-sensitive operations)
- **final_answer_callback**: Capture workflow results (log outcomes for analysis)
- **agent_spawn_callback**: NEW in v0.5.5 - Monitor dynamic agent creation with spawn configurations (track spawned agents, models, tools)

Enable/disable via `fleet.callbacks.*` in workflow.yaml. All callbacks are optional but recommended for production debugging. Callbacks route to multiple destinations:

1. **Console**: Real-time streaming output with visual indicators (✓ checkmarks, 🤖 emojis)
2. **Frontend SSE**: Server-Sent Events for React web interface
3. **Audit Log**: Structured JSON logs for compliance and debugging
4. **OpenTelemetry**: Distributed tracing when `ENABLE_OTEL=true`

See `docs/features/magentic-fleet.md` for custom callback patterns.

## Tools & Safety

- **Tool structure**: All tools live under `agents/<role>/tools/` and return Pydantic models (e.g., `CodeExecutionResult` from `core/code_types.py`, `WebSearchResponse`, `DataAnalysisResponse`). Enable/disable by toggling `tools` arrays in agent config.yaml.
- **Code execution**: `code_interpreter_tool` executes Python only, sandboxes builtins, captures stdout/stderr. **Critical**: Code routes through HITL approval handler when configured—never bypass approval checks. Type imports use `from agenticfleet.core.code_types import CodeExecutionResult`.
- **Researcher mocks**: `web_search_tool` serves deterministic mock data keyed by query; upgrading to real search APIs must preserve `WebSearchResponse` schema for downstream consumers.
- **Analyst tools**: `data_analysis_tool` and `visualization_suggestion_tool` share Pydantic contracts; adjust confidence thresholds in config.yaml, not inline.

## Human-in-the-Loop (HITL)

- **Approval system**: Core interfaces in `core/approval.py` (`ApprovalRequest`, `ApprovalResponse`, `ApprovalDecision` enum, `ApprovalHandler` ABC). CLI implementation in `core/cli_approval.py` with timeout handling and history tracking.
- **Configuration**: `workflow.yaml` controls HITL via `human_in_the_loop.enabled`, `approval_timeout_seconds`, `require_approval_for` (code_execution, file_operations, etc.), and `trusted_operations` (web_search, data_analysis).
- **Tool integration**: `code_interpreter.py` checks for approval handler via `approved_tools.py` wrapper. Always use `create_approval_request()` helper and support approve/reject/modify decisions. Seamless fallback when handler is None.
- **Fleet integration**: Pass `approval_handler` to `FleetBuilder` constructor. Builder automatically wires handler to all agents requiring approval. Manager's plan review can also trigger approval when `fleet.plan_review.require_human_approval: true`.

## Checkpointing & State

- **Checkpoint storage**: Workflows support state persistence via `agent_framework.CheckpointStorage`. Two types: `FileCheckpointStorage` (persistent JSON in `./var/checkpoints`) or `InMemoryCheckpointStorage` (testing only). Configure in `workflow.yaml` under `checkpointing.storage_type` and `checkpointing.storage_path`.
- **Fleet integration**: `FleetBuilder.with_checkpointing(storage)` auto-wires checkpointing into Magentic workflow. Manager state, agent history, and progress ledgers persist automatically. Restore via `resume_from_checkpoint=<id>` in `MagenticFleet.run()`.
- **REPL commands**: Limited checkpoint support in current REPL (list/resume). Full workflow state managed by Microsoft Agent Framework's built-in checkpoint system. Status shown at startup when enabled.
- **Cost optimization**: Checkpoints save 50-80% on retry costs by avoiding redundant LLM calls. Enable in production for long-running workflows or tasks with high failure risk.

## Memory & Context

- **Mem0 provider**: `context/mem0_provider.py` integrates long-term memory via Azure AI Search + Azure OpenAI embeddings. Requires env vars: `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_AI_SEARCH_KEY`, `AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME`, `AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME`.
- **Integration status**: Exported via `agenticfleet.context` but not yet wired into manager or agent prompts. When integrating, update manager instructions in `workflow.yaml` to reference memory, extend `FleetBuilder` to inject context provider, and add tests to `tests/test_mem0_context_provider.py`.

## Audit Logging

- **Purpose**: Secure, append-only logging for critical events (approvals, errors, state changes). Essential for compliance, debugging, and post-mortem analysis.
- **Storage**: JSONL files in `./var/audit/` with automatic rotation based on file size
- **Configuration**: `workflow.yaml` under `audit_logging` section controls enabled state, file path, max size, backup count, and sensitive data redaction
- **Features**:
  - Automatic rotation (configurable `max_bytes` and `backup_count`)
  - Sensitive data redaction (replaces values with SHA256 hash + metadata)
  - Structured JSONL format (one event per line, easy to parse)
  - File locking for multi-threaded safety
  - Immediate flush option for crash resilience
- **Event types**: workflow.started, approval.requested, tool.called, agent.spawned, error.occurred, state.changed
- **Redaction**: When `redact_sensitive: true`, fields like code, prompts, api_keys, passwords are replaced with `{"hash": "...", "type": "...", "length": N, "algorithm": "sha256"}`
- **Rule**: All security-sensitive events (approvals, code execution, external API calls) MUST be audited. Never log raw secrets.
- **CLI validation**: Run `uv run python -m agenticfleet.core.audit --validate` to check audit log integrity

## Backend & Frontend Integration

**Backend (FastAPI)**: `src/agenticfleet/haxui/api.py`

- RESTful API endpoints: `/health`, `/v1/entities`, `/v1/conversations`
- SSE streaming: `/v1/conversations/stream` for real-time agent responses
- Approval endpoints: POST `/v1/approvals/{approval_id}/decision`
- CORS enabled for local development (frontend :5173 → backend :8000)

**Frontend (React)**: `src/frontend/`

- SSE client: `lib/use-fastapi-chat.ts` handles streaming, parsing OpenAI Responses API events
- Main UI: `components/ChatContainer.tsx` orchestrates chat interface
- Proxy config: Vite routes `/api/*` to backend `:8000` in development
- State management: Zustand for global state, TanStack Query for server state

**Event format**: Backend emits SSE events matching OpenAI Responses API spec. Frontend parses `data: [DONE]`, `data: {"type": "response.delta", ...}`. Never change event shape without coordinating frontend parser updates.

## Development Workflow

- **Entry points**: Run via `uv run python -m agenticfleet` (package entry) or `agentic-fleet` (console script). Both dispatch to `cli/repl.py` and use Magentic Fleet by default. No mode flags needed—legacy workflow removed.
- **Config validation**: Always run `uv run python tests/test_config.py` after changing YAML or agent factories. It validates env vars, fleet config, agent structure, tool imports, and factory callables. Also validates `test_fleet_import()`.
- **Code quality**: Use `make check` (chains lint + format + type) before commits. Ruff enforces 100-char lines, Py312 rules; Black autoformats. mypy runs strict checks. CI replicates this matrix in `.github/workflows/ci.yml`.
- **Makefile shortcuts**: `make install` (first-time setup), `make sync` (update deps), `make test-config`, `make run`. Prefer these over raw uv commands for consistency.
- **Testing Magentic**: `tests/test_magentic_fleet.py` (14 tests) covers fleet creation, agent registration, callback wiring, and workflow execution. `tests/test_configuration.py` tests factory and checkpoint storage. Mock `OpenAIResponsesClient` to avoid API calls in tests.

## Runtime Environment & Directories

**Key directories** (auto-created at runtime):

- `var/checkpoints/` - Fleet state persistence (FileCheckpointStorage)
- `var/logs/` - Application logs (`agenticfleet.log`)
- `var/audit/` - Audit trail (JSONL format with rotation)
- `var/memories/` - Mem0 history database
- `var/mem0/` - Alternative memory path (configurable)

**Configuration locations**:

- `src/agenticfleet/config/workflow.yaml` - Fleet orchestration config
- `src/agenticfleet/agents/*/config.yaml` - Per-agent configuration
- `.env` - Environment variables (API keys, feature flags)
- `pyproject.toml` - Python dependencies, tool configurations
- `src/frontend/package.json` - Frontend dependencies

**Observability & Tracing**:

- Enable OpenTelemetry: `ENABLE_OTEL=true` in `.env`
- OTLP endpoint: `OTLP_ENDPOINT=http://localhost:4317` (defaults to this)
- Sensitive data capture: `ENABLE_SENSITIVE_DATA=true` (captures prompts/completions, off by default)
- Audit logging configured in `workflow.yaml` under `audit_logging` section

**Never commit**: `.env`, `var/`, `.venv/`, `__pycache__/`, `*.pyc`, checkpoint files. All are gitignored.

## VS Code Configuration

- **Python interpreter**: `.vscode/settings.json` sets `python.defaultInterpreterPath` to `.venv/bin/python`. The project uses **uv** for dependency management, not pip/venv. Never configure `python-envs` settings with venv/pip managers—this creates conflicts.
- **Formatting & linting**: Ruff is the default formatter with explicit save actions. Black runs via `make format`. Code actions (fix all, organize imports) are explicit to avoid noise. All settings in `pyproject.toml` prevent config drift.
- **Launch configs**: `.vscode/launch.json` provides debug targets for `main.py` and `tests/test_config.py`. Both use `.venv/bin/python` interpreter. Add new configs for agent debugging or REPL sessions.
- **Tasks**: All VS Code tasks in `.vscode/tasks.json` use `uv run` prefix and depend on `uv: sync`. Run tasks via Command Palette (Cmd+Shift+P → "Tasks: Run Task") or keyboard shortcuts. Standard tasks: lint, format, type-check, tests, test-config.
- **Workspace exclusions**: `.vscode/settings.json` excludes `.venv/`, `var/`, `__pycache__`, and cache directories from file watcher to improve performance. Runtime state lives in `var/checkpoints` and `var/logs`.

## Error Handling & Logging

- **Exception hierarchy**: Raise `AgentConfigurationError` for config issues, `WorkflowError` for orchestration failures, `ToolExecutionError` for tool problems, `ContextProviderError` for memory issues. All inherit from `AgenticFleetError` in `core/exceptions.py`.
- **Logging**: `setup_logging()` in `core/logging.py` runs during `Settings` init, writes to `var/logs/agenticfleet.log`. Respect `LOG_LEVEL` env var. Use `get_logger(__name__)` in modules, never print statements (except during debug).
- **Magentic debugging**: Enable all callbacks in workflow.yaml for verbose logging. Progress ledger shows manager's reasoning; tool callbacks show agent actions. Checkpoints enable replay for post-mortem analysis.
- **Type hints**: Always specify function parameter types and return types. Use `Type | None` instead of `Optional[Type]`. Example: `def process(data: str | None) -> Result:`

## Common Pitfalls & Integration Checklist

- **❌ Hardcoding models**: Never hardcode `gpt-4o` or model names in code. Always read from `agents/<role>/config.yaml`. Models can change; YAML is the source of truth.
- **❌ Bypassing YAML configuration**: Avoid setting agent behavior in Python factory code—move it to `config.yaml`. This lets non-engineers tune agent prompts and tools without code changes.
- **❌ Tool schema mismatches**: If a downstream agent can't parse tool output, it's likely the Pydantic schema changed but wasn't updated everywhere. Check `core/code_types.py` and ensure all tools match their expected response type.
- **❌ Skipping config validation**: Always run `uv run python tests/test_config.py` after YAML changes. It catches missing env vars, broken tool imports, and invalid agent structure before runtime.
- **❌ Using `python` directly**: Never run `python main.py` or `pytest`. Always use `uv run` prefix. This ensures you're in the project environment and respects the lockfile.
- **❌ Logging secrets**: Never log raw API keys, passwords, or sensitive data. Use audit logger's redaction feature via `redact_keys` in `workflow.yaml`.
- **✅ Before committing**: Run `make check` to lint, format, and type-check. Run `make test-config` to validate all agent config. Run `make test` to ensure no regressions.

## Extending the Magentic Fleet

- **Adding agents**: (1) Create `src/agenticfleet/agents/<new_agent>/` with `agent.py`, `config.yaml`, `tools/` package, `__init__.py`. (2) Model factory after existing patterns: load YAML via `settings.load_agent_config`, instantiate `OpenAIResponsesClient`, collect tools, return `ChatAgent`. (3) Export factory in `agents/__init__.py`. (4) Register in `fleet_builder.py`: add to `FleetBuilder` agents list with `.add_agent()`. (5) Update manager instructions in `workflow.yaml` to describe new agent's capabilities. (6) Extend `tests/test_config.py` and `tests/test_magentic_fleet.py`.
- **Adding tools**: (1) Create tool function in `agents/<role>/tools/<name>.py` returning Pydantic model. (2) Add to agent's `config.yaml` tools list with `enabled: true`. (3) For sensitive operations, wrap with HITL approval check via `approved_tools.py`. (4) Write unit tests mocking external calls. (5) Update agent system_prompt in config.yaml to document tool availability.
- **Customizing manager**: Edit manager instructions in `workflow.yaml` under `fleet.manager.instructions`. Be explicit about delegation strategy, planning format, and termination criteria. Manager uses these instructions to create plans and evaluate progress.
- **Model overrides**: Respect per-agent `model` in config.yaml; never hardcode models. This preserves preview models (e.g., `gpt-5-codex`, `gpt-5`) during refactoring. Fall back to `settings.openai_model` (default: `gpt-5`) when model key missing.

## Dynamic Agent Spawning (v0.5.5+)

**When to use dynamic spawning**:

- Task requires specialized agent not in static roster (generator for code creation, verifier for security review)
- Need different model capabilities for subtask (gpt-5-codex for code, gpt-4.1 for security validation)
- Want to optimize costs by spawning lightweight agents (gpt-5-nano) for simple subtasks
- Task complexity unknown upfront and requires adaptive agent creation

**How to spawn agents**:

1. **Via manager delegation**: Manager's instructions in `workflow.yaml` include when to spawn foundation agents (planner, executor, generator, verifier)
2. **Via DynamicOrchestrationManager**: Direct API call to `analyze_task()` → `create_spawn_config()` → `spawn_agent()`
3. **Configuration**: Set `dynamic_orchestration.enabled: true` in `workflow.yaml` and configure model pool, foundation agents, tool mappings, spawn limits

**Model selection guidelines**:

- **gpt-5**: Complex reasoning, strategic planning, high-level analysis
- **gpt-5-codex**: Code generation, debugging, refactoring (temperature 0.3 for deterministic output)
- **gpt-5-mini**: General tasks, synthesis, balanced performance/cost
- **gpt-5-nano**: Simple tasks, formatting, data extraction (lowest cost)
- **gpt-4.1**: Security review, quality assurance, validation (temperature 0.2 for analytical precision)
- **gpt-4.1-mini**: General validation, lightweight review

**Observability**: All spawn events emit to console (🤖 emoji), frontend SSE (agent.spawned), and audit log. Track agent lineage with `track_agent_lineage: true`.

**Example**: See `examples/magentic_with_dynamic_spawning.py` for complete workflow with dynamic spawning demonstration.

## Testing Patterns

- **Factory mocking**: Import `create_<role>_agent()` directly and test with a mock `OpenAIResponsesClient` to avoid API calls. Example: `mock_client = MagicMock(spec=OpenAIResponsesClient)`.
- **Config validation**: Use `settings.load_agent_config()` to verify YAML structure; assert required keys are present. This catches config drift early.
- **Callback testing**: Instantiate `ConsoleCallbacks` with a mock sink and verify callback signatures match expected events (e.g., `streaming_agent_response_callback` should receive `MagenticAgentDeltaEvent`).
- **Checkpoint testing**: Use `InMemoryCheckpointStorage` in tests; reserve `FileCheckpointStorage` for integration tests. Cleanup `var/checkpoints` between test runs if using file storage.

## Key References

- **Microsoft Agent Framework**: https://github.com/microsoft/agent-framework/python/ (core orchestration patterns, official documentation, latest API updates)
- **Magentic Architecture**: `docs/architecture/magentic-fleet.md` (architectural design), `docs/features/magentic-fleet.md` (complete feature guide), `docs/features/magentic-fleet-implementation.md` (implementation details)
- **Fleet Code**: `src/agenticfleet/fleet/magentic_fleet.py` (orchestrator), `src/agenticfleet/fleet/fleet_builder.py` (builder pattern), `src/agenticfleet/fleet/callbacks.py` (observability)
- **Core Types**: `src/agenticfleet/core/code_types.py` (`CodeExecutionResult`), `src/agenticfleet/core/approval.py` (HITL), `src/agenticfleet/core/exceptions.py` (error hierarchy)
- **Features**: `docs/features/checkpointing.md` (state persistence), `docs/guides/human-in-the-loop.md` (HITL usage), `docs/operations/mem0-integration.md` (memory setup)
- **Agents**: `docs/project/AGENTS.md` (agent catalog with capabilities)
- **Releases**: `docs/releases/2025-10-14-v0.5.1-magentic-fleet.md` (Magentic Fleet release), `docs/releases/2025-10-13-hitl-implementation.md` (HITL implementation)
