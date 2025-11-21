# AgenticFleet Agents Documentation

## Overview

AgenticFleet ships a roster of specialized agents built atop Microsoft's agent-framework. Each agent focuses on a distinct stage of problem solving (research, analysis, composition, evaluation, iteration). The DSPy reasoner chooses which subset to engage and how (delegated, sequential, parallel, or handoff chains).

---

## Core Agents

### 🔍 Researcher

Purpose: High‑quality information gathering & source discovery.
Reasoning Strategy: **ReAct** (Autonomous multi-step research loops).
Tools: `TavilyMCPTool`, `BrowserTool` (optional).
Strengths: Current events, citation generation, multi‑source synthesis.
Sample Tasks:

```text
"Who won the 2024 US presidential election?"
"Research latest transformer architecture improvements"
"Find pricing changes for Azure AI in Q3 2025"
```

Config (excerpt from `workflow_config.yaml`):

```yaml
agents:
  researcher:
    model: gpt-5-mini
    tools: [TavilySearchTool]
```

### 📊 Analyst

Purpose: Structured data, computation, code execution.
Reasoning Strategy: **Program of Thought** (Code-based logic & calculation).
Tools: `HostedCodeInterpreterTool`.
Strengths: Statistical analysis, simulations, chart generation, validation of research claims.
Sample Tasks:

```text
"Compute year‑over‑year growth from this CSV"
"Run a Monte Carlo simulation for risk assessment"
"Generate a bar chart of quarterly revenue"
```

Config:

```yaml
analyst:
  model: gpt-5-mini
  tools: [HostedCodeInterpreterTool]
```

### ✍️ Writer

Purpose: Narrative synthesis & formatted output.
Tools: None (language model only).
Strengths: Reports, documentation, blog posts, structured summaries.
Sample Tasks:

```text
"Draft an executive summary of research findings"
"Write a blog post on sustainable AI practices"
"Produce a README section describing evaluation pipeline"
```

Config:

```yaml
writer:
  model: gpt-5-mini
```

### 👀 Reviewer

Purpose: Quality gate, consistency & polish.
Tools: None.
Strengths: Style alignment, minor corrections, coherence checks.
Sample Tasks:

```text
"Review the draft report for clarity and tone"
"Check if instructions section covers all steps"
```

Config:

```yaml
reviewer:
  model: gpt-5-mini
```

### ⚖️ Judge

Purpose: Structured evaluation & scoring with dynamic criteria.
Tools: Internal reasoning (may leverage model reasoning effort flags).
Strengths: Criteria generation, gap detection, refinement directives.
Quality Threshold: Configurable (e.g. `judge_threshold: 7.0`).
Sample Evaluation Dimensions: correctness, completeness, clarity, citation quality (when applicable).

---

## Advanced Reasoning Strategies

AgenticFleet enhances agent capabilities by plugging specialized DSPy reasoning modules into the execution loop. This allows agents to go beyond simple chain-of-thought and employ more robust cognitive strategies:

### 🧠 ReAct (Reason + Act)

**Used by:** Researcher
**Description:** Enables the agent to perform autonomous loops of **Thought → Action → Observation**. The agent can issue multiple tool calls (e.g., search queries, browser navigation) in sequence, refining its understanding based on each result before formulating a final answer. This is critical for deep research where the initial query might not yield a direct answer.

### 🧮 Program of Thought (PoT)

**Used by:** Analyst
**Description:** Instead of hallucinating calculations, the agent generates and executes **Python code** to solve the problem. This ensures mathematical precision and allows for complex data manipulation. The agent formulates the logic in code, runs it via a local executor, and uses the output to derive the final response.

**Resilience:** If the generated code fails to execute (e.g., syntax error or runtime exception), the agent automatically falls back to the standard **ChatAgent** behavior. A short notice explaining the fallback reason is prepended to the response, ensuring the user still receives a helpful answer (albeit without the guarantee of code execution).

---

## Handoff Specialists

These roles participate in explicit multi‑stage production flows:

