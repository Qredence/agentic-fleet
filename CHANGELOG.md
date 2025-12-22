# Changelog

## Unreleased (2025-12-21)

### Highlights

- Execution history management utilities and background quality evaluation for richer workflow telemetry.
- Frontend architecture restructure (pages/stores) plus new design tokens and UI components.
- New docs-sync automation and expanded internal workflow documentation.

### Changes

#### Backend

- Added new history utilities under `src/agentic_fleet/utils/storage/` (conversation, history, persistence, job_store) plus `utils/storage/cosmos.py` for Cosmos-backed history storage.
- Added history management API surface in `src/agentic_fleet/api/routes/history.py` and integrated it into `api/api_v1/api.py` routing.
- Added new optimization endpoints and rewired optimization routes (`api/routes/optimization.py`), replacing older optimize route wiring.
- Expanded workflow event mapping in `src/agentic_fleet/api/events/mapping.py` to reflect new event categories.
- Introduced background quality evaluation runner in `src/agentic_fleet/evaluation/background.py` and updated `scripts/self_improve.py`/`scripts/evaluate_history.py` to use the new evaluation flow.
- Restructured DSPy module layout into subpackages (`dspy_modules/gepa`, `dspy_modules/lifecycle`) and refreshed signatures in `dspy_modules/signatures.py`.
- Added new DSPy optimizer utilities in `dspy_modules/optimizer.py` and program wrappers in `dspy_modules/programs.py`.
- Refactored workflow execution plumbing (`workflows/builder.py`, `workflows/context.py`, executors/_, strategies/_, `workflows/supervisor.py`) to align with the new module structure.
- Added `utils/infra/` layer (logging, profiling, resilience, telemetry, tracing) and updated imports to use the new infra package.
- Added `utils/cfg/` configuration helpers (loader, env, settings) and shifted config usage away from deprecated core modules.
- Removed deprecated core modules under `src/agentic_fleet/core/` and replaced usage across services/CLI.
- Cleaned service layer imports and added `services/optimization_service.py` plus supporting changes in `services/dspy_programs.py`, `services/chat_sse.py`, and `services/chat_websocket.py`.
- Added tool registry updates (`utils/tool_registry.py`) and MCP tooling adjustments in `tools/mcp_tools.py`.
- Added dependencies for OpenInference and Langfuse in `pyproject.toml` and updated wiring where needed.

#### Frontend

- Restructured UI into pages/stores pattern with new chat/layout components and sidebar workflows.
- Introduced design tokens and a refreshed component set (tabs, tooltip, textarea, etc.).
- Removed unused shared UI components and legacy styles.

#### Docs

- Added docs-sync workflow docs plus new agentic workflow optimization guide and internal plans.

#### Tests

- Added optimization API tests plus new frontend chat/dashboard tests.
- Removed obsolete optimization/self-improvement tests.

#### CI/Infra

- Added docs-sync workflow automation and Q agentic workflow optimizer workflow.

### Migration Notes

- Deprecated `agentic_fleet.core.*` modules removed; update external imports to new service/utility equivalents.

## v0.6.95 (2025-12-16) – Package Reorganization & Security Defaults

### Highlights

#### DSPy Compiled Artifact Pipeline (Phases 1-4)

- **Compiled artifact registry** – Fail-fast enforcement ensures DSPy modules are pre-compiled before production use, eliminating runtime compilation overhead.
- **Preloaded decision modules** – Routing, quality, and analysis modules are loaded at startup for faster first-request response times.
- **Parallel optimization support** – GEPA optimizer can run training in parallel for faster model optimization.
- **Phase integration tests** – Comprehensive test suite validates the complete compilation → loading → execution pipeline.

#### Optimization & Self-Improvement Dashboard

- **Optimization APIs** – REST endpoints for triggering DSPy optimization, evaluation runs, and self-improvement cycles.
- **Dashboard integration** – Monitor optimization progress, view evaluation metrics, and track self-improvement results.
- **History-based learning** – System learns from execution history to improve routing decisions over time.

#### Performance & Reliability

- **2x faster config loading** – Configuration caching reduces repeated YAML parsing overhead.
- **History indexing** – Execution history now indexed for faster queries and analysis.
- **70% code deduplication** – Helper extraction and delegation patterns reduced code redundancy.
- **Enhanced WebSocket stability** – Improved heartbeat handling and reconnection logic with exponential backoff.

#### Secure-by-Default Tracing

- **`capture_sensitive` defaults to `false`** – All tracing configurations now default to secure mode across schema, YAML, and built-in defaults.
- **Task preview redaction** – Cache telemetry redacts task previews by default; opt-in via `ENABLE_SENSITIVE_DATA=true`.

#### Package Reorganization

- **Utils subpackages** – Split `utils/` into focused modules for better maintainability:
  - `utils/infra/` – Tracing, resilience, telemetry, logging
  - `utils/storage/` – Cosmos, persistence, history management
  - `utils/cfg/` – Configuration utilities
- **Import path updates** – Changed `from agentic_fleet.utils.config` to `from agentic_fleet.utils.cfg` for consistency.

#### Cosmos DB Improvements

- **Partition-key fixes** – `query_agent_memory()` now uses single-partition queries for better performance.
- **User-scoped history** – History loads are user-scoped when `userId` is available.

#### Frontend Enhancements

- **New UI components** – Added Skeleton, Tabs, Textarea, Tooltip (shadcn/ui).
- **Theme context** – Centralized theme management via `ThemeContext`.
- **Frontend restructure (partial)** – Implemented `features/chat/` and `features/dashboard/` structure with components, hooks, stores, and types.
- **PromptInput accessibility** – Improved ARIA labels and keyboard navigation.
- **Textarea styling consistency** – Unified styling across all input components.

#### Documentation Overhaul

- **Comprehensive System Overview** – New `docs/developers/system-overview.md` (1,150+ lines) providing in-depth technical guide covering:
  - 5-phase pipeline architecture with diagrams
  - Agent system (Factory, Roles, Tools, Handoffs)
  - DSPy integration (GEPA, Training, Self-improvement)
  - User interfaces (CLI, Python API, Web Frontend)
  - Observability (Events, OpenTelemetry, Middleware)
