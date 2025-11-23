# Changelog

## Unreleased

### Highlights

- **Optional Azure Cosmos DB persistence** – `AGENTICFLEET_USE_COSMOS=1` now mirrors workflow history, agent memory, DSPy datasets, and cache metadata into Cosmos NoSQL using a single helper module (`utils/cosmos.py`). The runtime degrades gracefully when Cosmos is unreachable.
- **Data Model Documentation** – Added `docs/developers/cosmosdb_requirements.md` and `docs/developers/cosmosdb_data_model.md`, covering access patterns, container schemas, and provisioning guidance that follow Azure Cosmos DB best practices (high-cardinality partition keys, 2 MB limits, TTL guidance).
- **Quality & Persistence polish** – `HistoryManager` now mirrors executions asynchronously, the supervisor workflow records whether refinement ran, and tests gained realistic persistence utilities with summarization support.

### Changes

- Introduced `src/agentic_fleet/utils/cosmos.py`, a cached helper that manages Cosmos clients (managed identity or key auth), container lookups, and best-effort mirroring APIs for executions, agent memory items, DSPy examples/optimization runs, and cache entries.
- Updated `utils/history_manager.py`, `workflows/quality/refiner.py`, `workflows/supervisor_workflow.py`, and supporting modules to call the new helper without blocking the critical path.
- Added lightweight, in-memory persistence utilities (`utils/persistence.py`) used by `tests/test_persistence.py` to verify summarization thresholds (`summary_threshold` / `summary_keep_recent`).
- Expanded documentation: README (configuration, observability, new Cosmos section), `docs/users/configuration.md` (environment reference), and both `AGENTS.md` files to describe Cosmos-backed long-term memory.

### Testing

- Updated `tests/test_persistence.py` with real persistence helpers and summarization assertions.
- Extended workflow quality suites (`tests/workflows/test_judge_refinement.py`, `tests/workflows/test_quality_modules.py`) to ensure the new refinement and quality metadata paths behave as expected.

### Migration Notes

- Cosmos mirroring is off by default. Set `AGENTICFLEET_USE_COSMOS=1` plus the relevant endpoint/key (or managed identity) variables to enable it. The helper never creates databases/containers; provision them ahead of time using the schemas in `docs/developers/cosmosdb_data_model.md`.
- Container names default to `workflowRuns`, `agentMemory`, `dspyExamples`, `dspyOptimizationRuns`, and `cache`. Override via `AZURE_COSMOS_*_CONTAINER` env vars if your account uses different IDs.

---

## v0.6.2 (2025-11-23) – Code Quality & Tooling Hardening

### Highlights

- **Strict Quality Gates** – CI now enforces strict type checking (no `continue-on-error`) and a minimum **80% backend test coverage**.
- **Unified QA Tooling** – Added `make qa` command to run the full quality suite (lint, format, type-check, backend tests, frontend tests) in one go.
- **Cross-Editor Consistency** – Added `.editorconfig` to enforce consistent indentation and file settings across all IDEs.
- **Docstring Policy** – Enforced presence of docstrings on all public APIs via Ruff (`D100`-`D104`), with exceptions for tests and scripts.
- **Frontend Ergonomics** – Added `npm run format` script to `src/frontend/package.json` for easy Prettier formatting.

### Changes

- **Configuration**:
  - Added `.editorconfig` to root.
  - Updated `pyproject.toml`:
    - Enabled Ruff docstring rules `D100`-`D104`.
    - Configured `pytest-cov` with `fail_under = 80`.
    - Added per-file ignores for docstrings in `tests/`, `examples/`, and `scripts/`.
  - Updated `src/frontend/package.json`: Added `"format": "prettier --write ."` script.
  - Updated `.gitignore`: Added `.editorconfig` (if not tracked) and other IDE artifacts.

- **CI/CD**:
  - Updated `.github/workflows/ci.yml`:
    - Removed `continue-on-error: true` from `type-check` job.
    - Updated `pytest` command to use correct coverage source path (`src/agentic_fleet`).

- **Documentation**:
  - Updated `docs/developers/contributing.md` with new QA commands and style guidelines.
  - Updated `docs/developers/code-quality.md` with explicit coverage and docstring policies.

- **Makefile**:
  - Added `qa` target for comprehensive local testing.

---

## v0.6.0 (2025-11-13) – Major Refactor: Code Quality, Import Organization & Architecture Cleanup

### Highlights (v0.6.0)

