# PLANS

## ExecPlan: Phase-1-Type-Safe-Cognitive-Layer

### Purpose
Establish the type-safe DSPy cognitive layer (Pydantic models, signatures, validators) and lay down the initial project skeleton for the v2.0 architecture.

### Scope
- Create the required directory tree and placeholder modules.
- Implement `config.py`, `dspy_modules/signatures.py`, and `dspy_modules/validation.py`.
- Provide minimal `pyproject.toml` and `README.md` scaffolding.

### Plan
1. Scaffold the `src/agentic_fleet/` directory tree and placeholder files.
2. Implement Pydantic models and DSPy signatures in `signatures.py`.
3. Add Pydantic validators in `validation.py` and team registry in `config.py`.
4. Sanity check imports/type hints and document next steps.

### Progress
- [x] Scaffolded tree and placeholder files.
- [x] Implemented Phase 1 code (config, signatures, validators).
- [x] Sanity check and notes recorded.

### Decisions
- Use Pydantic v2 `field_validator` and `ConfigDict` for strict models.
- Keep `TeamRegistry` as a simple dictionary with minimal metadata.

### Risks
- Agent Framework is pre-release; expect API churn and breaking changes.

### Validation
- `uv run python -m compileall src/agentic_fleet`

## ExecPlan: Phase-2-Structural-Skeleton

### Purpose
Implement the runtime infrastructure that bridges Agent Framework with DSPy (base agent + context modulator).

### Scope
- Implement `ContextModulator` using `contextvars`.
- Implement `BaseFleetAgent` and `FleetBrain` wrapper.
- Add `tests/verify_phase_2.py` smoke test.

### Plan
1. Add typed team context in `config.py`.
2. Implement context middleware.
3. Implement base agent and DSPy bridge.
4. Add Phase 2 verification script.

### Progress
- [x] Added typed team context in `config.py`.
- [x] Implemented `ContextModulator`.
- [x] Implemented `BaseFleetAgent` and DSPy bridge.
- [x] Added `tests/verify_phase_2.py`.

### Decisions
- Use `agent_framework.BaseAgent` + `AgentRunResponse` for compatibility with Agent Framework 1.0.0b251223.
- Preserve active context when no explicit team is provided.

### Risks
- Agent Framework pre-release APIs may change; keep base agent minimal.

### Validation
- `uv run python tests/verify_phase_2.py`

## ExecPlan: Phase-3-Nervous-System

### Purpose
Implement dynamic routing via a router agent, a conditional workflow graph, and a FastAPI entry point.

### Scope
- Implement `RouterAgent` to emit routing metadata.
- Build the conditional workflow in `workflows/modules.py`.
- Expose `/run` endpoint in FastAPI.
- Add `tests/verify_phase_3.py` smoke test.

### Plan
1. Implement router agent with routing metadata.
2. Build workflow graph with switch-case routing and council path.
3. Wire FastAPI entry point.
4. Add Phase 3 verification script.

### Progress
- [x] Implemented `RouterAgent` with routing metadata.
- [x] Implemented workflow graph with conditional routing.
- [x] Implemented FastAPI `/run` entry point.
- [x] Added `tests/verify_phase_3.py`.
- [x] Hardened BaseFleetAgent context harvesting for Judge inputs.
- [x] Added terminal executor to silence dead-end warnings.

### Decisions
- Store routing info in `AgentRunResponse.additional_properties` and router message `additional_properties`.
- Use `WorkflowBuilder.add_switch_case_edge_group` with route pattern helpers.

### Risks
- Agent Framework routing APIs may change (pre-release).

### Validation
- `uv run python tests/verify_phase_3.py`

## ExecPlan: Phase-5-GEPA-Optimization

### Purpose
Enable self-improvement by compiling DSPy Planner using approved traces.

### Scope
- Add GEPA trace collector and optimizer.
- Add `/train` endpoint to compile and reload planner.
- Add Phase 5 verification script.

### Plan
1. Implement `TraceCollector` and `FleetOptimizer`.
2. Wire `/train` to compile and reload the workflow.
3. Add `tests/verify_phase_5.py`.

### Progress
- [x] Implemented `TraceCollector` in `gepa/collector.py`.
- [x] Implemented `FleetOptimizer` in `gepa/optimizer.py`.
- [x] Added `/train` endpoint to compile and reload planner.
- [x] Added `tests/verify_phase_5.py`.

### Risks
- Training data extraction is heuristic until richer trace storage is wired in.

### Validation
- `uv run python tests/verify_phase_5.py`

## ExecPlan: Phase-6-Hardening-Alignment

### Purpose
Harden routing, training context, artifacts, and stubbed modules to reduce drift and cleanup technical debt.

### Scope
- Normalize routing labels between DSPy signatures and workflow routing logic.
- Preserve team context in GEPA training data and `/train` inputs.
- Relocate or ignore generated artifacts (optimized JSON, __pycache__).
- Implement or remove unused `brains.py` stub.