- **Enriched User Documentation** – React-docs style transformation:
  - `docs/users/overview.md`: Complete rewrite (84 → 446 lines) with problem/solution framework, visual diagrams, and FAQ
  - `docs/users/getting-started.md`: Enriched (277 → 491 lines) with "Hello World" tutorial, progressive examples, and troubleshooting
- **README.md Updates** – Enhanced with 5-phase pipeline diagram, system architecture overview, and split documentation sections (Users/Developers)

#### Repository Cleanup

- **Removed legacy tracking files** – Deleted redundant root-level files:
  - `GEMINI.md`, `PLANS.md`, `PLANS_previous.md` (consolidated into docs/plans)
  - `PR_SUMMARY.md`, `TRACING_STATUS.md`, `PHASE3_PHASE4_IMPLEMENTATION.md` (temporary tracking)
  - `docs/plans/archive/` (old version-specific plans)
- **Cleaned .gitignore** – Removed duplicate entries, kept `docker/` and `infrastructure/` tracked (useful deployment templates)
- **Untracked generated files** – `report/jscpd-report.json` now properly excluded

### Changes

#### Backend

- **`src/agentic_fleet/utils/`**: Reorganized into `infra/`, `storage/`, and `cfg/` subpackages.
- **Import paths**: Updated all imports from `config` to `cfg` module for consistency.
- **`evaluate_routing` function**: Enhanced with detailed docstring and type hinting.
- **`optimize_reasoner` script**: Updated import paths for clarity.
- **`ChatSSEService`**: Streamlined `workflow_id` handling; added session creation assertion.
- **`DSPyService`**: Cleaner async task creation in `compile_module_async`.

#### Frontend

- **`src/frontend/src/components/ui/`**: Added Skeleton, Tabs, Textarea, Tooltip components.
- **`src/frontend/src/contexts/`**: Added ThemeContext for centralized theme management.

#### Documentation

- **`docs/plans/2025-12-15-frontend-restructure-design.md`** (NEW): Approved design for feature-based frontend structure.
- **`provision_cosmos` script**: Updated documentation with usage examples and container descriptions.

### Bug Fixes

- **Fixed `load_config` import path** – Resolved module import error in reasoner that could cause startup failures.
- **Fixed reasoning effort cleanup** – Proper cleanup on workflow timeout prevents resource leaks.
- **Fixed LiteLLM test teardown** – Suppressed noisy cleanup errors during test execution.
- **Fixed ChatMessage field preservation** – Pydantic model cloning ensures all fields are properly propagated.
- **Fixed predictor initialization** – Corrected DSPy predictor setup for version compatibility.
- **Fixed conversation context injection** – Proper injection of conversation history into workflow context.
- **Fixed Jaeger image version** – Pinned to stable version preventing tracing failures.

### Security

- **Log injection prevention** – Addressed CodeQL alerts #164, #165, #166, #167, #169 by sanitizing user input before logging.

### Tests

- **Phase 3 & 4 integration tests** – Validates compiled module loading and caching.
- **Tracing initialization tests** – Ensures YAML config properly initializes OpenTelemetry.
- **FastPath detector tests** – Unit tests for simple task routing logic.
- **EventNarrator tests** – Coverage for DSPy-based event narration.
- **Profiling utility tests** – Tests for performance monitoring decorators.
- **TTL cache tests** – Comprehensive tests for time-based caching.
- **Background quality evaluation tests** – Tests for async quality assessment.

### Migration Notes

- **Update imports**: `from agentic_fleet.utils.config` → `from agentic_fleet.utils.cfg`
- **Legacy compatibility**: Re-exports maintained in package `__init__.py` files for backward compatibility.
- **No breaking changes**: Existing workflows continue to work without modification.

### Stats

- **93 commits** in this release
- **390 files changed**
- **+36,121 insertions**, **-16,352 deletions**
- **55 test files** added or updated

---

## v0.6.9 (2025-12-07) – DSPy Typed Signatures, Workflow Refactor & Docs

### Highlights

#### Typed Pydantic Models for Structured Outputs

- **Pydantic-based output models** – New `typed_models.py` module provides validated, type-safe outputs from DSPy predictions.
- **Automatic coercion** – Comma-separated strings automatically convert to lists; scores clamp to valid ranges.
- **8 typed output models** – `RoutingDecisionOutput`, `TaskAnalysisOutput`, `QualityAssessmentOutput`, `ProgressEvaluationOutput`, `ToolPlanOutput`, `WorkflowStrategyOutput`, `HandoffDecisionOutput`, `CapabilityMatchOutput`.
- **Field validators** – Normalize execution modes to lowercase, validate literal values, and enforce constraints.

#### DSPy Assertions for Routing Validation

- **Expanded assertions module** – Comprehensive validation functions for routing decisions.
- **Hard constraints** – `assert_valid_agents()`, `assert_valid_tools()`, `assert_mode_agent_consistency()` for critical validations.
- **Soft suggestions** – `suggest_valid_agents()`, `suggest_valid_tools()`, `suggest_mode_agent_consistency()` for optimization hints.
- **Task type detection** – `detect_task_type()` classifies tasks as research/coding/analysis/writing/general with keyword sets.
- **Routing assertions decorator** – `@with_routing_assertions()` for assertion-driven backtracking.

#### Typed Signatures for DSPy 3.x

- **7 typed signatures** – `TypedTaskAnalysis`, `TypedTaskRouting`, `TypedEnhancedRouting`, `TypedQualityAssessment`, `TypedProgressEvaluation`, `TypedToolPlan`, `TypedWorkflowStrategy`.
- **Pydantic output fields** – Signatures use Pydantic models as `dspy.OutputField()` types for JSON schema compliance.
- **DSPy 3.x compatibility** – Leverages DSPy's native Pydantic support for structured outputs.

#### Workflow Refactor & Message Consolidation

- **Consolidated Message Models** – Merged message-related classes from `messages.py` into `models.py` for better organization.
- **Streamlined Group Chat** – Introduced `GroupChatBuilder` in `group_chat_adapter.py` and removed redundant builder files.
- **API Versioning** – Adjusted API versioning in frontend client and tests to align with new endpoint structure.

#### Documentation Updates

- **Project Overview** – Updated `GEMINI.md` with comprehensive project overview, structure, and development conventions.
- **Tracing Configuration** – Added comprehensive documentation for `TracingConfig` `capture_sensitive` field with security notes.
- **Tavily MCP Tool** – Added tests and documentation for Bearer token authentication.

