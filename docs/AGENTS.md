# AgenticFleet Agents Guide

This document explains how the multi-agent system in AgenticFleet is assembled, configured, and extended. It is intended for maintainers who need to understand where each agent lives in the codebase, what tools and configuration it depends on, and how the orchestration logic binds everything together.

## System Overview

- All agent factories live under `src/agenticfleet/agents/` with one subdirectory per agent (`orchestrator`, `researcher`, `coder`, `analyst`).
- Agents are instantiated through factory helpers that wrap Microsoft Agent Framework constructs (primarily `ChatAgent`) and share configuration via `src/agenticfleet/config/settings.py`.
- The runtime workflow is defined in `src/agenticfleet/fleet/magentic_fleet.py`; it uses the Magentic manager/executor stack to coordinate the orchestrator with the specialist agents.

| Agent        | Factory Helper                                   | Config File                                             | Key Tools / Capabilities                                                | Primary Role                                             |
|--------------|--------------------------------------------------|---------------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------|
| Orchestrator | `create_orchestrator_agent()`                     | `src/agenticfleet/agents/orchestrator/config.yaml`      | - (no tools)                                                             | Task triage, delegation, result synthesis                |
| Researcher   | `create_researcher_agent()`                       | `src/agenticfleet/agents/researcher/config.yaml`        | `web_search_tool` (structured web search responses)                      | Information gathering and citation prep                  |
| Coder        | `create_coder_agent()`                            | `src/agenticfleet/agents/coder/config.yaml`             | Hosted code interpreter runtime (auto-attached when `agent_framework` is installed) | Code generation guidance and review                      |
| Analyst      | `create_analyst_agent()`                          | `src/agenticfleet/agents/analyst/config.yaml`           | `data_analysis_tool`, `visualization_suggestion_tool` (structured output) | Data exploration, insight generation, visualization help |

## Orchestration Flow

- Use `agenticfleet.fleet.create_default_fleet()` to instantiate the Magentic
  orchestration pipeline configured via `fleet/fleet_builder.py`.
- `FleetBuilder` wraps `MagenticBuilder` to register participants and configure the
  `StandardMagenticManager`. The manager produces task ledgers (facts, plans,
  progress updates) that drive which specialist agent speaks next—no manual
  `DELEGATE` tokens are required.
- After each specialist agent responds, the manager evaluates progress and either
  schedules another agent, replans, or emits the final answer.
- Workflow-level safeguards (e.g., `max_rounds`, `max_stalls`, `max_resets`) are read from `src/agenticfleet/config/workflow.yaml`.

## Agents in Detail

### Orchestrator (`src/agenticfleet/agents/orchestrator/agent.py`)

- **Factory**: `create_orchestrator_agent()` builds a `ChatAgent` with instructions loaded from the agent’s YAML config and an `OpenAIResponsesClient` whose `model_id` defaults to the repository-wide `OPENAI_MODEL`.
- **Configuration**: `config.yaml` supplies the system prompt, default model (`gpt-5`), and metadata such as capabilities and delegation rules. The prompt emphasizes checklist-based planning, explicit delegation, and result synthesis.
- **Delegation Protocol**: The Magentic manager selects the next speaker based on the
  task ledger; the orchestrator focuses on planning and synthesis and should not emit
  manual `DELEGATE` tokens.
- **Tools**: The orchestrator does not bind any tools by default, but additional helper tools can be registered by adding imports and references in `create_orchestrator_agent()`.

### Researcher (`src/agenticfleet/agents/researcher/agent.py`)

- **Factory**: `create_researcher_agent()` configures a `ChatAgent` with the `web_search_tool` imported from `tools/web_search_tools.py`. Tools are enabled/disabled by toggling entries in the `tools` list inside the YAML config.
- **Tooling**: The tool returns a `WebSearchResponse` made up of `SearchResult` Pydantic models. Phase 1 uses deterministic mock data; upgrading to a real search API should preserve the schema.
- **Configuration**: `config.yaml` sets the default model (`gpt-5`), temperature (0.3), and research strategies. The `output_format` section enforces inline citations, which the orchestrator can rely on during synthesis.

### Coder (`src/agenticfleet/agents/coder/agent.py`)

