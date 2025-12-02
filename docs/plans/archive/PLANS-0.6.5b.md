# AgenticFleet Execution Plans

This document tracks major architectural initiatives, implementation plans, and their status.

## 1. FastAPI App & Streaming Implementation

**Status**: ✅ Completed
**Date**: 2025-11-28

### Motivation

To transform the `agentic-fleet` framework from a CLI-based tool into a scalable backend service capable of supporting a modern React frontend. The primary goals were to enable real-time feedback via streaming, handle concurrent user sessions, and expose the sophisticated multi-agent orchestration logic through a standard HTTP API.

### Objectives

- **Expose Agent Capabilities**: Create RESTful endpoints to trigger workflows and retrieve history.
- **Real-time UX**: Implement Server-Sent Events (SSE) to stream agent thoughts, tool executions, and final answers to the UI.
- **Modern Standards**: Ensure full compliance with Pydantic v2.12+ and FastAPI best practices.
- **Reasoning Support**: Future-proof the API to handle and stream "reasoning" tokens (e.g., from o1/GPT-5 models) separately from content.

### Implementation Details

#### Architecture

- **Framework**: FastAPI (v0.120+) with Uvicorn as the ASGI server.
- **Streaming**: `sse-starlette` used for robust Server-Sent Events implementation.
- **Concurrency**: Async-first design with a `WorkflowSessionManager` to track and limit active workflows.

#### Key Components

1.  **Streaming Router (`/api/chat`)**:
    - Supports `POST` requests with `stream=True`.
    - Yields structured events: `orchestrator.message`, `orchestrator.thought`, `response.delta`, `reasoning.delta`, etc.
    - Handles client disconnects gracefully.

2.  **Session Management**:
    - In-memory `WorkflowSessionManager` tracks active sessions.
    - Enforces `MAX_CONCURRENT_WORKFLOWS` (default: 10) to prevent resource exhaustion.
    - Endpoints to list (`GET /api/sessions`) and cancel (`DELETE /api/sessions/{id}`) sessions.

3.  **Data Models (Pydantic v2)**:
    - Strict typing with `ConfigDict` and `StrEnum`.
    - `ChatRequest` supports `reasoning_effort` configuration.
    - `StreamEvent` handles serialization for SSE.

4.  **Reasoning Capture**:
    - Integrated `ReasoningStreamEvent` to capture and stream raw reasoning deltas from supported models.
    - Configurable logging via `log_reasoning` flag.

### Expected Outcome

A production-ready backend that serves as the foundation for the AgenticFleet web interface. It allows users to interact with agents in real-time, seeing the "thought process" (reasoning/tool use) alongside the final response, mirroring the experience of advanced AI chat interfaces.

### Verification

- **Unit Tests**: Comprehensive suite in `tests/api/` covering schemas, session logic, and endpoint behavior.
- **Integration**: Verified with `curl` and live workflow executions.

## 2. History & DSPy Introspection Endpoints

**Status**: ✅ Completed
**Date**: 2025-11-28

### Motivation

To provide users and developers with deep visibility into the system's operation. Users need to access past conversations (history), while developers need to understand the "mind" of the agent (DSPy prompts and logic) to debug and optimize performance.

### Objectives

- **Conversation Persistence**: Enable browsing, retrieving, and managing past workflow executions.
- **DSPy Transparency**: Expose the internal state of the DSPy reasoner, including active signatures, compiled prompts, and few-shot examples.
- **Configuration Visibility**: Allow runtime inspection of model settings and optimization status.

### Implementation Details

#### 1. Enhanced History API (`/api/history`)

- **Endpoints**:
  - `GET /api/history`: List past executions with pagination (limit/offset) and filtering (by status/mode).
  - `GET /api/history/{workflow_id}`: Retrieve full details of a specific execution, including all steps and metadata.
  - `DELETE /api/history/{workflow_id}`: Delete a specific execution record.
  - `DELETE /api/history`: Clear all history (admin/dev utility).
- **Backend**:
  - Extend `HistoryManager` to support efficient single-item retrieval and deletion.
  - Ensure consistency between file-based logs (`jsonl`) and Cosmos DB mirror.

#### 2. DSPy Introspection API (`/api/dspy`)

- **Endpoints**:
  - `GET /api/dspy/prompts`: Return the active prompts for all reasoner modules (Router, Planner, etc.), including:
    - Signature instructions.
    - Field descriptions.
    - Selected few-shot examples (demos).
  - `GET /api/dspy/config`: Return current DSPy settings (LM provider, temperature, trace settings).
  - `GET /api/dspy/stats`: Return usage statistics (token counts, cache hits) if available.
- **Backend**:
  - Create a new `dspy_router.py`.
  - Implement serialization logic for `dspy.Predict` and `dspy.Signature` objects extracted from `DSPyReasoner.named_predictors()`.

### Expected Outcome

A "Glass Box" experience where the frontend can not only show _what_ the agent did (history) but also _how_ it was instructed to do it (DSPy prompts). This is critical for trust and debugging in agentic systems.

## 3. API Code Quality & Optimization Pass

**Status**: ✅ Completed
**Date**: 2025-11-28

### Motivation