### Plan
1. **Routing normalization**
   - Decide canonical route labels (e.g., `direct|simple|complex`).
   - Add a normalization layer in `RouterAgent` and/or widen `RoutingDecision.pattern`.
   - Align workflow routing cases to canonical values.
2. **Training context integrity**
   - Extend `TraceCollector` to use actual team context/metadata when available.
   - Update `/train` to accept `team_id` or full `TaskContext` per example.
   - Ensure optimizer defaults remain sane when context is missing.
3. **Artifact hygiene**
   - Move optimized planner state to a runtime state directory (e.g., `.context/state` or `var/state`).
   - Add `.gitignore` entries for generated artifacts and `__pycache__`.
   - Update load path handling in `BaseFleetAgent` / workflow builder.
4. **Brains module**
   - Either implement `brains.py` (Planner/Worker/Judge DSPy modules) or remove it if unused.
5. **WebSocket endpoint**
   - Add `/ws` endpoint for running workflow over WebSocket.
   - Validate JSON payloads and return outputs/trace per message.
6. **Verification**
   - Update tests (Phase 3/5) to reflect routing normalization and context handling.
   - Run: `uv run python tests/verify_phase_3.py` and `uv run python tests/verify_phase_5.py`.

### Progress
- [x] Routing normalization.
- [x] Training context integrity.
- [x] Artifact hygiene.
- [x] Brains module decision.
- [x] WebSocket endpoint.
- [x] Verification.

## ExecPlan: Phase-7-DB-Async-WebSockets

### Purpose
Adopt SQLModel + asyncer + WebSocket best practices for persistence and realtime runs.

### Scope
- Introduce SQLModel models + engine setup.
- Use asyncer to offload sync DB operations from async endpoints.
- Harden WebSocket handling with `receive_json` and structured responses.

### Plan
1. Add `db.py` with SQLModel models and sync engine.
2. Initialize DB on startup via asyncer.
3. Persist run traces from `/run` and `/ws`.
4. Update `.gitignore` and docs for DB/state config.

### Progress
- [x] SQLModel `RunTrace` + engine in `db.py`.
- [x] Startup DB initialization using asyncer.
- [x] Persist run traces from `/run` and `/ws`.
- [x] WebSocket JSON handling best practices.
- [x] Docs/ignore updates.

## ExecPlan: Phase-8-LLM-Routing-Integration

### Purpose
Wire per-role LLM routing into the workflow so Router/Planner/Worker/Judge use the right model aliases via the LiteLLM proxy, while keeping tests deterministic.

### Scope
- Update workflow builders and agents to pass model roles/aliases consistently.
- Use shared LLM helpers in FastAPI startup and routing logic.
- Adjust tests to disable model routing and keep DummyLM usage.

## ExecPlan: Skill-Context-ID-Mapping

### Purpose
Align skill context storage (objects) with DSPy/GEPA expectations (IDs) and make skill metadata available in traces.

### Scope
- Store Skill objects in SkillContext while exposing ID lists for DSPy inputs.
- Ensure TraceCollector uses skill IDs from response metadata or repository lookups.
- Document the change and keep defaults safe.

### Plan
1. Add SkillContext helpers for available/mounted skill IDs and update context consumers.
2. Normalize TraceCollector skill extraction and fallback logic.
3. Update documentation in PLANS.md and note validation.

### Progress
- [x] Add SkillContext ID helpers and adjust context consumers.
- [x] Normalize TraceCollector skill extraction and fallback logic.
- [x] Document change and note validation.

### Validation
- Not run (logic-only change; no tests added yet).
- Document LLM routing env vars and defaults.

### Plan
1. **Agent/workflow wiring**
   - Route Router/Planner/Worker/Judge through the LLM routing helper.
   - Pass `model_role` per agent in `build_modules_workflow`.
2. **Runtime configuration**
   - Use `agentic_fleet.llm.get_lm` in FastAPI startup.
   - Ensure routing can be disabled with `FLEET_MODEL_ROUTING=0`.
3. **Verification + docs**
   - Update tests to disable model routing.
   - Document LLM routing env vars in `AGENTS.md`.

### Progress
- [x] Agent/workflow wiring.
- [x] Runtime configuration.
- [x] Verification + docs.

## ExecPlan: Phase-9-Direct-Provider-SDKs

### Purpose
Use provider SDKs directly for model execution: OpenAI SDK for DeepInfra-compatible models, google-genai for Gemini, and Anthropics SDK for GLM via ZAI base URL.

### Scope
- Replace LiteLLM proxy usage with direct SDK calls in `llm.py`.
- Load environment variables for provider credentials.
- Add required dependencies for Anthropic + Postgres driver.
- Update docs for new env vars.

### Plan
1. Implement provider-specific LM routing in `llm.py` with SDK calls.
2. Ensure startup loads env for LLM credentials.
3. Update docs and dependencies for new SDKs and DB driver.

### Progress
- [x] Provider SDK routing.
- [x] Env loading.
- [x] Docs + dependencies.