- **Factory**: `create_coder_agent()` builds the base `ChatAgent` from YAML configuration. At runtime, `MagenticFleet._apply_coder_tooling()` swaps in a `HostedCodeInterpreterTool` whenever Microsoft Agent Framework packages are present; the agent falls back to manual drafting if that dependency is missing.
- **Tooling**: The hosted interpreter executes code in Microsoft’s sandbox, so guard long-running or unsafe operations in prompts and approval flows. When the fallback path is active, the coder agent should explicitly state that outputs are advisory only.
- **Configuration**: `config.yaml` targets `gpt-5` with a conservative temperature so generated snippets stay deterministic. Style guidance (line length, documentation style) still applies to keep output consistent.
- **Extensibility**: To augment tooling, extend `_apply_coder_tooling()` (or register additional tools in the factory) and cover the behaviour in `tests/test_code_types.py`/`tests/test_magentic_fleet.py`.

### Analyst (`src/agenticfleet/agents/analyst/agent.py`)

- **Factory**: `create_analyst_agent()` loads both `data_analysis_tool` and `visualization_suggestion_tool`, again governed by the YAML `tools` list.
- **Tooling**: Pydantic schemas (`DataAnalysisResponse`, `VisualizationSuggestion`) standardize outputs so downstream consumers can parse insights, confidence scores, and visualization recommendations reliably.
- **Configuration**: `config.yaml` lists supported analysis types, visualization defaults, and confidence thresholds. Adjust these to guide prompts or downstream interpretation.

## Settings, Environment, and Shared Config

- `src/agenticfleet/config/settings.py` loads environment variables at import time. Only `OPENAI_API_KEY` is strictly required; it raises `AgentConfigurationError` the first time `require_openai_api_key()` is called if the key is missing.
- Optional Azure settings (`AZURE_AI_PROJECT_ENDPOINT`, search endpoints/keys, deployed model names) are defined for future integration, but the current Mem0/OpenAI flow works without them.
- Logging is initialized through `agenticfleet.core.logging.setup_logging`, honoring `LOG_LEVEL` and `LOG_FILE`. Update `.env` to redirect logs during development.
- The shared workflow defaults (model, temperature, token limits) are declared in `config/workflow.yaml` and can be overridden agent by agent in the respective config files.

## Memory Integration

- `src/agenticfleet/context/mem0_provider.py` integrates with Mem0 to persist and retrieve long-term context. It now relies on the standard OpenAI API for both LLM calls and embeddings, with Mem0 managing the local vector store.
- Required environment variables for memory: `OPENAI_API_KEY` (plus optional `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, and `MEM0_HISTORY_DB_PATH`).
- The provider exposes `get()` and `add()` helpers. The orchestrator can query memory via injected context without managing additional cloud services.

## Testing and Validation

- `tests/test_config.py` validates required environment variables, workflow configuration integrity, agent YAML structure, tool imports, and factory callables. Run `uv run pytest tests/test_config.py -v` after modifying any agent-related configuration.
- Additional sanity checks reside in `tests/test_mem0_context_provider.py` and other files within the `tests/` directory. Extend these when introducing new tools or agent behaviors.

## Adding or Modifying Agents

1. **Scaffold**: Create a new subdirectory under `src/agenticfleet/agents/<new_agent>/` containing `__init__.py`, `agent.py`, `config.yaml`, and an optional `tools/` package.
2. **Factory Pattern**: Model `agent.py` after existing factories: load YAML via `settings.load_agent_config`, instantiate `OpenAIResponsesClient`, collect enabled tools, and return a configured `ChatAgent`.
3. **Register**: Export the new factory in `src/agenticfleet/agents/__init__.py` and wire the agent into `fleet/fleet_builder.py` (add `.with_agents(...)`, delegation predicates, and edges as needed).
4. **Prompt + Delegation**: Update the orchestrator prompt (or other agents) to emit delegation tokens that match your new predicate logic (e.g., `DELEGATE: planner`).
5. **Configuration + Tests**: Add YAML knobs for any new tool options, and extend `tests/test_config.py` to cover the new agent’s configuration and tool imports.

Keeping these conventions consistent ensures the multi-agent graph stays declarative, debuggable, and easy to extend.

## Related References

- [README](../README.md) – project overview, setup, and architecture diagram.
- [Repository Guidelines](operations/repository-guidelines.md) – coding standards and review checklist.
- [Progress Tracker](overview/progress-tracker.md) – roadmap and milestone history.
- [Mem0 Integration](operations/mem0-integration.md) – long-term memory configuration details referenced in this guide.