#### Performance Optimization

- **Routing cache** – TTL-based caching for routing decisions to avoid redundant LLM calls.
- **Cache configuration** – `enable_routing_cache`, `cache_ttl_seconds` settings in workflow config.
- **Lazy module initialization** – Typed predictors initialized on first use.

### Changes

#### Backend

- **`src/agentic_fleet/dspy_modules/typed_models.py`** (NEW):
  - Pydantic models for all DSPy outputs.
  - Field validators for normalization and coercion.
  - `coerce_list()` helper for comma-separated string → list conversion.
  - Score clamping for `QualityAssessmentOutput` and `CapabilityMatchOutput`.

- **`src/agentic_fleet/dspy_modules/signatures.py`**:
  - Added 7 typed signature classes using Pydantic output models.
  - Sorted `__all__` alphabetically per ruff RUF022.

- **`src/agentic_fleet/dspy_modules/reasoner.py`**:
  - Added `use_typed_signatures` parameter (default: `True`).
  - Added `enable_routing_cache` and `cache_ttl_seconds` parameters.
  - Added routing cache with `_get_cache_key()`, `_get_cached_routing()`, `_cache_routing()`, `clear_routing_cache()`.
  - Added `_extract_typed_routing_decision()` for Pydantic model → dict conversion.

- **`src/agentic_fleet/dspy_modules/assertions.py`**:
  - Added `validate_agent_exists()`, `validate_tool_assignment()`, `validate_mode_agent_match()`.
  - Added `detect_task_type()` with keyword frozensets.
  - Added `validate_routing_decision()`, `validate_full_routing()`.
  - Added assertion wrappers: `assert_valid_agents()`, `assert_valid_tools()`, `assert_mode_agent_consistency()`.
  - Added suggestion wrappers: `suggest_valid_agents()`, `suggest_valid_tools()`, `suggest_mode_agent_consistency()`.
  - Added `suggest_task_type_routing()` for task-type specific routing suggestions.
  - Added `with_routing_assertions()` decorator.
  - Exported keyword sets: `RESEARCH_KEYWORDS`, `CODING_KEYWORDS`, `ANALYSIS_KEYWORDS`, `WRITING_KEYWORDS`.

- **`src/agentic_fleet/workflows/executors.py`**:
  - Integrated `detect_task_type` and `validate_full_routing` in `RoutingExecutor`.
  - Added routing validation after DSPy routing decisions.

- **`src/agentic_fleet/workflows/models.py`**:
  - Consolidated message dataclasses and streaming events.
  - Merged content from `messages.py`.

- **`src/agentic_fleet/workflows/group_chat_adapter.py`**:
  - Introduced `GroupChatBuilder` for streamlined management.

- **`src/agentic_fleet/tools/tavily_mcp_tool.py`**:
  - Added Bearer token authentication support.

- **`src/agentic_fleet/config/workflow_config.yaml`**:
  - Added `use_typed_signatures: true` setting.
  - Added `enable_routing_cache: true` setting.
  - Added `cache_ttl_seconds: 300` setting.

#### Documentation

- **`GEMINI.md`**:
  - Comprehensive update of project overview and conventions.

- **`docs/consolidation_analysis_report.md`**:
  - Added consolidation analysis report.

#### Tests

- **`tests/dspy_modules/test_typed_models.py`** (NEW):
  - 44 tests covering all Pydantic models.
  - Tests for field coercion, normalization, clamping, and validation.
  - Tests for model serialization/deserialization.

- **`tests/dspy_modules/test_assertions.py`** (NEW):
  - 39 tests for assertion functions.
  - Tests for agent validation, tool validation, mode/agent matching.
  - Tests for task type detection with keyword coverage.
  - Tests for assertion and suggestion wrappers.

- **`tests/dspy_modules/test_reasoner.py`**:
  - Added `TestTypedSignatures` class (6 tests).
  - Added `TestRoutingCache` class (6 tests).
  - Added `TestTypedRoutingExtraction` class (4 tests).
  - Added `TestBackwardCompatibility` class (4 tests).

### Configuration

New settings in `workflow_config.yaml`:

```yaml
dspy:
  optimization:
    use_typed_signatures: true # Use Pydantic output models
    enable_routing_cache: true # Cache routing decisions
    cache_ttl_seconds: 300 # Cache TTL (5 minutes)
```

### Migration Notes

- **No breaking changes** – Existing workflows continue to work.
- **Typed signatures enabled by default** – Set `use_typed_signatures: false` to disable.
- **Routing cache enabled by default** – Set `enable_routing_cache: false` to disable.
- **Field name consistency** – `RoutingDecisionOutput` uses `execution_mode` (not `mode`).

---

## v0.6.8 (2025-12-05) – Dev CLI, NLU Module & Frontend UX Overhaul

### Highlights

#### New `agentic-fleet dev` CLI Command

- **One-command development server** – Start both FastAPI backend and Vite frontend with `agentic-fleet dev`.
- **Flexible options** – Custom ports (`--backend-port`, `--frontend-port`), backend-only (`--no-frontend`), or frontend-only (`--no-backend`).
- **Graceful shutdown** – Both processes terminate cleanly on Ctrl+C.
- **Three script aliases** – `agentic-fleet`, `agenticfleet`, and `fleet` all work identically.

#### DSPy NLU Module

- **Intent Classification** – New `DSPyNLU` module with `classify_intent()` for routing user intents.
- **Entity Extraction** – `extract_entities()` identifies people, organizations, dates, and other entity types.
- **API Endpoints** – REST endpoints at `/api/v1/classify_intent` and `/api/v1/extract_entities`.
- **Offline Compilation** – NLU module follows the offline-only compilation pattern with cache at `.var/logs/compiled_nlu.pkl`.

#### Event Mapping Refactor

- **Dedicated events module** – Extracted event mapping logic into `src/agentic_fleet/app/events/mapping.py`.
- **UI hints and categories** – Events now include `category` and `ui_hint` fields for frontend component routing.
- **Rule-based classification** – `classify_event()` maps event types to semantic categories (STEP, THOUGHT, REASONING, PLANNING, OUTPUT, etc.).

#### Frontend UX Improvements

