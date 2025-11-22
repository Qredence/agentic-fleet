# AgenticFleet Copilot Instructions

## Project Context

AgenticFleet is a hybrid runtime combining **DSPy** (analysis, routing, quality) and **Microsoft agent-framework** (orchestration, execution).

- **Core Flow:** Task → DSPy Analysis → DSPy Routing → Agent Execution → Quality Assessment → Refinement.
- **Config:** `config/workflow_config.yaml` controls models, agents, thresholds, and strategies.
- **Source of Truth:** `src/agentic_fleet/` is the main package.

## Key Architecture & Files

- **Orchestration:** `src/agentic_fleet/workflows/supervisor.py` drives the pipeline.
- **Reasoning:** `src/agentic_fleet/dspy_modules/reasoner.py` handles DSPy logic (Analysis, Routing, Quality).
- **Signatures:** `src/agentic_fleet/dspy_modules/signatures.py` defines DSPy input/output structures.
- **Agents:** `src/agentic_fleet/agents/` contains agent definitions.
- **Tools:** `src/agentic_fleet/tools/` and `src/agentic_fleet/utils/tool_registry.py`.
- **CLI:** `src/agentic_fleet/cli/console.py` is the entry point.

## Development Workflow

- **Build & Test:** Run `make check` (lint/types) and `make test` (pytest).
- **Run Workflow:** `uv run python -m agentic_fleet.cli.console run -m "Your task"`
- **Clear Cache:** `uv run python -m agentic_fleet.scripts.manage_cache --clear` (essential when changing signatures/config).
- **Environment:** `OPENAI_API_KEY` is required. `TAVILY_API_KEY` enables web search.

## Coding Conventions

- **Declarative Config:** Do not hardcode thresholds or prompts. Use `workflow_config.yaml` and `prompts/` modules.
- **DSPy Signatures:** Define inputs/outputs in `signatures.py`. Wrap with `dspy.ChainOfThought`.
- **Tooling:** Register tools in `ToolRegistry` before use. Do not instantiate tools directly in agents.
- **Error Handling:** Use `workflows/exceptions.py` for typed exceptions (`CompilationError`, `ToolError`).
- **Type Safety:** Use protocols in `utils/types.py`. Avoid `Any`.

## Common Tasks

- **Add Agent:** Create `agents/<name>.py`, add prompt, register in `workflow_config.yaml`, update `AGENTS.md`.
- **Add Tool:** Implement adapter in `tools/`, register in `ToolRegistry`, reference in YAML.
- **Optimize:** Adjust `gepa_max_metric_calls` in config for faster DSPy compilation.

## Common Gotchas

- **Path References:** Always use `src/agentic_fleet/...`.
- **Tool Lists:** YAML lists names; registry provides instances.
- **Missing Examples:** Weaker routing if `supervisor_examples.json` isn't updated.
- **Parallel Mode:** Auto-normalizes to delegated if only one agent is assigned.

## PR Checklist

1. YAML updated (no hardcoded thresholds).
2. Examples added/changed; cache cleared.
3. Tests updated (routing/quality/tool parsing).
4. Docs touched (`AGENTS.md` or this file).
5. Lint & types pass (`make check`).