- **[BREAKING]** Complete refactor and reorganization of `agentic_fleet` package structure
- **[BREAKING]** Removed `examples/` folder; consolidated to single `examples/simple_workflow.py`
- Removed all unused imports and fixed critical linting violations (F401, F541, F841, F824)
- Standardized import order using `isort` with black profile for consistency
- Applied `black` code formatting (line-length 100) across all 54 Python files
- Achieved zero critical flake8 errors across entire codebase
- Improved package organization with clear separation of concerns

### Package Structure (v0.6.0)

The refactored `src/agentic_fleet/` structure:

```
agentic_fleet/
├── __init__.py              # Package initialization
├── console.py               # Enhanced CLI with SSE streaming
├── main.py                  # Main entry point
├── manage_cache.py          # Cache management utilities
│
├── agents/                  # Agent implementations
│   ├── coder.py            # Code generation agent
│   ├── coordinator.py       # Multi-agent coordinator
│   ├── executor.py          # Code execution agent
│   ├── generator.py         # Content generation agent
│   ├── planner.py           # Task planning agent
│   └── verifier.py          # Verification agent
│
├── cli/                     # CLI interface (TUI components)
│   └── __init__.py
│
├── config/                  # Configuration files
│   └── workflow_config.yaml # Centralized workflow configuration
│
├── data/                    # Training and evaluation data
│   ├── supervisor_examples.json           # DSPy training examples
│   ├── evaluation_tasks.jsonl             # Evaluation tasks
│   └── history_evaluation_tasks.jsonl     # Historical evaluation data
│
├── dspy_modules/            # DSPy optimization modules
│   ├── signatures.py        # DSPy signature definitions
│   ├── supervisor.py        # DSPy supervisor with ChainOfThought
│   ├── handoff_signatures.py # Agent handoff signatures
│   └── workflow_signatures.py # Workflow-specific signatures
│
├── evaluation/              # Evaluation framework
│   ├── evaluator.py         # Task evaluation logic
│   └── metrics.py           # Performance metrics
│
├── prompts/                 # Agent prompt templates
│   ├── coder.py
│   ├── executor.py
│   ├── generator.py
│   ├── planner.py
│   └── verifier.py
│
├── scripts/                 # Utility scripts
│   ├── analyze_history.py              # Execution history analysis
│   ├── create_history_evaluation.py    # Generate evaluation datasets
│   └── self_improve.py                 # Self-improvement workflow
│
├── tools/                   # Agent tools and integrations
│   ├── browser_tool.py      # Playwright browser automation
│   ├── hosted_code_adapter.py # Code interpreter adapter
│   ├── tavily_tool.py       # Tavily search integration
│   └── tavily_mcp_tool.py   # Tavily MCP protocol tool
│
├── utils/                   # Core utilities
│   ├── cache.py             # Caching utilities
│   ├── compiler.py          # DSPy module compilation
│   ├── config_loader.py     # Configuration loading
│   ├── config_schema.py     # Configuration schemas
│   ├── dspy_manager.py      # DSPy LM management
│   ├── gepa_optimizer.py    # GEPA optimization algorithm
│   ├── history_manager.py   # Execution history persistence
│   ├── logger.py            # Logging setup
│   ├── models.py            # Data models
│   ├── self_improvement.py  # Self-improvement utilities
│   ├── telemetry.py         # Telemetry and tracing
│   ├── tool_registry.py     # Tool registration and discovery
│   └── tracing.py           # OpenTelemetry tracing
│
└── workflows/               # Workflow orchestration
    ├── exceptions.py        # Workflow-specific exceptions
    ├── handoff_manager.py   # Agent handoff coordination
    └── supervisor_workflow.py # Main supervisor workflow
```

### Changes (v0.6.0)

#### Code Quality & Linting

- **Import Cleanup**: Removed unused imports across all modules:
  - `typing.List`, `typing.Dict`, `typing.Any` removed where unused
  - `urllib.parse.urljoin` removed from `browser_tool.py`
  - `asyncio` removed from `history_manager.py`
  - `concurrent.futures` marked with `noqa: F401` where import validates runtime behavior
  - `dspy` imports marked with `noqa: F401` where required for module initialization
- **F-string Fixes**: Corrected f-strings missing placeholders in:
  - `scripts/create_history_evaluation.py` (line 106): Changed to regular string
  - `utils/gepa_optimizer.py` (line 442): Split into multi-line with proper placeholders