| Agent     | Role                                          | Highlights                                         |
| --------- | --------------------------------------------- | -------------------------------------------------- |
| Planner   | Decompose task into ordered steps             | High reasoning effort; produces structured plan    |
| Executor  | Coordinate plan execution & progress tracking | Detects stalls; escalates blockers                 |
| Coder     | Implement technical changes / prototypes      | Low temperature; code interpreter access           |
| Verifier  | Validate artifacts & test improvements        | Regression detection & acceptance criteria checks  |
| Generator | Final user‑facing assembly                    | Integrates verified outputs into polished response |

Additions require updates to: `workflow_config.yaml`, `agents/*.py`, prompt modules, training examples, and tests.

---

## Execution Patterns

| Pattern       | Flow                                   | Example                                                        |
| ------------- | -------------------------------------- | -------------------------------------------------------------- |
| Delegated     | Single agent                           | "Summarize latest AI conference keynote" → Researcher          |
| Sequential    | Linear chain                           | Researcher → Analyst → Writer → Reviewer                       |
| Parallel      | Concurrent specialists then synthesize | Researcher(AWS) + Researcher(Azure) + Researcher(GCP) → Writer |
| Handoff Chain | Explicit staged roles                  | Planner → Coder → Verifier → Generator                         |

Reasoner selects pattern based on task analysis + historical examples.

Routing defaults (2025-11): when the router assigns multiple agents but leaves mode as delegated, the workflow auto-normalizes to parallel fan-out with aligned subtasks to cut latency. Time-sensitive tasks (keywords like "latest/current/today" or years >=2023) force `tavily_search` and ensure Researcher is included if the key is available.

---

## Selection Guidelines

| Need                                    | Choose     | Rationale                        |
| --------------------------------------- | ---------- | -------------------------------- |
| Current factual info                    | Researcher | Web search + citation tooling    |
| Computation / data transform            | Analyst    | Sandboxed code execution         |
| Narrative / documentation               | Writer     | Higher creativity temperature    |
| Final polish / consistency              | Reviewer   | Style & coherence adjustment     |
| Formal scoring / improvement directives | Judge      | Structured criteria & thresholds |

Combine agents when tasks span multiple domains (e.g. research + quantitative analysis + reporting).

---

## Tooling Matrix

| Tool                      | Provided By           | Purpose                 | Notes                                                |
| ------------------------- | --------------------- | ----------------------- | ---------------------------------------------------- |
| TavilyMCPTool             | Researcher            | Web search w/ citations | Requires `TAVILY_API_KEY`; medium latency            |
| BrowserTool               | Researcher (optional) | Direct page interaction | Install Playwright; respect robots.txt; high latency |
| HostedCodeInterpreterTool | Analyst, Coder        | Compute & visualize     | Sandboxed; no external network; high latency/cost    |

- OpenAI-hosted web search is intentionally disabled here; Tavily MCP is the default and must be used for any time-sensitive or current-event queries when the key is present.

- Tavily remains an optional dependency: the `tavily-python` package is only required when the key is set and the tool is instantiated. The CLI/API will boot without it, but web search is unavailable until installed and configured.
- DSPy now requires a real model ID (e.g., `gpt-5-mini`); the former `test-model` dummy path has been removed to avoid silent mock outputs.

Extending tooling: implement agent-framework `ToolProtocol`, register in `ToolRegistry`, reference in YAML. The `ToolRegistry` now provides concise tool descriptions with latency hints and TTL-caches common results.

### Long-Term Memory & Cosmos Mirror

- Set `AGENTICFLEET_USE_COSMOS=1` to mirror workflow history, agent memories, DSPy datasets, and cache metadata into Azure Cosmos DB. The helper (`utils/cosmos.py`) reuses a single client, supports managed identity, and never blocks the critical path when Cosmos is unavailable.
- `agentMemory` uses `/userId` as its partition key. Keep IDs high-cardinality (tenant, workspace, or developer handle) to avoid hot partitions, and keep each memory item well under Cosmos’s 2 MB limit by summarizing older turns.
- Container defaults align with the documented schema (`workflowRuns`, `agentMemory`, `dspyExamples`, `dspyOptimizationRuns`, `cache`). Override via `AZURE_COSMOS_*_CONTAINER` vars if your account already uses different IDs.
- Full requirements + data model live in `cosmosdb_requirements.md` and `cosmosdb_data_model.md`; provision the database ahead of time since AgenticFleet never creates containers automatically.