- **Native reconnecting WebSocket** – Replaced unmaintained `reconnecting-websocket` package with native implementation featuring exponential backoff.
- **Workflow visualization components** – New `OrchestratorPanel`, `AgentGroup`, `SmartWorkflowDisplay`, and `WorkflowRenderer` components.
- **Enhanced useChat hook** – Better deduplication, workflow phase tracking, and agent activity display.
- **Design tokens system** – New CSS custom properties for consistent theming (`variables-primitive.css`, `variables-semantic.css`, `variables-components.css`).
- **Error boundaries** – Added `ErrorBoundary` component for graceful error handling.
- **Improved animations** – Shared animation library in `lib/animations.ts`.
- **Code block enhancements** – Header with language label, copy button, and dark theme support.
- **Persistent conversations** – Sidebar now displays conversation history with click-to-load.

#### Documentation

- **New Frontend Guide** – `docs/users/frontend.md` with comprehensive coverage of web interface features.
- **Updated Getting Started** – Added web interface section with `agentic-fleet dev` instructions.
- **Quick Reference updates** – CLI development commands documented.

### Changes

#### Backend

- **`src/agentic_fleet/cli/commands/dev.py`** (NEW):
  - `dev()` command launches uvicorn + npm concurrently.
  - Signal handling for graceful process termination.
  - Rich console output with status messages.

- **`src/agentic_fleet/cli/console.py`**:
  - Registered `dev` command in Typer app.

- **`src/agentic_fleet/app/events/mapping.py`** (NEW):
  - `classify_event()` for rule-based UI component routing.
  - `map_workflow_event()` converts internal events to `StreamEvent`.
  - Handles reasoning, agent messages, phase completions, and workflow output.

- **`src/agentic_fleet/app/routers/nlu.py`** (NEW):
  - `/classify_intent` endpoint for intent classification.
  - `/extract_entities` endpoint for entity extraction.
  - Uses workflow's `dspy_reasoner.nlu` module.

- **`src/agentic_fleet/dspy_modules/nlu.py`** (NEW):
  - `DSPyNLU` class with lazy-loaded ChainOfThought modules.
  - `get_nlu_module()` factory with compiled cache loading.

- **`src/agentic_fleet/dspy_modules/nlu_signatures.py`** (NEW):
  - `IntentClassification` signature for intent detection.
  - `EntityExtraction` signature for named entity recognition.

- **`src/agentic_fleet/dspy_modules/reasoner.py`**:
  - Added `nlu` property for lazy-loaded NLU module.
  - `analyze_task()` now performs NLU analysis first.

- **`src/agentic_fleet/app/routers/streaming.py`**:
  - Refactored to use `map_workflow_event()` from events module.
  - Reduced from ~700 lines to ~450 lines.

- **`src/agentic_fleet/app/conversation_store.py`** (NEW):
  - In-memory conversation persistence with JSON file backup.

- **`src/agentic_fleet/app/middleware.py`** (NEW):
  - Request logging middleware for debugging.

- **`src/agentic_fleet/utils/tracing.py`**:
  - Enhanced OpenTelemetry configuration.

- **`pyproject.toml`**:
  - Added `agenticfleet` script alias.

#### Frontend

- **`src/frontend/src/lib/reconnectingWebSocket.ts`** (NEW):
  - Native WebSocket wrapper with exponential backoff.
  - Configurable max retries and reconnection delays.
  - Same API as native WebSocket for drop-in replacement.

- **`src/frontend/src/components/workflow/`** (NEW):
  - `OrchestratorPanel.tsx` - Displays orchestrator routing/analysis/quality steps.
  - `AgentGroup.tsx` - Groups and displays agent activity.
  - `SmartWorkflowDisplay.tsx` - Smart display with collapsible sections.
  - `WorkflowRenderer.tsx` - Top-level workflow visualization.
  - `utils.ts` - Event grouping and categorization utilities.
  - `types.ts` - TypeScript interfaces for workflow visualization.

- **`src/frontend/src/components/ErrorBoundary.tsx`** (NEW):
  - React error boundary for graceful error handling.

- **`src/frontend/src/components/AnimatedMessage.tsx`** (NEW):
  - Animated message transitions.

- **`src/frontend/src/components/MessageSkeleton.tsx`** (NEW):
  - Loading skeleton for messages.

- **`src/frontend/src/lib/animations.ts`** (NEW):
  - Shared animation definitions (fade, slide, scale).

- **`src/frontend/src/lib/codeDetection.ts`** (NEW):
  - Utilities for detecting code blocks in messages.

- **`src/frontend/src/styles/`** (NEW):
  - `variables-primitive.css` - Base design tokens (colors, spacing, typography).
  - `variables-semantic.css` - Semantic variables (surfaces, text, borders).
  - `variables-components.css` - Component-specific variables.
  - `base.css`, `globals.css`, `utilities.css` - Organized CSS architecture.

- **`src/frontend/src/hooks/useChat.ts`**:
  - Replaced `reconnecting-websocket` with native implementation.
  - Added `requestSentRef` to prevent duplicate requests on reconnection.
  - Enhanced step deduplication with `isDuplicateStep()`.
  - Added workflow phase tracking for shimmer display.

- **`src/frontend/src/hooks/useStreamingBatcher.ts`** (NEW):
  - Batches rapid streaming updates for performance.

- **`src/frontend/src/components/prompt-kit/code-block.tsx`**:
  - Added header with language label.
  - Added copy-to-clipboard button.
  - Dark theme support.

- **`src/frontend/src/api/client.ts`**:
  - Added `classifyIntent()` and `extractEntities()` methods.

- **`src/frontend/src/api/types.ts`**:
  - Added `IntentRequest`, `IntentResponse`, `EntityRequest`, `EntityResponse` types.

- **`src/frontend/package.json`**:
  - Removed `reconnecting-websocket` dependency.

#### Documentation

- **`docs/users/frontend.md`** (NEW):
  - Quick start with `agentic-fleet dev`.
  - Chat interface and workflow visualization features.
  - Development workflow (testing, linting, building).
  - WebSocket protocol overview.
  - Troubleshooting section.

- **`docs/users/getting-started.md`**:
  - Added "Using the Web Interface" section.
  - Updated CLI examples to use `agentic-fleet` directly.

- **`docs/guides/quick-reference.md`**:
  - Added `agentic-fleet dev` commands.

