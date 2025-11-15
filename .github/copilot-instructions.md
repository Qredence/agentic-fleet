# DSPy-Enhanced Agent Framework - AI Coding Guide

## Architecture Overview

This project combines **Microsoft's agent-framework** with **DSPy's prompt optimization** to create self-improving multi-agent workflows. The key insight: DSPy modules optimize task routing and quality assessment, while agent-framework handles orchestration.

**Core Components:**

- `src/dspy_modules/supervisor.py` - DSPy supervisor with ChainOfThought wrappers; exposes analyze_task, route_task, evaluate_progress, assess_quality
- `src/workflows/supervisor_workflow.py` - Main workflow orchestrator combining both frameworks (delegated/sequential/parallel modes, streaming, history persistence)
- `config/workflow_config.yaml` - Centralized config for models, agents, and execution parameters
- `data/supervisor_examples.json` - Training examples for DSPy compilation
- `console.py` - Primary Typer CLI with run, analyze, benchmark, list_agents, export_history commands
- `src/cli/fleet.py` - TUI entry point (`dspy-fleet` command) with Rich-based UI
- `src/utils/compiler.py` - Compiles supervisor using BootstrapFewShot; defines routing_metric

**Data Flow:** Console input → SupervisorWorkflow.run/run_stream → DSPy analysis → DSPy routing → agent execution → DSPy quality assessment → optional refinement → append to logs/execution_history.json

**4-Phase Execution:** (1) DSPy Task Analysis → (2) DSPy Task Routing → (3) Agent Execution → (4) DSPy Quality Assessment (refine if score < 8/10)

## Critical Patterns

### 1. DSPy Signature Pattern

All DSPy modules use **Signatures** (not plain prompts). Signatures define input/output fields with descriptions:

```python
# AgenticFleet – AI Coding Instructions (Concise)

Purpose: Equip AI coding agents with just-in-time knowledge to be productive in this DSPy + Microsoft agent-framework hybrid. Keep changes declarative (YAML, examples) and lean on existing abstractions (SupervisorWorkflow, DSPySupervisor, ToolRegistry).

## Core Architecture
4 Phases (+ optional Judge loop): Analysis → Routing → Execution → Progress/Quality → (Refinement). Lazy DSPy compilation runs in the background (`logs/compiled_supervisor.pkl` + `.meta` with signature+config hashes) – never block user flows waiting for completion.

Key runtime files:
- `src/agentic_fleet/dspy_modules/supervisor.py` – DSPySupervisor (task/tool-aware analysis, routing, progress, quality, execution summary)
- `src/agentic_fleet/dspy_modules/signatures.py` – Signatures; follow field docstyle when adding
- `src/agentic_fleet/workflows/supervisor_workflow.py` – Orchestrates phases, judge refinement, streaming
- `src/agentic_fleet/config/workflow_config.yaml` – Models, thresholds, agents, GEPA, tracing, evaluation
- `src/agentic_fleet/utils/compiler.py` – Compilation + cache invalidation (signature/config hash)
- `src/agentic_fleet/utils/tool_registry.py` – Tool discovery + capability mapping (drives tool‑aware routing)
- `src/agentic_fleet/utils/cache.py` – TTLCache + hit‑rate stats (analysis caching via `analysis_cache_ttl_seconds`)

## Execution Modes & Handoffs
`ExecutionMode`: delegated (single), sequential (dependency chain, optional structured handoffs), parallel (independent subtasks). Handoffs enabled via `handoffs.enabled: true` using `handoff_manager` in sequential runs.

## Tool‑Aware DSPy
Agents created first; tools registered (single instance per tool) → supervisor sees registry before compilation. Signatures include `available_tools`; analysis may set `needs_web_search` & `search_query`; routing injects tool requirements from assigned agents.

## Judge & Refinement
Judge loop active if `quality.enable_judge: true`. Stops when `score >= judge_threshold` OR `refinement_needed == no` OR max rounds reached. Legacy refinement uses `quality.refinement_threshold` & progress action == "refine".

## Configuration Conventions
Edit `workflow_config.yaml` only (avoid hardcoding). Notable knobs: `dspy.optimization.use_gepa`, `gepa_max_metric_calls` (fast prompt evolution), `workflow.supervisor.analysis_cache_ttl_seconds` (0 disables cache), `quality.judge_threshold` (lower for faster exits), `agents.*.tools` (names resolved via registry).

## Adding / Extending
New agent: YAML block → `agents/<name>.py` → prompts module (if needed) → add examples (`src/agentic_fleet/data/supervisor_examples.json`) → tests (routing + quality) → docs (`AGENTS.md`).
New signature: add in `signatures.py` → wrap with `dspy.ChainOfThought` in `supervisor.py` → expose accessor method.

## Training Examples & Cache
Examples: `src/agentic_fleet/data/supervisor_examples.json` (fields: `task`, `team`, `assigned_to`, `mode`). After changes: `python src/agentic_fleet/manage_cache.py --clear` to force recompilation.

## Parsing & Safety
Parse string outputs (`assigned_to`, `subtasks`, quality scores like "8/10" → float). Validate routing (fallback if invalid; normalize parallel with 1 agent to delegated). Log edge cases (time‑sensitive without search, single‑agent parallel) for learning.

## Environment & Secrets
Required: `OPENAI_API_KEY`. Optional: `TAVILY_API_KEY`, `DSPY_COMPILE`, tracing vars (`OTEL_EXPORTER_OTLP_ENDPOINT`). Use `.env` locally; managed secret store in production.

## CLI / Dev Workflow
Entry points: `agentic-fleet`, alias `fleet`. Example: `agentic-fleet run -m "Research 2025 AI trends" --verbose`. Programmatic: `create_supervisor_workflow()`. Analytics: `scripts/analyze_history.py`, improvement: `scripts/self_improve.py`.

## Testing & Quality
`pytest` covers routing, tool parsing, judge refinement, cache behavior. Add minimal example when introducing a new signature. Stubs avoid external API calls.

## Performance & Optimization
Use smaller supervisor model (`gpt-5-mini`) for speed. Prefer `gepa_max_metric_calls` for ultra-fast GEPA. Lower `max_refinement_rounds` for latency. Monitor `phase_timings` & `phase_status` in workflow output.

## Common Gotchas
Wrong path references (use `src/agentic_fleet/...`). Tool list misuse (YAML lists names; registry provides instances). Missing examples → weaker routing (fallback still works). Judge loop stalls if threshold too high. Parallel mode with one agent auto-normalizes to delegated.

## PR Checklist
1. YAML updated (no hardcoded thresholds)
2. Examples added/changed; cache cleared
3. Tests updated (routing/quality/tool parsing)
4. Docs touched (`AGENTS.md` or this file)
5. Lint & types pass (`ruff`, `mypy`, `black`)

Feedback welcome—request clarification if any pattern seems incomplete or outdated.

```