- **Variable Usage**: Added `noqa: F841` for intentionally unused variables:
  - `workflows/supervisor_workflow.py` (`assigned_agents`, `subtasks`) - kept for debugging
  - `utils/compiler.py` (`optional_fields`) - reserved for future validation
- **Global Declarations**: Fixed unused global declaration in `utils/dspy_manager.py` with `noqa: F824`
- **Import Organization**: All files now follow consistent import order:
  1. Standard library imports
  2. Third-party imports
  3. Local/relative imports

#### Formatting

- Applied `black --line-length 100` to 54 files (16 reformatted)
- Applied `isort --profile black` to 37 files for import consistency
- Applied `autopep8 --aggressive --aggressive` for whitespace and line-length fixes
- Maintained 112 E501 warnings (line-too-long) in docstrings and configuration strings where breaking lines would reduce readability

#### Architecture Improvements

1. **Modular Organization**: Clear separation between:
   - Agents (`agents/`) - Individual agent implementations
   - Workflows (`workflows/`) - Orchestration and coordination
   - DSPy (`dspy_modules/`) - Prompt optimization
   - Tools (`tools/`) - External integrations
   - Utils (`utils/`) - Shared utilities

2. **Configuration Centralization**: Single source of truth in `config/workflow_config.yaml` for:
   - Model selection (DSPy, agents)
   - Optimization parameters
   - Workflow settings
   - Tool configurations

3. **Evaluation Framework**: Structured evaluation with:
   - `evaluation/evaluator.py` - Evaluation orchestration
   - `evaluation/metrics.py` - Metric definitions
   - `data/*.jsonl` - Evaluation datasets

4. **Tool Registry**: Centralized tool management via `utils/tool_registry.py`:
   - Automatic tool discovery
   - Tool capability metadata
   - Tool-aware DSPy routing

5. **DSPy Integration**: Complete DSPy workflow with:
   - Signature definitions (`dspy_modules/signatures.py`)
   - Supervisor with ChainOfThought (`dspy_modules/supervisor.py`)
   - BootstrapFewShot compilation (`utils/compiler.py`)
   - GEPA optimizer (`utils/gepa_optimizer.py`)

#### Files Modified (Summary)

**Core Components (16 files reformatted):**

- `agents/coordinator.py` - Multi-agent coordination logic
- `console.py` - CLI interface with streaming support
- `dspy_modules/supervisor.py` - DSPy supervisor module
- `dspy_modules/signatures.py` - Task routing signatures
- `dspy_modules/handoff_signatures.py` - Agent handoff logic
- `tools/browser_tool.py` - Playwright integration
- `tools/tavily_tool.py` - Search tool
- `tools/tavily_mcp_tool.py` - MCP protocol adapter
- `utils/compiler.py` - DSPy compilation
- `utils/gepa_optimizer.py` - GEPA algorithm
- `utils/history_manager.py` - History persistence
- `utils/tool_registry.py` - Tool registry
- `utils/self_improvement.py` - Self-improvement logic
- `workflows/supervisor_workflow.py` - Main workflow
- `workflows/handoff_manager.py` - Handoff coordination
- `scripts/create_history_evaluation.py` - Evaluation generation

**Import Organization (37 files):**
All Python files in `agents/`, `dspy_modules/`, `evaluation/`, `prompts/`, `scripts/`, `tools/`, `utils/`, and `workflows/`

### Breaking Changes (v0.6.0)

1. **Import Paths**: While no import paths changed, downstream code depending on re-exported unused imports may break. Verify all imports are directly sourced.

2. **Code Style Requirements**: All contributions must now adhere to:
   - Black formatting (line-length 100)
   - isort import ordering (black profile)
   - Flake8 compliance (excluding E501 for docstrings)

3. **Examples Consolidation**: Multiple example files removed, consolidated to `examples/simple_workflow.py`

4. **Type Hints**: Removed `@no_type_check` decorators in preparation for strict type checking

### Migration Notes (v0.6.0)

No functional changes. This is purely a code quality and organizational release. If you maintain a fork:

1. **Rebase carefully** - formatting touches 54 files across all modules

2. **Development Setup** - Add formatting tools:

   ```bash
   uv pip install black isort flake8 autopep8
   ```

3. **Pre-commit Workflow** - Run before submitting PRs:

   ```bash
   # Format code
   uv run black --line-length 100 src/agentic_fleet/

   # Organize imports
   uv run isort src/agentic_fleet/ --profile black

   # Check linting (excluding line-length for docstrings)
   uv run flake8 src/agentic_fleet/ --max-line-length=100 \
     --extend-ignore=E203,W503,E501
   ```

