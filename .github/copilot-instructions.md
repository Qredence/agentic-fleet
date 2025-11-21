# AgenticFleet – Copilot Instructions

## Project Overview

AgenticFleet is a hybrid **DSPy + Microsoft agent-framework** runtime for self-optimizing multi-agent workflows.

- **Core Flow**: Task → DSPy Analysis → DSPy Routing → Agent Execution → Quality Assessment → Refinement.
- **Architecture**: `src/agentic_fleet/` is the source of truth.
- **Configuration**: Controlled by `config/workflow_config.yaml` (models, agents, thresholds).

## Key Components & File Structure

- **Orchestration**: `src/agentic_fleet/workflows/supervisor.py` (`SupervisorWorkflow`) drives the pipeline.
  - Strategies: `src/agentic_fleet/workflows/strategies.py` (Delegated, Sequential, Parallel).
  - Executors: `src/agentic_fleet/workflows/executors.py` (Analysis, Routing, Execution, Quality).
- **Reasoning**: `src/agentic_fleet/dspy_modules/reasoner.py` (`DSPyReasoner`) handles DSPy logic.
  - Signatures: `src/agentic_fleet/dspy_modules/signatures.py` (TaskAnalysis, Routing, Quality).
- **Agents**: `src/agentic_fleet/agents/` contains agent definitions and prompts.
- **Tools**: `src/agentic_fleet/tools/` and `src/agentic_fleet/utils/tool_registry.py`.
- **CLI**: `src/agentic_fleet/cli/console.py` (entry point for `agentic-fleet`).

## Development Workflow

- **Quality Gate**: Run `make check` (ruff, mypy) and `make test` (pytest) before committing.
- **CLI Usage**: Use `agentic-fleet` or `uv run python -m agentic_fleet.cli.console`.
  - Example: `agentic-fleet run -m "Research AI trends" --verbose`
- **DSPy Caching**: Compilation artifacts live in `logs/compiled_supervisor.pkl`.
  - Clear cache: `uv run python -m agentic_fleet.scripts.manage_cache --clear`
  - **Important**: Clear cache when changing DSPy signatures or `supervisor_examples.json`.

## Coding Conventions

- **Declarative Config**: Prefer modifying `config/workflow_config.yaml` over hardcoding values.
- **Agent Definition**:
  1. Create `agents/<name>.py`.
  2. Register in `workflow_config.yaml`.
  3. Add prompts in `agents/prompts.py`.
  4. Add training examples in `data/supervisor_examples.json`.
- **Tooling**: Register tools in `ToolRegistry` (`utils/tool_registry.py`) before referencing in YAML.
- **Error Handling**: Use exceptions from `src/agentic_fleet/workflows/exceptions.py` (e.g., `CompilationError`, `ToolError`).
- **Type Safety**: Use protocols from `src/agentic_fleet/utils/types.py`.

## Integration Points

- **Cosmos DB**: Set `AGENTICFLEET_USE_COSMOS=1` to mirror history/memory. See `src/agentic_fleet/utils/cosmos.py`.
- **Tracing**: OpenTelemetry hooks in `src/agentic_fleet/utils/tracing.py`.
- **Environment**: `OPENAI_API_KEY` is required. `TAVILY_API_KEY` for search.

## Common Patterns

- **DSPy Signatures**: Define inputs/outputs in `signatures.py`, wrap with `dspy.ChainOfThought` in `reasoner.py`.
- **Execution Modes**: Delegated (single), Sequential (chain), Parallel (fan-out).
- **Handoffs**: Managed by `HandoffManager` in `workflows/handoff.py`.

## Documentation

- **Agents**: `src/agentic_fleet/AGENTS.md`
- **Architecture**: `docs/developers/architecture.md`