- **`docs/INDEX.md`**:
  - Added Frontend Guide to user documentation.
  - Added Frontend Development section for developers.

#### Tests

- **`tests/app/events/test_mapping.py`** (NEW):
  - Tests for `classify_event()` and `map_workflow_event()`.
  - Coverage for reasoning, agent messages, and phase completions.

- **`tests/app/test_nlu_endpoints.py`** (NEW):
  - Tests for NLU API endpoints with mocked workflow.

- **`tests/dspy_modules/test_nlu.py`** (NEW):
  - Unit tests for `DSPyNLU` module.

- **`tests/app/test_conversation_store.py`** (NEW):
  - Tests for conversation persistence.

- **`tests/app/test_logging_json.py`** (NEW):
  - Tests for JSON logging configuration.

- **`tests/utils/test_tracing.py`** (NEW):
  - Tests for OpenTelemetry tracing utilities.

### Bug Fixes

- **Fixed attribute name mismatch** – NLU router now uses `workflow.dspy_reasoner` instead of non-existent `workflow.reasoner`.
- **Fixed import path** – `MagenticAgentMessageEvent` imported from local module instead of `agent_framework._workflows`.
- **Fixed duplicate WebSocket requests** – Added guard to prevent re-sending on reconnection.
- **Fixed frontend lint errors** – Resolved ESLint warnings across components.

### Migration Notes

- **New CLI command**: Use `agentic-fleet dev` instead of `make dev` for unified development server.
- **Script aliases**: All three work identically: `agentic-fleet`, `agenticfleet`, `fleet`.
- **WebSocket package**: The `reconnecting-websocket` npm package has been removed in favor of a native implementation.

---

## v0.6.7 (2025-12-04) – Simple Task Routing & Evaluation Framework

### Highlights

#### Routing Intelligence

- **Improved Simple Task Detection** – `is_simple_task()` now correctly identifies factual questions, math expressions, and direct queries, routing them to fast-path instead of multi-agent workflows.
- **70%+ of simple queries** that previously triggered complex orchestration now get direct LLM responses.
- **Sub-second responses** for simple questions like "What is 2+2?" or "Hello" that previously took 30-90 seconds.

#### Evaluation Framework

- **New Evaluation Script** – `scripts/evaluate_history.py` scores execution history using DSPy with configurable models (default: gpt-5-nano).
- **Quality Metrics** – Evaluates correctness, completeness, and provides detailed reasoning for each score (1-10 scale).
- **High-Quality Dataset Export** – Automatically filters and saves high-scoring examples to `.var/logs/high_quality_examples.jsonl` for DSPy training.

### Performance Impact

| Metric                         | Before | After  |
| ------------------------------ | ------ | ------ |
| Simple task routing accuracy   | ~30%   | ~95%   |
| "What is 2+2?" response time   | 30-90s | <1s    |
| Factual questions to fast-path | Rarely | Always |

### Changes

#### Backend

- **`src/agentic_fleet/workflows/helpers.py`**:
  - Expanded `is_simple_task()` with math patterns (`7+7`, `what is 2+2`)
  - Added simple question starters (`what is`, `explain`, `list`, `who is`, `where is`, etc.)
  - Added word count heuristics (tasks under 8 words without complex keywords → simple)
  - Added complex pattern exclusions (`help me plan`, `create a comprehensive`, `include activities`)

- **`scripts/evaluate_history.py`** (NEW):
  - DSPy-based evaluation with `AnswerQuality` signature
  - Explicit scoring rubric (1-10 scale prioritizing correctness)
  - `is_correct` and `is_complete` intermediate fields for better reasoning
  - Incremental result saving to `.var/logs/evaluation_results.jsonl`
  - Summary statistics (average, min, max scores)

---

## v0.6.6 (2025-12-01) – Latency Optimization, Frontend Overhaul & Conversation History

### Highlights

#### Performance

- **66% Latency Reduction** – Complex queries now complete in ~2 minutes vs ~6 minutes previously. Achieved by removing the redundant Judge phase and optimizing DSPy module selection.
- **5-Phase Pipeline** – Workflow graph simplified from 6 phases to 5: `analysis → routing → execution → progress → quality`. The redundant `JudgeRefineExecutor` has been removed.
- **DSPy Module Optimization** – Switched `self.router` from `dspy.ChainOfThought` to `dspy.Predict` for faster routing without reasoning traces.
- **Fast Model Tier** – Added `dspy.routing_model: gpt-5-mini` configuration for cost-effective analysis/routing phases.

#### Frontend Architecture

- **Modernized Frontend Architecture** – Complete refactor of the React frontend to align with the new 5-phase pipeline and event streaming model.
- **Event-Driven UI** – New `WorkflowEvents` and `ChatStep` components to visualize granular execution progress (Analysis → Routing → Execution).
- **Simplified State** – Removed legacy `useStreamingChat` in favor of a robust `useChat` hook with better error handling and type safety.
- **Component Cleanup** – Deleted 20+ deprecated UI components (`chat-container`, `markdown`, `code-block`) to reduce technical debt.
- **Prompt Kit Integration** – Added `prompt-kit` for enhanced input handling with Steps, Markdown, TextShimmer, Reasoning, ChainOfThought, and Message components.
- **Schema Alignment** – Fixed all frontend TypeScript types to match backend Pydantic schemas for proper real-time streaming.

#### Conversation History

- **Conversation History in Sidebar** – Sidebar now displays all past conversations with titles, timestamps, and click-to-load functionality.
- **Message Persistence Fix** – Assistant responses are now properly saved to conversations, enabling conversation reload.
- **Auto-Generated Conversation Titles** – Conversations are automatically titled based on the first user message instead of "New Chat".
- **Streaming Memoization** – Added message ID propagation for Markdown block-level memoization during streaming responses.

### Performance Results

| Phase     | Before     | After          |
| --------- | ---------- | -------------- |
| Analysis  | ~15s       | 10.7s          |
| Routing   | ~25s       | 20.0s          |
| Execution | ~180s      | 66.6s          |
| Progress  | ~15s       | 11.5s          |
| Quality   | ~20s       | 12.9s          |
| **Judge** | **~60s**   | **0.0003s** ✅ |
| **Total** | **~6 min** | **~2 min**     |

### Changes

#### Backend