4. **Import Updates** - If you were importing from consolidated examples:

   ```python
   # Old (multiple example files)
   from agentic_fleet.examples.workflow_example import ...

   # New (single example)
   from agentic_fleet.examples.simple_workflow import ...
   ```

### Verification (v0.6.0)

- **Flake8**: 0 critical errors (F401, F541, F841, F824 all resolved)
- **Black**: All 54 files formatted consistently
- **isort**: Import order standardized across 37 files
- **Remaining**: 112 acceptable E501 warnings in docstrings/configs where readability takes precedence
- **Package Structure**: Clean hierarchy with clear separation of concerns
- **Tests**: All existing tests pass without modification

### Technical Details (v0.6.0)

#### DSPy Workflow

1. **Task Analysis** → DSPy analyzes incoming task
2. **Task Routing** → DSPy routes to appropriate agents with execution mode
3. **Agent Execution** → Agents execute in parallel/sequential/delegated mode
4. **Quality Assessment** → DSPy evaluates quality (refines if score < 8/10)

#### Execution Modes

- **Delegated**: Single agent handles entire task
- **Sequential**: Task flows through agents in order
- **Parallel**: Multiple agents work simultaneously

#### Configuration Hierarchy

```yaml
config/workflow_config.yaml
├── dspy (model, optimization)
├── workflow (supervisor settings)
├── agents (researcher, analyst, writer, reviewer)
└── tools (TavilySearchTool, HostedCodeInterpreterTool)
```

### Follow-up (v0.6.0)

- Add pre-commit hooks for black/isort/flake8 automation
- Evaluate migrating to ruff for faster unified linting
- Add mypy strict mode once type stubs for agent_framework are available
- Consider adding pytest-cov for test coverage tracking
- Document tool creation patterns in developer guide
- Add architecture decision records (ADRs) for major design choices

---

## v0.5.8 (2025-11-06) – Async Factory & Domain Exceptions

### Highlights (v0.5.8)

- **[BREAKING]** Removed legacy `core/` package (10 files), duplicate `workflow.yaml`, `api/responses/models.py`, empty `api/eventing/`, and obsolete `tests/test_magentic_integration.py` – achieving 14% file reduction (94→87 files, ~1,572 lines removed).
- Consolidated imports: `MagenticContext`, `OpenAIResponsesClient` now imported from upstream `agent_framework` instead of local copies.
- Single authoritative `workflows.yaml` now drives configuration (removed workflow.yaml fallback).
- Introduced fully asynchronous `WorkflowFactory.create()` with non-blocking YAML load and DI-friendly singleton (`get_workflow_factory`).
- Added centralized domain exceptions (`api/exceptions.py`) with consistent JSON error envelope: `{"error": {"code": <string>, "message": <string>}}`.
- Replaced all `HTTPException` raises in routes/services with domain exceptions (`WorkflowNotFoundError`, `WorkflowExecutionError`, `EntityNotFoundError`, `ConversationMissingError`, `ValidationError`).
- Eliminated all `@no_type_check` decorators – routes now have explicit type hints ready for strict mypy.
- Consolidated Responses streaming models into a single module (`responses/schemas.py`); removed `responses/models.py`.
- Added Pydantic v2 models for Entities (`EntityListResponse`, `EntityDetailResponse`) and Conversations (`MessageResponse`, `ConversationResponse`, `ConversationsListResponse`).
- Converted remaining synchronous endpoints (system health, approvals submission) to `async` functions.
- Normalized conversation and entity endpoints to structured response models (no manual dict serialization helpers).

### Changes (v0.5.8)

#### Backend Architecture

- **Consolidation**: Removed `core/` shim layer (10 files), `workflow.yaml`, `api/responses/models.py`, empty `api/eventing/`, obsolete `test_magentic_integration.py`.
- **Upstream imports**: `MagenticContext`, `OpenAIResponsesClient` imported from `agent_framework` package.
- `utils/factory.py`: Async construction (`create()`), singleton helpers (`get_workflow_factory`, `get_workflow_factory_cached`) and default workflow fallback semantics preserved.
- `api/workflow_factory.py`: Simplified resolution order to only check workflows.yaml (removed workflow.yaml fallback).
- `api/app.py`: Registers domain exception handlers during app creation via `register_exception_handlers(app)`.
- `api/exceptions.py`: Provides base `AgenticFleetException` + specialized subclasses; adds automatic handler registration loop.
- `api/workflows/routes.py`: Raises `WorkflowNotFoundError` / `WorkflowExecutionError` instead of raw HTTP errors; streaming and status endpoints updated accordingly.
- `api/entities/schemas.py`: Replaced `EntityInfo` / `DiscoveryResponse` with `EntityDetailResponse` / `EntityListResponse` (extra fields allowed via `extra="allow"`).
- `api/conversations/routes.py`: Refactored to use Pydantic models (removed custom serializer functions) with explicit `response_model` declarations.
- `api/responses/schemas.py`: Merged streaming event classes (Delta, Completed, Orchestrator) alongside request/complete schemas (removed duplicate models.py).
- `api/chat/service.py`: Emits `WorkflowExecutionError` on failure instead of `HTTPException`.
- Removed all `@no_type_check` decorators across API modules for stricter typing.

