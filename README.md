![AgenticFleet Architecture](assets/banner.png)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/agentic-fleet)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/qredence/agentic-fleet)

> **⚠️ Active Development Notice**
> APIs, signatures, and execution semantics can change between minor versions. Pin a version tag for production usage.

---

# AgenticFleet – DSPy‑Enhanced Multi‑Agent Orchestration

AgenticFleet is a hybrid **DSPy + Microsoft agent-framework** runtime that delivers a self‑optimizing fleet of specialized AI agents. DSPy handles task analysis, routing, progress & quality assessment; agent-framework provides robust orchestration primitives, event streaming, and tool execution. Together they enable delegated, sequential, parallel, and handoff‑driven workflows with iterative refinement loops.

---

## Table of Contents

- [AgenticFleet – DSPy‑Enhanced Multi‑Agent Orchestration](#agenticfleet--dspyenhanced-multiagent-orchestration)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Architecture Overview](#architecture-overview)
    - [Workflow Diagram](#workflow-diagram)
    - [Latency \& Slow Phases](#latency--slow-phases)
  - [Directory Layout](#directory-layout)
  - [Installation](#installation)
    - [Python (uv recommended)](#python-uv-recommended)
    - [Standard pip](#standard-pip)
    - [Optional Frontend](#optional-frontend)
    - [Playwright (Browser Tool)](#playwright-browser-tool)
  - [Configuration \& Environment](#configuration--environment)
  - [Quick Start](#quick-start)
    - [TUI / CLI](#tui--cli)
    - [Python API](#python-api)
    - [Streaming](#streaming)
  - [Execution Modes](#execution-modes)
  - [Agents](#agents)
  - [DSPy Optimization](#dspy-optimization)
  - [Observability \& History](#observability--history)
  - [Evaluation \& Self-Improvement](#evaluation--self-improvement)
  - [Testing \& Quality](#testing--quality)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)
  - [Related Documentation](#related-documentation)

---

## Key Features

- **Adaptive Routing** – DSPy supervisor analyzes tasks and decides agent roster + execution mode (delegated / sequential / parallel).
- **Quality Loops** – Automatic Judge / Reviewer refinement when quality score drops below configurable threshold.
- **Tool‑Aware Decisions** – Signatures include tool context; Supervisor recommends tool usage (code interpreter, search, browser, etc.).
- **Streaming Events** – Emits OpenAI Responses‑compatible events for real‑time TUI / web UI updates.
- **Self‑Improvement** – GEPA + BootstrapFewShot compilation refines routing from curated examples & execution history.
- **YAML‑Driven** – Central `workflow_config.yaml` governs models, thresholds, agents, tracing, evaluation toggles.
- **Rich Ergonomics** – Typer CLI (`cli/console.py`), `dspy-fleet` command, optional Vite frontend, history analytics scripts.
- **Safe Fallbacks** – Graceful degradation when DSPy unavailable (heuristic routing & quality scoring).
- **Extensible Toolkit** – Add agents, tools, signatures, evaluation metrics with minimal boilerplate.

---

## Architecture Overview

Four‑phase pipeline:

```
Task → [1] DSPy Analysis → [2] DSPy Routing → [3] Agent Execution → [4] Quality / Judge Assessment → (Optional Refinement)
```

| Phase     | Responsibility                            | Source                                                  |
| --------- | ----------------------------------------- | ------------------------------------------------------- |
| Analysis  | Extract goals, complexity, constraints    | `dspy_modules/supervisor.py` (`analyze_task`)           |
| Routing   | Pick agents + execution mode, tools       | `dspy_modules/supervisor.py` (`route_task`)             |
| Execution | Orchestrate agents & tools; stream events | `workflows/supervisor_workflow.py`                      |
| Quality   | Score output, recommend improvements      | `dspy_modules/supervisor.py` (`assess_quality` + Judge) |

### Workflow Diagram

```mermaid
graph TD
A[Task input] --> B[DSPy analysis]
B --> C[DSPy routing]
C --> D1[Agent execution delegated]
C --> D2[Agent execution sequential]
C --> D3[Agent execution parallel]
D1 --> E[Quality assessment]
D2 --> E
D3 --> E
E --> F[Final output]
E --> G[Refinement loop]
G --> F
```

Refinement triggers when score < threshold (default 8 or judge threshold ≥ 7). Handoffs coordinate multi‑agent chains via `HandoffManager`.

Consult: `docs/developers/architecture.md` & `docs/guides/quick-reference.md`.

### Latency & Slow Phases

Common bottlenecks and how to mitigate:

- DSPy compilation on first run
  - Use cached compiled supervisor after first run; clear via `uv run python -m agentic_fleet.scripts.manage_cache --clear`
  - Reduce GEPA effort in `config/workflow_config.yaml` (e.g., `gepa_max_metric_calls`, `max_bootstrapped_demos`)
  - Set `DSPY_COMPILE=false` during rapid iteration
- External tool calls (OpenAI, Tavily, Hosted Interpreter)
  - Prefer lighter Supervisor model `dspy.model: gpt-5-mini`
  - Disable pre‑analysis tool usage for simple tasks
- Judge/refinement loops
  - Set `quality.max_refinement_rounds: 1`
  - Use `judge_reasoning_effort: minimal`
- Parallel fan‑out synthesis
  - Cap `execution.max_parallel_agents` to a small number
  - Enable streaming to surface progress early
- History and tracing I/O
  - Reduce verbosity in production; batch writes if needed

For timing analysis, run history analytics: `uv run python src/agentic_fleet/scripts/analyze_history.py --timing`.

---

## Directory Layout

| Path                               | Purpose                                                    |
| ---------------------------------- | ---------------------------------------------------------- |
| `config/workflow_config.yaml`      | Models, agents, thresholds, tracing, evaluation flags      |
| `src/agentic_fleet/dspy_modules/`  | DSPy Signatures & Supervisor implementation                |
| `src/agentic_fleet/workflows/`     | `SupervisorWorkflow`, handoff & exceptions                 |
| `src/agentic_fleet/agents/`        | Specialist configurations & factory                        |
| `src/agentic_fleet/tools/`         | Tool adapters: Tavily, Browser, Hosted Interpreter, MCP    |
| `src/agentic_fleet/utils/`         | Compiler cache, GEPA optimizer, history, tracing, registry |
| `src/agentic_fleet/evaluation/`    | Metrics & evaluator engine                                 |
| `src/agentic_fleet/cli/console.py` | Rich / Typer CLI (dspy-fleet)                              |
| `examples/`                        | Minimal workflow samples                                   |
| `scripts/`                         | Analysis, self-improvement, dataset generation             |
| `logs/`                            | Execution history, compilation artifacts                   |
| `frontend/`                        | Optional Vite + React streaming UI                         |

---

## Installation

### Python (uv recommended)

```bash
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# Create and sync a local environment from pyproject.toml
uv sync
```

### Standard pip

```bash
# From PyPI (library / CLI usage)
pip install agentic-fleet

# From a local clone (editable install)
pip install -e .
```

### Optional Frontend

```bash
make frontend-install          # installs Node dependencies
make dev                       # runs backend + frontend dev servers
```

### Playwright (Browser Tool)

```bash
playwright install chromium
```

---

## Configuration & Environment

Create `.env` (or copy `.env.example`):

```bash
OPENAI_API_KEY=sk-...          # Required for all model calls (validated at startup)
TAVILY_API_KEY=tvly-...        # Optional: Enables web search for Researcher agent
DSPY_COMPILE=true              # Toggle DSPy compilation (true/false)
OPENAI_BASE_URL=https://...    # Optional custom endpoint
LANGFUSE_PUBLIC_KEY=...        # Optional observability
LANGFUSE_SECRET_KEY=...
```

**Note**: The `OPENAI_API_KEY` environment variable is required and will be validated at startup. If missing, the application will fail with a clear error message.

Key YAML knobs (`workflow_config.yaml`):

- `dspy.model` – Supervisor model (e.g. gpt-5-mini)
- `dspy.optimization.metric_threshold` – Minimum routing accuracy
- `workflow.supervisor.max_rounds` – Conversation turn limit
- `workflow.supervisor.enable_streaming` – Event streaming toggle
- `agents.*` – Per-agent model + temperature + tools
- `evaluation.*` – Batch evaluation settings

**Configuration Validation**: The YAML configuration is automatically validated against a schema when loaded. Invalid values (e.g., out-of-range temperatures, invalid model names) will raise `ConfigurationError` with clear messages indicating which field failed validation.

---

## Quick Start

### TUI / CLI

```bash
agentic-fleet                       # Launch interactive console (packaged entry point)

# Process a single task with streaming
agentic-fleet run -m "Research 2024 AI funding trends" --verbose

# List available agents and their tools
agentic-fleet list-agents

# Run batch evaluation (uses config dataset by default)
agentic-fleet evaluate --max-tasks 5

# Module-style invocation (alternative)
python -m agentic_fleet.cli.console --help
```

### Python API

```python
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def main():
		workflow = await create_supervisor_workflow(compile_dspy=True)
		result = await workflow.run("Summarize transformer architecture evolution")
		print(result["result"])  # final output
		print(result["quality"]) # quality assessment details

asyncio.run(main())
```

### Streaming

```python
async for event in workflow.run_stream("Compare AWS vs Azure AI offerings"):
		# Handle MagenticAgentMessageEvent / WorkflowOutputEvent
		print(event)
```

---

## Execution Modes

| Mode           | Description                                        | Use Case                            |
| -------------- | -------------------------------------------------- | ----------------------------------- |
| Delegated      | Single agent manages entire task                   | Focused research, simple writeups   |
| Sequential     | Output of one feeds next                           | Research → Analyze → Write report   |
| Parallel       | Multiple agents concurrently; synthesis afterwards | Multi‑source comparisons            |
| Handoff Chains | Explicit role transitions with artifacts           | Complex coding + verification flows |

Supervisor chooses based on task structure + examples; can be overridden via configuration or future explicit flags.

---

## Agents

Core specialists: Researcher, Analyst, Writer, Reviewer, Judge (quality). Extended handoff specialists: Planner, Executor, Coder, Verifier, Generator.

See **[AGENTS.md](AGENTS.md)** for detailed roles, tool usage, configuration examples, and selection guidelines.

---

## DSPy Optimization

Training examples live in `src/agentic_fleet/data/supervisor_examples.json`:

```json
{
  "task": "Research the latest AI advances",
  "team": "Researcher: web search\nAnalyst: code + data",
  "assigned_to": "Researcher,Analyst",
  "mode": "sequential"
}
```

Compilation (BootstrapFewShot + GEPA) occurs on first run (if `DSPY_COMPILE=true`). Cache stored under `logs/compiled_supervisor.pkl`. Refresh via:

```bash
uv run python -m agentic_fleet.scripts.manage_cache --clear
```

---

## Observability & History

- **History**: Structured events appended to `logs/execution_history.jsonl`.
- **Tracing**: Enable OpenTelemetry in YAML; export to AI Toolkit / OTLP endpoint.
- **Logging**: Adjustable log level via env (`AGENTIC_FLEET_LOG_LEVEL=DEBUG`).
- **Analysis**: `scripts/analyze_history.py --all` surfaces aggregate metrics.

---

## Evaluation & Self-Improvement

Run batch evaluations against curated tasks:

```bash
uv run python -m agentic_fleet.cli.console analyze --dataset data/evaluation_tasks.jsonl
```

Generate evaluation datasets from history:

```bash
uv run python scripts/create_history_evaluation.py
```

Self‑improve routing by folding high‑quality history examples back into DSPy training:

```bash
uv run python scripts/self_improve.py --max 50
```

---

## Testing & Quality

```bash
make check                 # lint + format (Ruff), type‑check (mypy)
make test                  # run pytest suite
PYTHONPATH=. uv run pytest tests/workflows/test_supervisor_workflow.py::test_supervisor_workflow -q
```

Key test domains: routing accuracy, tool registry integration, judge refinement, lazy compilation, tracing hooks.

---

## Troubleshooting

| Symptom                | Cause                    | Fix                                                                       |
| ---------------------- | ------------------------ | ------------------------------------------------------------------------- |
| Missing web citations  | `TAVILY_API_KEY` unset   | Export key or set in `.env`                                               |
| Workflow startup fails | Missing `OPENAI_API_KEY` | Set `OPENAI_API_KEY` in `.env` or environment                             |
| Configuration error    | Invalid YAML values      | Check `workflow_config.yaml` for invalid values (e.g., temperature > 2.0) |
| Slow first run         | DSPy compilation         | Enable cache; reduce `max_bootstrapped_demos`                             |
| No streaming output    | `enable_streaming=false` | Toggle in YAML                                                            |
| Low quality score      | Insufficient examples    | Add training examples; rerun compilation                                  |
| Tool warning           | Name mismatch            | Verify tool name & registry entry                                         |

Detailed guides: `docs/users/troubleshooting.md`, `docs/guides/dspy-optimizer.md`.

---

## Contributing

1. Fork / branch (`breaking-refactor` for large changes)
2. Add or update tests (prefer focused unit tests over broad integration when possible)
3. Run `make check` and ensure no style / type errors
4. Update docs (README, AGENTS.md, or relevant guide) for user‑visible changes
5. Submit PR with clear rationale & architectural notes (link to `docs/developers/architecture.md` sections if modifying internals)

Please see: `docs/developers/contributing.md`.

---

## License

MIT License – see [LICENSE](LICENSE).

---

## Acknowledgments

- **Microsoft agent-framework** – Orchestration, events & tool interfaces
- **DSPy (Stanford NLP)** – Prompt optimization & structured signatures
- **Tavily** – Reliable, citation‑rich web search
- **OpenAI Responses** – Event paradigm enabling unified CLI/TUI/frontend streaming

---

## Related Documentation

- Getting Started: `docs/users/getting-started.md`
- Configuration: `docs/users/configuration.md`
- Architecture Deep Dive: `docs/developers/architecture.md`
- Quick Reference: `docs/guides/quick-reference.md`
- DSPy Optimization: `docs/guides/dspy-optimizer.md`
- Evaluation: `docs/guides/evaluation.md`
- Tracing: `docs/guides/tracing.md`
- Self Improvement: `docs/users/self-improvement.md`
- Troubleshooting: `docs/users/troubleshooting.md`

---

Happy hacking! 🚀