---

## Code Quality & Architecture

### Enhanced Error Handling

- Comprehensive exception hierarchy in `workflows/exceptions.py` with context-aware error reporting
- Specific exceptions: `CompilationError`, `CacheError`, `ValidationError`, `TimeoutError`, `ToolError`
- Structured error context for better debugging and monitoring

### Type Safety

- Protocol definitions in `utils/types.py` for DSPy, agent-framework, and internal interfaces
- Type aliases and runtime-checkable protocols to improve IDE support
- Better type hints throughout the codebase

### Caching & Performance

- Enhanced `TTLCache` with hit rate tracking (`CacheStats`) in `utils/cache.py`
- Incremental cleanup of expired entries for better memory management
- Async compilation support in `utils/async_compiler.py` for non-blocking initialization
- Constants centralized in `utils/constants.py` for maintainability

### Code Organization

- CLI module structure: `cli/runner.py` (WorkflowRunner), `cli/display.py` (display utilities)
- Improved separation of concerns and modularity

At a high level, the runtime is layered as follows:

- Workflows (`src/agentic_fleet/workflows/*`) orchestrate execution using agent-framework `WorkflowBuilder` and executors.
- DSPy modules (`src/agentic_fleet/dspy_modules/*`) analyze tasks, choose agents/modes, and assess quality; they do not run inside workflow executors.
- Agents and tools (`src/agentic_fleet/agents/*`, `src/agentic_fleet/tools/*`) wrap `ChatAgent` instances and tool implementations that workflows call as opaque executors.
- The CLI wires everything together: DSPy → workflow assembly → execution → optional DSPy judge/refinement.

See `docs/developers/code-quality.md` for detailed documentation.

---

## Adding a New Agent (Checklist)

1. Create `agents/new_role.py` with `get_config()`.
2. Add prompt instructions in `agents/prompts.py`.
3. Register in `workflow_config.yaml` under `agents:`.
4. Update training examples (include tasks requiring new role).
5. Extend tests (routing + execution + quality) under `tests/`.
6. Document in `AGENTS.md` & link where relevant.
7. (Optional) Provide evaluation tasks exercising new role.

---

## Performance Tuning

- Use lighter model (gpt-5-mini) for reasoner to reduce latency.
- Limit `max_bootstrapped_demos` during prototyping; increase for production stability.
- Cache compilation; clear when signatures or examples change.
- Stream outputs (`enable_streaming: true`) for improved UX on long tasks.
- Use async compilation (`utils/async_compiler.py`) for non-blocking workflow initialization.
- Monitor cache hit rates via `CacheStats` to optimize TTL settings.
- Leverage incremental cache cleanup to reduce memory usage in long-running processes.
- Prefer minimal judge reasoning effort and 1 refinement round; set `judge_timeout_seconds`.
- Use `gepa_max_metric_calls` and small `max_bootstrapped_demos` for faster DSPy optimization.

---

## Troubleshooting Quick Hits

| Issue             | Likely Cause                   | Mitigation                                  |
| ----------------- | ------------------------------ | ------------------------------------------- |
| Weak routing      | Sparse or low-quality examples | Expand `supervisor_examples.json`           |
| Slow refinement   | High reasoning effort on Judge | Try `reasoning_effort: minimal`             |
| Missing citations | Tavily key absent              | Set `TAVILY_API_KEY` in `.env`              |
| Tool not found    | Registry mismatch              | Confirm name & import in `ToolRegistry`     |
| Stalled chain     | Overly long agent roster       | Reduce agents or enable progress heuristics |

See `docs/users/troubleshooting.md` for deeper coverage.

---

## Reference Links

- Architecture: `docs/developers/architecture.md`
- Quick Reference: `docs/guides/quick-reference.md`
- DSPy Optimization: `docs/guides/dspy-optimizer.md`
- Evaluation: `docs/guides/evaluation.md`
- Configuration: `docs/users/configuration.md`

---

This document complements the runtime layout guide at `src/agentic_fleet/AGENTS.md` (internal developer focus). This root file targets users selecting and combining agents effectively.