#### Error Handling

- Unified envelope: Example 404 workflow error → `{"error": {"code": "workflow_not_found", "message": "Workflow 'abc' not found"}}`.
- Validation issues (e.g. missing input) now emit `validation_error` (status 400).
- Legacy `ConversationNotFoundError` mapped to new JSON format transparently.

#### Testing

- Updated `test_chat_schema_and_workflow.py` to expect `WorkflowExecutionError` instead of `HTTPException` for failing workflow execution path.
- Streaming, entity, and conversation tests pass against new Pydantic schemas (subset run: 34 tests green).
- Backward-compatible synchronous factory constructor retained temporarily; full migration to async usage planned in follow-up (Task 15).

### Migration Notes (v0.5.8)

Breaking/API-visible changes:

1. **Removed `core/` package**: Update imports:
   - `from agentic_fleet.core.agents` → `from agentic_fleet.agents.coordinator`
   - `from agentic_fleet.core.events` → `from agentic_fleet.models.events` or `from agent_framework`
   - `from agentic_fleet.core.tools` → `from agentic_fleet.tools.registry`
   - `from agentic_fleet.core.magentic_framework import MagenticContext` → `from agent_framework import MagenticContext`
2. **Configuration**: Remove references to `workflow.yaml` (singular) – only `workflows.yaml` is recognized.
3. Error response shape changed (was `{"detail": "..."}` for HTTPException, now structured `{"error": {"code": "...", "message": "..."}}`). Update clients parsing error details.
4. Entity models renamed: replace `EntityInfo` → `EntityDetailResponse`, `DiscoveryResponse` → `EntityListResponse`.
5. Conversation endpoints now return typed models; any code expecting raw dict keys should adapt to identical field names but may benefit from schema validation.
6. Responses streaming model imports: use `from agentic_fleet.api.responses.schemas import ResponseDeltaEvent` (models module removed).
7. Prefer `await get_workflow_factory()` in async contexts; direct `WorkflowFactory()` construction is deprecated and will be removed.

Regex-assisted refactors (examples):

```bash
# Replace HTTPException instantiations (manual review recommended)
grep -R "HTTPException" -l src | xargs sed -E -i '' 's/HTTPException\((status_code=)?500[^)]*\)/WorkflowExecutionError("An error occurred while processing your request")/g'

# Entity model rename
grep -R "EntityInfo" -l src | xargs sed -E -i '' 's/EntityInfo/EntityDetailResponse/g'
grep -R "DiscoveryResponse" -l src | xargs sed -E -i '' 's/DiscoveryResponse/EntityListResponse/g'
```

### Verification (v0.5.8)

- Targeted pytest subset (entities, responses, conversation memory, chat workflow service) passing: 34 tests.
- Chat workflow domain error propagation verified (`WorkflowExecutionError`).
- SSE streaming still emits `response.delta`, `response.completed`, `reasoning.completed`, `[DONE]` markers unchanged.
- Health and approvals endpoints function asynchronously (manual invocation smoke-tested via test clients).

### Follow-up (v0.5.8)

- Migrate all remaining test instantiation sites to async factory (Task 15).
- Enforce mypy strict mode and remove legacy synchronous factory constructor.
- Extend domain exceptions with optional trace IDs for observability once OTEL integration toggled via `ENABLE_OTEL`.
- Add richer validation for entity input schemas (support structured `input` variants).

---

## v0.5.7 (2025-11-06) – Conversation Memory Enhancement

### Highlights (v0.5.7)

- Fixed conversation retrieval bug preventing empty conversations from being loaded
- Implemented full conversation listing functionality via `PersistenceAdapter.list()`
- Added `ConversationRepository.list_all()` for retrieving all conversations
- Conversation history now correctly injects into workflow context for multi-turn interactions
- Added regression test `test_empty_conversation_retrieval()` to prevent future bugs

