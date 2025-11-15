# AgenticFleet – AI Coding Instructions (Concise)

Purpose: Equip AI coding agents with just-in-time knowledge for this DSPy + Microsoft agent-framework hybrid. Keep changes declarative (YAML, examples). Leverage existing abstractions: SupervisorWorkflow, DSPySupervisor, ToolRegistry.

## Core Flow

Phases: 1) Analysis → 2) Routing → 3) Execution → 4) Progress/Quality → (optional refinement). Background lazy DSPy compilation: `logs/compiled_supervisor.pkl` + `.meta` (signature + config hashes).

## Key Files

- `src/agentic_fleet/dspy_modules/supervisor.py` (analysis, routing, progress, quality, execution summary)
- `src/agentic_fleet/dspy_modules/signatures.py` (add new signatures here; docstyle fields)
- `src/agentic_fleet/workflows/supervisor_workflow.py` (phase orchestration, judge loop, streaming)
- `src/agentic_fleet/config/workflow_config.yaml` (models, thresholds, agents, GEPA, tracing, evaluation)
- `src/agentic_fleet/utils/compiler.py` (compilation + cache invalidation)
- `src/agentic_fleet/utils/tool_registry.py` (tool capability mapping for routing)
- `src/agentic_fleet/utils/cache.py` (TTL analysis cache + stats)

## Modes & Handoffs

ExecutionMode: delegated | sequential | parallel. Sequential can enable structured handoffs (`handoffs.enabled: true`). Parallel with 1 agent auto-normalizes.

## Tool-Aware Routing

Agents + tools instantiated first; registry available to supervisor before compilation. Signatures expose `available_tools`; analysis may set `needs_web_search` & `search_query`; routing injects tool needs automatically.

## Judge & Refinement

Active if `quality.enable_judge: true`. Stop when `score >= quality.judge_threshold`, refinement not needed, or max rounds reached. Legacy refinement path uses `quality.refinement_threshold` when progress action == "refine".

## Configuration (edit ONLY YAML)

Important knobs: `dspy.optimization.use_gepa`, `gepa_max_metric_calls`, `workflow.supervisor.analysis_cache_ttl_seconds` (0 disables), `quality.judge_threshold`, `max_refinement_rounds`, agent tool lists (`agents.*.tools`). Never hardcode thresholds.

## Extend System

New agent: add YAML block → `agents/<name>.py` → optional prompts module → update `supervisor_examples.json` → tests (routing & quality) → docs. New signature: add in `signatures.py`, wrap with `dspy.ChainOfThought` in supervisor, expose accessor.

## Training Examples & Cache

Examples file: `src/agentic_fleet/data/supervisor_examples.json` (fields: task, team, assigned_to, mode). After changes run: `python src/agentic_fleet/manage_cache.py --clear`.

## Parsing & Safety

Normalize scores like "8/10" → float. Validate routing (fallback if invalid). Log edge cases (single-agent parallel, missing search when time-sensitive). Convert comma lists (`assigned_to`).

## Environment & Secrets

Required: OPENAI_API_KEY. Optional: TAVILY_API_KEY (web search), DSPY_COMPILE (force compile), OTEL_EXPORTER_OTLP_ENDPOINT (tracing). Use `.env` locally; secure store in prod.

## Dev Workflow

CLI: `agentic-fleet run -m "Task" --verbose`. TUI: `agentic-fleet`. Programmatic: `create_supervisor_workflow()`. Analytics: `scripts/analyze_history.py`. Self-improve: `scripts/self_improve.py`.

## Testing & Quality

`pytest` covers routing, tool parsing, judge/refinement, cache behavior. Add minimal example for each new signature. Mock external calls.

## Performance Tips

Use lighter supervisor model (`gpt-5-mini`). Lower `max_refinement_rounds` for latency. Tune `gepa_max_metric_calls`. Monitor returned `phase_timings` and `phase_status`.

## Common Gotchas

Wrong path (`src/agentic_fleet/...`). YAML tool names vs runtime instances. Sparse examples → weaker routing (fallback still works). Judge threshold too high → slow exit.

## PR Checklist

1. YAML updated (no hardcoded thresholds)
2. Examples adjusted & cache cleared if needed
3. Tests added/updated (routing, quality, tool parsing)
4. Docs updated (`AGENTS.md` or this file)
5. Lint & types pass (`ruff`, `mypy`, `black`)

Feedback welcome—request clarification if any pattern seems outdated.
