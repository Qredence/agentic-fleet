# Plans / Execution Tracker

This file tracks ongoing, in-flight work for the `agentic-fleet` repo (branch: `release-preprod-ready`).

## Active initiative: Option B — Deep alignment with `agent-framework`

### Goal

Make `agent-framework` the authoritative runtime for:

- streaming (consistent event semantics)
- HITL request/response (pause & resume)
- thread/multi-turn continuity
- (next) checkpointing & resumability

AgenticFleet should primarily own DSPy routing/quality + UI/event mapping, not re-implement orchestration.

### Target versions

- `agent-framework`: `>=1.0.0b251211`
- `agent-framework-declarative`: `>=1.0.0b251211`

### Status (last updated: 2025-12-13)

#### Completed ✅

- Dependency pins bumped to `1.0.0b251211`.
- HITL: request events are surfaced during streaming and mapped to UI events.
- HITL: WebSocket accepts workflow responses (e.g. `workflow.response`) and forwards them to the running workflow.
- Group chat: manager wiring updated to `GroupChatBuilder.set_manager(...)` with structured `ManagerSelectionResponse`.
- Multi-turn: `AgentThread` is now propagated through **non-streaming** delegated / parallel / sequential execution paths.
  - Compatibility preserved by only passing `thread=...` when non-`None`.
  - Fast-path is now automatically **disabled on follow-up turns** (when the thread has history) to avoid losing context.
- Typing: streaming strategy executors now declare explicit `AsyncIterator[...]` return types.
- Handoff mode: `HandoffBuilder` is constructed with keyword args (compatible with kw-only signature in `1.0.0b251211`).
  - Verified via `tests/workflows/test_builder.py`.
- Checkpoint plumbing (backend): `checkpoint_id` can be provided on the Supervisor workflow run APIs and on WebSocket chat requests.
  - Default storage: `FileCheckpointStorage` rooted at `.var/checkpoints` (fallback to in-memory if filesystem is unavailable).
  - Note: in `agent-framework`, `checkpoint_id` is **resume-only** (you must not pass it alongside a start `message`).
    For new runs, checkpointing is enabled via `checkpoint_storage`.
  - Verified via `tests/api/test_streaming.py` plus `ruff` import sorting checks.

- Frontend: HITL request/response + checkpoint id type alignment.
  - `ChatRequest.checkpoint_id` is typed for future resume flows.
    - `checkpoint_id` is **resume-only** in `agent-framework` (message XOR checkpoint_id).
    - Current WS new-run path ignores any provided `checkpoint_id` to avoid the XOR violation.
  - Can send `workflow.response` messages over WebSocket.
  - HITL request events render as a first-class `request` step with an inline responder.

- Checkpoint resume semantics (protocol + backend):
  - New WebSocket message: `{"type": "workflow.resume", "checkpoint_id": "..."}`.
  - `ChatRequest.enable_checkpointing` added to enable checkpoint persistence for **new runs**.
  - `checkpoint_id` is treated as **resume-only** at the protocol level; providing it alongside `message` is deprecated.
  - `SupervisorWorkflow.run_stream(task=None, checkpoint_id=...)` now performs a true resume (message omitted).
  - WebSocket handler routes new-run vs resume correctly and preserves agent-framework XOR semantics.

#### Next up 🔜 (in priority order)

1. **Checkpoint UX**: decide how checkpoint ids are generated (conversation/session) and expose “resume” controls.
   - Optional: expose checkpoint controls in CLI.
2. **HITL UX hardening**: improve response payload helpers for common request types (tool approval, plan review), error feedback when responses fail, and “resolved” UI state.
3. **Reduce shim reliance**: minimize direct imports from `agent_framework._*` where safe, and/or improve shim coverage so importing `_workflows` does not depend on importing `agentic_fleet` first.

### Risks / gotchas

- Some `agent-framework` builds appear to have incomplete root exports (e.g., `_workflows` importing root symbols).
  - Current workaround: `ensure_agent_framework_shims()` executed when importing `agentic_fleet`.
- `WorkflowRequestEvent` may be absent while `RequestInfoEvent` exists; code must be resilient to runtime API drift.

### How we verify

- Unit tests: `tests/test_workflow_strategies.py` must remain green.
- Full backend suite should remain green (`pytest` / `make test`).
- Manual smoke (CLI + WebSocket):
  - request event appears
  - responding unblocks workflow
  - multi-turn retains context across turns

## Work log

### 2025-12-13

- Implemented thread propagation for non-streaming strategies:
  - `src/agentic_fleet/workflows/strategies_delegated.py`
  - `src/agentic_fleet/workflows/strategies_parallel.py`
  - `src/agentic_fleet/workflows/strategies_sequential.py`
  - `src/agentic_fleet/workflows/strategies.py` (fallback delegated path)
- Added explicit return types for async streaming executor functions.
- Tests:
  - `tests/test_workflow_strategies.py`: 5 passed
  - `tests/workflows/test_builder.py`: 20 passed
  - `tests/api/test_streaming.py`: 27 passed

- Added checkpoint id plumbing:
  - `src/agentic_fleet/models/requests.py` (`ChatRequest.checkpoint_id`)
  - `src/agentic_fleet/services/chat_websocket.py` (enables checkpointing via `checkpoint_storage`; ignores `checkpoint_id` on new runs)
  - `src/agentic_fleet/workflows/supervisor.py` (forwards `checkpoint_id`/storage to agent-framework `Workflow.run_stream`)

- Fixed runtime crash: `ValueError: Cannot provide both 'message' and 'checkpoint_id'`.
  - Root cause: WS streaming path forwarded `checkpoint_id` alongside a task message.
  - Fix: never forward `checkpoint_id` in the WS new-run path; keep checkpointing opt-in via storage.
  - Added regression test: `tests/services/test_chat_websocket_checkpoint_semantics.py`.

- Frontend HITL + checkpoint type alignment:
  - `src/frontend/src/api/types.ts` (checkpoint_id + workflow.response typings)
  - `src/frontend/src/api/websocket.ts` (sendWorkflowResponse)
  - `src/frontend/src/stores/chatStore.ts` (request steps + sendWorkflowResponse action)
  - `src/frontend/src/components/blocks/full-chat-app.tsx` (inline request responder UI)

- Implemented explicit resume semantics + separated checkpoint enablement:
  - `src/agentic_fleet/models/requests.py` (`ChatRequest.enable_checkpointing`, `WorkflowResumeRequest`)
  - `src/agentic_fleet/workflows/supervisor.py` (streaming resume via `task=None` + `checkpoint_id`)
  - `src/agentic_fleet/services/chat_websocket.py` (handshake routes `workflow.resume`; XOR-safe forwarding)
  - `tests/services/test_chat_websocket_checkpoint_semantics.py` (resume-path regression)
  - `tests/api/test_streaming.py` (request model tests)
  - `src/frontend/src/api/types.ts`, `src/frontend/src/api/websocket.ts`, `src/frontend/src/stores/chatStore.ts` (typed client support)

- Fixed multi-turn context loss on short follow-ups:
  - Root cause: fast-path responder is stateless and ignores `AgentThread` history.
  - Fix: `SupervisorWorkflow._should_fast_path()` now disables fast-path when the current `conversation_thread` has history.
  - Regression tests: `tests/workflows/test_supervisor_fast_path_thread_history.py`.