### Changes (v0.5.7)

#### Backend

- **PersistenceAdapter.get()**: Now checks conversation table first before loading messages, allowing empty conversations to be retrieved
- **PersistenceAdapter.list()**: Fully implemented using `ConversationRepository.list_all()`, returns conversations without loading messages for performance
- **ConversationRepository.list_all()**: New method returning all conversations ordered by `updated_at DESC`
- **Conversation Memory**: History formatted as "ROLE: content" pairs, prepended to current message with format "Previous conversation:\n{history}\n\nUser's current message: {message}"
- **Metadata Extraction**: Conversation title and timestamps now extracted from conversation record instead of first message

#### Tests

- Added `test_empty_conversation_retrieval()` regression test to `test_conversation_memory.py`
- All 18 tests passing (11 persistence + 6 conversation memory + 1 API CRUD)
- End-to-end UI testing verified with Chrome DevTools

#### Docs

- Updated conversation memory implementation notes
- Documented history injection format and workflow integration

### Bug Fixes (v0.5.7)

- Fixed "Conversation not found" error when retrieving newly created conversations before first message
- Fixed conversation listing returning empty results despite existing conversations

### Migration Notes (v0.5.7)

No action required. Existing conversations continue working. New conversations now properly support immediate retrieval.

### Verification (v0.5.7)

Production testing completed:

- Two-turn conversation tested: "What is the Monty Hall problem?" followed by "Why should I switch? Isn't it 50-50 after the host reveals a goat?"
- Backend logs confirmed history injection working correctly
- Agent responses demonstrated full context awareness
- Follow-up questions answered appropriately using previous message context

## v0.5.6 (2025-11-06) – Reasoning Integration

### Highlights (v0.5.6)

- Unified reasoning integration: backend extraction, single SSE emission (`reasoning.completed`), persistence, and dual UI surfaces (Reasoning panel + ChainOfThought).
- Reasoning trace appears before assistant content and is stored with the message for auditability.
- Backward compatible: models without reasoning simply omit the panel; no client changes required.
- Stability: workflow_start timing initialization removes potential elapsed-time inconsistencies in fast-path streaming.

### Changes (v0.5.6)

#### Core Backend

- Added reasoning trace extraction helper in workflow events.
- Emitted a single `reasoning.completed` SSE event prior to assistant message finalization.
- Extended conversation message persistence with optional `reasoning` field (non-breaking).

#### Frontend

- Added transient reasoning state (content + completion) with automatic panel collapse.
- Retained ChainOfThought for structured orchestration; reasoning panel used for model-internal trace.
- Ensured rendering order shows reasoning before assistant message content.

#### Types & Contracts

- Added `reasoning` to serialized messages.
- Registered only final `reasoning.completed` (no incremental streaming events).

#### Documentation

- Consolidated earlier reasoning notes into this single release entry.
- Removed transitional version entries (0.5.7 / 0.5.8) to reduce fragmentation.

### Migration Notes (v0.5.6)

No action required. Reasoning appears only when provided; absence yields unchanged responses.

## v0.5.5 (2025-11-05)

### Highlights (v0.5.5)

- Frontend SSE payloads now expose `agentId` exclusively in camelCase to match backend event schemas.
- New `useMetricsStore` placeholder lays groundwork for upcoming streaming telemetry without impacting current UI flows.
- Documentation refreshed to capture chat store retirement and metrics store hand-off.

### Changes (v0.5.5)

- Normalised Responses event bridge and frontend consumers to rely on camelCase identifiers.
- Archived legacy chat store, API client, and component Vitest suites to unblock modernised coverage.
- Added guidance around metrics store scaffolding and removal rationale to docs set.

### Removed

- `src/frontend/src/stores/__tests__/chatStore.test.ts`
- `src/frontend/src/lib/__tests__/api.test.ts`
- `src/frontend/src/components/chat/__tests__/ChatMessage.test.tsx`

### Migration Notes (v0.5.5)

- Extend telemetry features from new `useMetricsStore` instead of deprecated chat store state.
- Historical assertions remain available under `docs/archive/chatStore_legacy_tests.md` and `docs/archive/frontend_api_and_component_tests.md` for reference.

### Follow-up (v0.5.5)

- Rebuild streaming-focused chat store coverage aligned with new architecture.
- Hook performance event instrumentation into `useMetricsStore` once telemetry pipeline lands.