- **`src/agentic_fleet/workflows/builder.py`**:
  - Removed `JudgeRefineExecutor` import and workflow edge.
  - Pipeline now terminates at `QualityExecutor`.

- **`src/agentic_fleet/config/workflow_config.yaml`**:
  - Added `dspy.routing_model: gpt-5-mini` for fast cognitive tasks.
  - Set `quality.enable_judge: false` to disable judge evaluation.
  - Set `quality.max_refinement_rounds: 0` to disable refinement loops.

- **`src/agentic_fleet/dspy_modules/signatures.py`**:
  - Removed `JudgeEvaluation` signature class (redundant with `QualityAssessment`).

- **`src/agentic_fleet/dspy_modules/reasoner.py`**:
  - Removed `self.judge` module initialization.
  - Changed `self.router` from `dspy.ChainOfThought` → `dspy.Predict`.
  - Updated `predictors()` and `named_predictors()` to exclude judge module.

- **`src/agentic_fleet/workflows/executors.py`**:
  - Added deprecation warning to `JudgeRefineExecutor` (retained for backwards compatibility).

- **`src/agentic_fleet/app/routers/streaming.py`**:
  - Fixed unreachable code in `_map_workflow_event` (RoutingMessage, QualityMessage, ProgressMessage handlers were incorrectly nested).
  - Fixed message capture to save assistant responses from `RESPONSE_COMPLETED`, `AGENT_OUTPUT`, and `AGENT_MESSAGE` events.

- **`src/agentic_fleet/app/dependencies.py`**:
  - `add_message()` now auto-updates conversation title from first user message content.

#### Frontend

- **`src/frontend/src/api/types.ts`**:
  - Added `reasoning_effort` to `ChatRequest` for per-request GPT-5 reasoning control.
  - Added `reasoning_partial` to `StreamEvent` for interrupted reasoning detection.
  - Fixed `WorkflowSession` schema (`session_id` → `workflow_id`, added `task`, `started_at`, `completed_at`).
  - Fixed `AgentInfo` schema (added `type`, removed non-existent `capabilities`).

- **`src/frontend/src/api/client.ts`**:
  - Added `listConversations()` method to fetch all conversations.
  - Added `loadConversationMessages()` method to load a specific conversation's messages.

- **`src/frontend/src/hooks/useChat.ts`**:
  - Added `SendMessageOptions` interface with `reasoning_effort` parameter.
  - Added `conversations` state array for sidebar display.
  - Added `loadConversations()` to fetch conversation list from backend.
  - Added `selectConversation(id)` to switch between conversations and load their messages.
  - Enhanced error handling to preserve partial reasoning when `reasoning_partial` is true.
  - Fixed missing `AbortController` signal in API calls (cancel button now works).
  - Added explicit handling for user-initiated stream abortion.
  - Added duplicate message prevention in `response.completed` handler.

- **`src/frontend/src/components/`**:
  - Added `AgentMessageGroup.tsx`, `ChatStep.tsx`, `WorkflowEvents.tsx`.
  - Synchronized `WORKFLOW_EVENT_TYPES` between `WorkflowEvents.tsx` and `MessageBubble.tsx`.
  - Deleted legacy components: `chat-container.tsx`, `message.tsx`, `response-stream.tsx`, etc.

- **`src/frontend/src/components/Sidebar.tsx`**:
  - Now accepts `conversations`, `currentConversationId`, and `onSelectConversation` props.
  - Displays real conversations instead of hardcoded placeholders.
  - Shows relative timestamps ("Today", "Yesterday", "X days ago").
  - Highlights the currently active conversation.

- **`src/frontend/src/components/Layout.tsx`**:
  - Extended props to pass conversation data to Sidebar.

- **`src/frontend/src/components/MessageBubble.tsx`**:
  - Added `id` prop for message identification.
  - Passes `id` to `MessageContent` for Markdown memoization during streaming.

- **`src/frontend/src/components/WorkflowEvents.tsx`**:
  - Refined styling to better match prompt-kit Steps component patterns.

- **`src/frontend/src/App.tsx`**:
  - Wired up conversation list loading and selection.
  - Passes `id` prop to `MessageBubble` for memoization optimization.

### Bug Fixes

- **Cancel Streaming** – Fixed cancel button not aborting HTTP requests (missing AbortController signal).
- **Phase Event Mapping** – Fixed `RoutingMessage`, `QualityMessage`, and `ProgressMessage` events not being emitted (unreachable code bug).
- **Workflow Events Display** – Added `agent_thought` and `agent_output` to workflow event types for consistent display.
- **Conversation Messages Not Saving** – Fixed assistant responses not being persisted due to incorrect event type matching.
- **Empty Conversation Titles** – Conversations now show meaningful titles from user's first message.
- **Conversation Selection** – Clicking a conversation in sidebar now properly loads its messages.
- **Duplicate Final Answer Messages** – Fixed potential duplicate messages when `response.completed` content matched existing content.

### Schema Alignment (Frontend ↔ Backend)

| Type              | Field               | Before         | After           |
| ----------------- | ------------------- | -------------- | --------------- |
| `WorkflowSession` | `session_id`        | ✗ wrong name   | `workflow_id` ✓ |
| `WorkflowSession` | `task`              | ✗ missing      | ✓ added         |
| `WorkflowSession` | `started_at`        | ✗ missing      | ✓ added         |
| `WorkflowSession` | `completed_at`      | ✗ missing      | ✓ added         |
| `AgentInfo`       | `type`              | ✗ missing      | ✓ added         |
| `AgentInfo`       | `capabilities`      | ✗ non-existent | removed         |
| `ChatRequest`     | `reasoning_effort`  | ✗ missing      | ✓ added         |
| `StreamEvent`     | `reasoning_partial` | ✗ missing      | ✓ added         |

### Migration Notes

- **Clear DSPy Cache**: Run `uv run python -m agentic_fleet.scripts.manage_cache --clear` after upgrading.
- **Custom Workflows**: If you used `JudgeRefineExecutor` in custom workflow configurations, it will emit a deprecation warning but continue to function.
- **Quality Assessment**: The `QualityAssessment` signature still provides scoring—only the redundant judge layer was removed.
- **Existing Conversations**: No breaking changes. Existing conversations created before this update will retain "New Chat" titles but new messages will be saved correctly.

---