After initial implementation of the FastAPI app and endpoints, a review identified several code quality issues, unused dependencies, and opportunities for optimization and hardening.

### Issues Identified & Fixed

#### 1. Linting & Type Errors

- **`async` without `await`**: `_get_workflow()` in `dependencies.py` was declared `async` but contained no async operations. Removed the `async` keyword.
- **Unused function arguments**: `get_dspy_config()` and `get_dspy_stats()` had unused `workflow` parameters. Removed these as DSPy settings are accessed globally via `dspy.settings`.
- **Missing router export**: `dspy_management` was not exported in `routers/__init__.py`.

#### 2. Improvements

- **API Version Bump**: Incremented API version to `0.3.0` reflecting new features.
- **CORS Origins Parsing**: Improved `_get_allowed_origins()` to strip whitespace from environment values.
- **OpenAPI Docs**: Explicitly set `docs_url`, `redoc_url`, and `openapi_url` for clarity.
- **Readiness Endpoint**: Added `GET /ready` endpoint that checks if the workflow is initialized (useful for k8s probes).
- **Session Cancellation**: Added `DELETE /api/sessions/{workflow_id}` endpoint to cancel running workflows.
- **Type Ignore for CORS**: Added `# type: ignore[arg-type]` for the known FastAPI/Starlette CORS middleware typing issue.

### Verification

- Ran `ruff check` and `ty` on the `app/` module.
- All endpoints remain functional via existing test suite.

## 4. Remove Judge Phase & DSPy Optimization

**Status**: ✅ Completed
**Date**: 2025-11-28

### Motivation

Testing revealed that complex queries (e.g., "Compare and contrast microservices vs monolithic architecture") took ~6 minutes to complete. Analysis identified the 6-phase workflow pipeline as the primary bottleneck, with the JudgeRefineExecutor adding 20-60 seconds of redundant quality evaluation that duplicated QualityAssessment functionality.

### Objectives

- **Eliminate Redundant Judge Phase**: Remove JudgeRefineExecutor from the workflow graph to reduce latency.
- **Optimize DSPy Module Selection**: Switch routing from `ChainOfThought` to `dspy.Predict` where reasoning traces aren't needed.
- **Add Fast Model Tier**: Configure `gpt-5-mini` for DSPy analysis/routing phases to reduce cost and latency.
- **Target Latency**: Reduce complex query execution from ~6 minutes to <90 seconds.

### Implementation Details

#### 1. Workflow Graph Changes (`builder.py`)

- **Before**: `analysis → routing → execution → progress → quality → judge_refine`
- **After**: `analysis → routing → execution → progress → quality` (5 phases)
- Removed `JudgeRefineExecutor` import and edge from workflow graph.

#### 2. Configuration Updates (`workflow_config.yaml`)

- Set `enable_judge: false` to disable judge evaluation.
- Set `max_refinement_rounds: 0` to disable refinement loops.
- Added `dspy.routing_model: gpt-5-mini` for fast cognitive tasks.

#### 3. DSPy Signature Cleanup (`signatures.py`)

- Removed `JudgeEvaluation` signature class (redundant with `QualityAssessment`).
- Both signatures scored 0-10 and tracked `missing_elements`—consolidated into single quality path.

#### 4. DSPy Module Optimization (`reasoner.py`)

- Removed `self.judge = dspy.ChainOfThought(JudgeEvaluation)` module.
- Changed `self.router` from `dspy.ChainOfThought` → `dspy.Predict` for faster routing.
- Updated `predictors()` and `named_predictors()` to exclude judge module.

#### 5. Executor Deprecation (`executors.py`)

- Added deprecation warning to `JudgeRefineExecutor.__init__()`.
- Class retained for backwards compatibility with custom workflow configurations.

### Expected Outcome

- **Latency**: ~60-70% reduction in complex query execution time.
- **Cost**: Reduced token usage by eliminating judge LLM calls and reasoning traces in routing.
- **Simplicity**: Cleaner 5-phase pipeline easier to debug and maintain.

### Verification

- [x] Run `make test-config` to validate workflow configuration.
- [x] Run `make test` to ensure no regressions (35 tests passed).
- [x] Clear DSPy cache: `uv run python -m agentic_fleet.scripts.manage_cache --clear`
- [x] Re-test "Compare microservices vs monolithic" query to verify latency improvement.

### Results

| Phase     | Before     | After          |
| --------- | ---------- | -------------- |
| Analysis  | ~15s       | 10.7s          |
| Routing   | ~25s       | 20.0s          |
| Execution | ~180s      | 66.6s          |
| Progress  | ~15s       | 11.5s          |
| Quality   | ~20s       | 12.9s          |
| **Judge** | **~60s**   | **0.0003s** ✅ |
| **Total** | **~6 min** | **~2 min**     |

**Improvement**: ~66% reduction in latency (from ~360s to ~122s).

### Notes

- `dspy.Parallel` module was considered but is designed for concurrent DSPy module execution, not agent-framework `ChatAgent.run()` calls. The existing `asyncio.gather()` approach for parallel agent execution remains unchanged.
- Quality assessment via `QualityAssessment` signature is retained—only the redundant judge layer was removed.
