# AgenticFleet Copilot Instructions

## System snapshot

- Hybrid runtime: DSPy handles analysis/routing/quality (`src/agentic_fleet/dspy_modules/`), Microsoft agent-framework executes plans (`src/agentic_fleet/workflows/`).
- Four phases always fire in order: Task → DSPy analysis → DSPy routing → Agent execution → Quality/Judge → optional refinement. See `workflows/supervisor.py`.
- Configuration is declarative; `config/workflow_config.yaml` defines models, agents, thresholds, tracing, and evaluation options.

## Key directories you’ll reference

- `src/agentic_fleet/agents/` (specialist definitions, prompts, `AgentFactory`).
- `src/agentic_fleet/tools/` + `utils/tool_registry.py` (tool adapters + registration rules).
- `src/agentic_fleet/workflows/` (builder, strategies, executors, handoffs, exceptions).
- `src/agentic_fleet/dspy_modules/` (signatures + reasoner logic). Training data lives in `src/agentic_fleet/data/supervisor_examples.json`.
- CLI entry: `src/agentic_fleet/cli/console.py`; backend FastAPI server under `src/agentic_fleet/api/`.

## Environment & configuration

- `OPENAI_API_KEY` is mandatory; copy `.env.example` → `.env` and fill it plus optional `TAVILY_API_KEY`, `DSPY_COMPILE`, tracing, Cosmos, etc.
- Keep knobs in YAML—never hardcode thresholds, prompts, or tool lists inside Python. Update `workflow_config.yaml` and align docs in `AGENTS.md` when behavior changes.
- DSPy caches compilation to `logs/compiled_supervisor.pkl`; clear via `uv run python -m agentic_fleet.scripts.manage_cache --clear` whenever signatures, prompts, or examples change.

## Everyday workflows

- Install/sync with `uv sync` (`make install` or `make dev-setup` to cover frontend + hooks).
- Run backend workflows via `uv run python -m agentic_fleet.cli.console run -m "..."`; use `make dev` for backend+frontend stack or `make backend` / `make frontend-dev` individually.
- Quality gates: `make check` (ruff + ty) and `make test` (pytest). Frontend checks live under `src/frontend` (`npm test`, `npm run lint`).
- History & analytics scripts live in `scripts/` (e.g., `analyze_history.py`, `self_improve.py`, `benchmark_api.py`).

## Extending agents & tools

- Adding an agent: new module under `agents/`, wire prompts in `agents/prompts.py`, register in YAML `agents:` block, update training examples + `docs/AGENTS.md`, and add unit tests (routing + execution).
- Adding a tool: implement adapter in `tools/`, expose via `ToolRegistry`, list it by name in YAML, and document latency/cost expectations.
- DSPy signatures (`dspy_modules/signatures.py`) must describe any new inputs/outputs; wrap models in `dspy.ChainOfThought` and keep reasoning hints short.

## DSPy optimization & datasets

- Training examples: edit `src/agentic_fleet/data/supervisor_examples.json` and recompile DSPy. Keep examples in sync with agent roster and execution modes.
- GEPA/BootstrapFewShot knobs live under `dspy.optimization` in YAML; tune `gepa_max_metric_calls` or disable with `DSPY_COMPILE=false` for rapid iteration.
- Execution history + compiled modules live under `logs/`; never hand-edit `compiled_supervisor.pkl`, always regenerate via the cache script.

## Quality, testing, and debugging

- `make test-config` validates YAML/agent wiring; `make validate-agents` ensures docs describe the current roster.
- Use typed exceptions from `workflows/exceptions.py` (e.g., `CompilationError`, `ToolError`) and protocols in `utils/types.py`; avoid ad-hoc exceptions or `Any` typing.
- When routing degrades, inspect `logs/execution_history.jsonl`, refresh examples, and rerun compilation. Weak judge scores often mean `quality.max_refinement_rounds` or `judge_threshold` needs tuning in YAML.

## Pitfalls & reminders

- Paths are relative to `src/agentic_fleet/...`; avoid importing from root-level modules directly.
- Tool names in YAML must match registry keys; mismatches lead to runtime warnings.
- Parallel mode auto-normalizes to delegated if only one agent survives routing—double-check DSPy output before forcing execution strategies.
- Always touch docs (`AGENTS.md`, `docs/guides/quick-reference.md`, or this file) when agent rosters, tools, or workflows change.

## Optional persistence (Cosmos)

- Enable with `AGENTICFLEET_USE_COSMOS=1`; provide `AZURE_COSMOS_ENDPOINT` plus credential (key or managed identity). Containers default to `workflowRuns`, `agentMemory`, `dspyExamples`, `dspyOptimizationRuns`, `cache` with partition keys `/workflowId` or `/userId`—keep payloads <2 MB and ensure high-cardinality IDs.
- Cosmos writes are best-effort; failures shouldn’t block workflows but should log warnings. Consult `docs/developers/cosmosdb_data_model.md` before schema changes.