## v0.6.5 (2025-11-28) – DSPy Dynamic Prompt, GEPA Enhancement & Discussion Mode

### Highlights

- **Offline Layer Architecture** – Enforced strict separation between offline DSPy compilation and runtime execution. Runtime compilation is now explicitly disabled in `initialization.py`, ensuring zero-latency overhead for optimized prompts.
- **Dynamic Agent Prompts** – Introduced `PlannerInstructionSignature` and updated `AgentFactory` to support dynamic, optimizer-tunable agent instructions, replacing static prompt templates for the Planner agent.
- **Discussion Mode** – Introduced a new interaction mode enabling multi-agent group chats and discussions.
- **Enhanced GEPA Optimizer** – Upgraded `GEPAConfig` with latency-aware metrics (`gepa_latency_weight`) and assertion-aware feedback (`gepa_feedback_weight`) to optimize for both quality and speed.
- **Systematic Assertions** – Integrated `dspy.Assert` and `dspy.Suggest` into routing logic (`reasoner.py`, `signatures.py`) to enforce critical constraints (e.g., valid agent count) and provide soft guidance (e.g., tool availability).
- **Bridge Middleware** – Implemented `BridgeMiddleware` to capture runtime execution history and convert it into DSPy training examples, closing the data feedback loop.
- **Agent Framework Alignment** – Updated `WorkflowOutputEvent` to return `list[ChatMessage]` instead of a dictionary, aligning with the latest `agent-framework` SDK breaking changes.
- **RAG Integration** – Added `AzureAISearchContextProvider` implementation for retrieval-augmented generation within agent workflows.

### Internal Improvements

- **MCP Tool Refactor** – Consolidated MCP tool logic into a reusable `BaseMCPTool` class, improving connection reliability and reducing code duplication (#391).
- **Resilience** – Enhanced error handling with specific exceptions and configurable thresholds (#392).

### Changes

- **`src/agentic_fleet/workflows/initialization.py`**:
  - Explicitly disabled runtime compilation (`compile_dspy=False`) to enforce the Offline Layer pattern.

- **`src/agentic_fleet/dspy_modules/agent_signatures.py`**:
  - Added `PlannerInstructionSignature` for dynamic instruction generation.

- **`src/agentic_fleet/agents/coordinator.py`**:
  - Updated `AgentFactory` to use `PlannerInstructionSignature` when available, enabling dynamic prompts.

- **`src/agentic_fleet/dspy_modules/reasoner.py`**:
  - Integrated `dspy.Assert` and `dspy.Suggest` into `_robust_route` for validation.

- **`src/agentic_fleet/dspy_modules/signatures.py`**:
  - Added assertion logic to `EnhancedTaskRouting` signature.

- **`src/agentic_fleet/api/middlewares.py`**:
  - Added `BridgeMiddleware` for history capture and conversion.

- **`src/agentic_fleet/workflows/supervisor.py`**:
  - Updated `WorkflowOutputEvent` to return `list[ChatMessage]`.

- **`src/agentic_fleet/tools/azure_search_provider.py`**:
  - Added `AzureAISearchContextProvider` implementation.

- **`src/agentic_fleet/config/workflow_config.yaml`** (schema):
  - Added `gepa_latency_weight` and `gepa_feedback_weight` to `GEPAConfig`.

### Migration Notes

- **Workflow Output Format**: If you consume `WorkflowOutputEvent.data`, update your code to handle `list[ChatMessage]` instead of a dictionary.
- **Offline Compilation**: Ensure you run `scripts/optimize.py` (or `make optimize`) to generate cached modules before deploying to production, as runtime compilation is now disabled.

---

## v0.6.4 (2025-11-25) – Code Quality & Type Safety Improvements

### Highlights

- **Pydantic V2 Migration** – Migrated deprecated `class Config` to `model_config = ConfigDict()` pattern, eliminating Pydantic deprecation warnings and ensuring compatibility with Pydantic V3.
- **Improved Type Safety** – Added proper return type annotations for async generators, defined `WorkflowEvent` type alias, and fixed 4 type checker errors across workflow modules.
- **Dependency Hygiene** – Moved dev/test dependencies (`pytest`, `ruff`, `mypy`, `flake8`, `locust`) from main dependencies to `[dependency-groups.dev]`.
- **Dynamic Versioning** – Package version is now read dynamically from `pyproject.toml` using `importlib.metadata`, eliminating version mismatch issues.
- **Refactored Fast-Path Logic** – Consolidated duplicate fast-path code in `SupervisorWorkflow` into reusable helper methods.
- **Better Error Handling** – `ToolRegistry.execute_tool()` now raises typed `ToolError` exceptions with full context instead of returning error strings.
- **Deduplicated Retry Logic** – Consolidated 4 identical `_call_with_retry` methods into a shared `async_call_with_retry` utility in `resilience.py`.
- **Documented Graceful Degradation** – Added documentation comments to all executor exception handlers explaining the intentional broad exception handling pattern for system availability.
- **Centralized Environment Variables** – Added `EnvConfig` class with instance-level caching (replacing `@lru_cache` on methods to avoid memory leaks) for typed environment variable access.
- **Phase A-E Code Quality Plan Completed** – All 14 items evaluated (12 completed, 1 partial, 1 deferred, 1 not recommended). Added 97 new unit tests, standardized docstrings, and improved type safety.
- **Makefile Cleanup** – Removed non-existent targets (`demo-hitl`, `validate-agents`, `test-automation`, `load-test-*`) and added `analyze-history` and `self-improve` targets for existing scripts.
- **GitHub Actions Workflow Overhaul** – Simplified and modernized all 8 CI/CD workflows with best practices, semver action versions, and `uv publish` for trusted publishing.

### Changes

- **`src/agentic_fleet/__init__.py`**:
  - Version now read dynamically via `importlib.metadata.version("agentic-fleet")` with fallback for editable installs.

- **`src/agentic_fleet/api/schemas/chat.py`**:
  - Migrated `Message` and `Conversation` models from deprecated `class Config` to `model_config = ConfigDict(from_attributes=True)`.

- **`src/agentic_fleet/workflows/supervisor.py`**:
  - Added `WorkflowEvent` type alias for workflow events union type.
  - Added `AsyncIterator[WorkflowEvent]` return type to `run_stream()` method.
  - Extracted `_should_fast_path()` and `_handle_fast_path()` helper methods to eliminate code duplication.
  - Added type assertions to satisfy type checker for `dspy_reasoner` attribute.

- **`src/agentic_fleet/workflows/executors.py`**:
  - Removed 4 duplicate `_call_with_retry` methods from `AnalysisExecutor`, `RoutingExecutor`, `ProgressExecutor`, and `QualityExecutor`.
  - Now uses shared `async_call_with_retry` utility from `resilience.py`.
  - Added documentation comments to all `except Exception` handlers explaining the graceful degradation pattern.

- **`src/agentic_fleet/utils/resilience.py`**:
  - Added `async_call_with_retry[T]()` function for centralized retry logic.
  - Uses PEP 695 type parameters for modern generic syntax.
  - Supports both sync and async callables with configurable attempts and backoff.
  - Logs retry attempts via existing `log_retry_attempt` callback.

- **`src/agentic_fleet/utils/tool_registry.py`**:
  - `execute_tool()` now raises `ToolError` with tool name and arguments context instead of returning error strings.

- **`.github/workflows/*.yml`** (all 8 workflows):
  - **ci.yml**: Removed Windows from test matrix (per `pyproject.toml`), removed redundant import sorting check, used `uv sync --frozen` (auto-detects Python from `pyproject.toml`), simplified branch triggers.
  - **release.yml**: Migrated to `uv publish --trusted-publishing always` per [uv docs](https://docs.astral.sh/uv/guides/integration/github/#publishing-to-pypi), removed unnecessary Python install steps.
  - **codeql.yml**: Removed non-existent branches (`develop`, `0.5.0a`).
  - **dependency-review.yml**: Removed non-existent branches.
  - **pre-commit-autoupdate.yml**: Used `uv tool install pre-commit`, fixed deterministic branch naming.
  - **All workflows**: Updated to semver action versions (`@v4`, `@v5`) instead of SHA hashes for better readability and dependabot compatibility.
  - Improved error handling with exception chaining (`from e`) to preserve stack traces.

- **`pyproject.toml`**:
  - Removed dev/test packages from main `dependencies`: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `flake8`, `locust`.
  - Added `mypy`, `flake8`, `locust` to `[dependency-groups.dev]`.
  - Removed redundant CLI aliases (`dynamic-fleet`, `workflow`), keeping only `agentic-fleet` and `fleet`.

- **`src/agentic_fleet/utils/env.py`**:
  - Added `EnvConfig` class with instance-level dictionary caching (avoiding `@lru_cache` on methods which causes memory leaks - B019).
  - Added `get_env_bool()`, `get_env_int()`, `get_env_float()` helper functions with type safety.
  - Added `env_config` singleton instance for easy access throughout the codebase.
  - Added `clear_cache()` method for testing scenarios where env vars change at runtime.
  - Updated `validate_agentic_fleet_env()` to use `EnvConfig` internally.

- **`Makefile`**:
  - Removed non-existent targets: `demo-hitl`, `validate-agents`, `test-automation`, all `load-test-*` targets.
  - Added `analyze-history` target for `agentic_fleet.scripts.analyze_history`.
  - Added `self-improve` target for `agentic_fleet.scripts.self_improve`.
  - Updated `.PHONY` declaration to match actual targets.

- **`src/agentic_fleet/api/routes/chat.py`**:
  - Fixed `event.message.text` null check (possibly-missing-attribute warning).
  - Fixed `event.output` access using `getattr()` for type safety.

- **`src/agentic_fleet/workflows/strategies.py`**:
  - Fixed `available_agents` dict type annotation for `evaluate_handoff()` call.
  - Added explicit `dict[str, str]` typing with `or ""` for nullable descriptions.

- **`src/agentic_fleet/workflows/supervisor.py`**:
  - Imported `WorkflowMode` type and used `cast()` for type-safe mode switching.

- **`src/agentic_fleet/agents/coordinator.py`**:
  - Now uses `env_config.enable_dspy_agents`, `env_config.openai_api_key`, and `env_config.openai_base_url`.

- **`src/agentic_fleet/utils/logger.py`**:
  - Now uses `env_config.log_format` instead of direct `os.getenv()`.

- **`src/agentic_fleet/cli/utils.py`**, **`src/agentic_fleet/cli/commands/agents.py`**:
  - Migrated to use `env_config.mlflow_dspy_autolog` and `env_config.tavily_api_key`.

- **`src/agentic_fleet/tools/tavily_tool.py`**:
  - Now uses `env_config.tavily_api_key` instead of direct `os.getenv()`.

### Migration Notes

- **Tool Registry Error Handling**: If you were checking for error strings from `ToolRegistry.execute_tool()`, update your code to catch `ToolError` exceptions instead:

  ```python
  # Before
  result = await registry.execute_tool("my_tool", arg="value")
  if result and result.startswith("Error"):
      handle_error(result)

  # After
  from agentic_fleet.workflows.exceptions import ToolError
  try:
      result = await registry.execute_tool("my_tool", arg="value")
  except ToolError as e:
      handle_error(e)
  ```

- **CLI Aliases**: The `dynamic-fleet` and `workflow` CLI commands have been removed. Use `agentic-fleet` or `fleet` instead.

---

## v0.6.3 (2025-11-25) – Agent Framework Compatibility Fixes

### Highlights

- **Agent Framework v0.5+ Compatibility** – Resolved import errors caused by the namespace package structure of `agent_framework` v0.5+.
- **Stability** – Fixed 40+ static analysis errors to ensure `make check` passes cleanly.

### Changes

- Updated imports across the codebase to use specific submodules (`_agents`, `_workflows`, `_tools`, `_mcp`, `_types`) instead of the top-level `agent_framework` package.
- Affected modules:
  - `src/agentic_fleet/agents/base.py`
  - `src/agentic_fleet/agents/coordinator.py`
  - `src/agentic_fleet/api/routes/chat.py`
  - `src/agentic_fleet/cli/runner.py`
  - `src/agentic_fleet/tools/*.py`
  - `src/agentic_fleet/utils/types.py`
  - `src/agentic_fleet/workflows/*.py`

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
├── src/agentic_fleet/data/                    # Training and evaluation data
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
   - `src/agentic_fleet/data/*.jsonl` - Evaluation datasets

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
