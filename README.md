![AgenticFleet Architecture](docs/afleet-preview.png)
# AgenticFleet

> Multi-agent orchestration built on the Microsoft Agent Framework.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

AgenticFleet coordinates specialised researcher, coder, and analyst agents through the Magentic planner/manager pattern. It gives you a batteries-included environment for planning, delegating, checkpointing, and supervising complex tasks from the command line.

---

## Why AgenticFleet

- **Magentic-native** – First-class support for the Microsoft Agent Framework manager/executor stack.
- **Thoughtful CLI** – Codex-style interface with history search, live status streaming, and readable plan/progress sections (`fleet`).
- **Persistent context** – Optional Mem0 memory layer (OpenAI-backed) plus on-disk workflow checkpoints.
- **Safety rails** – HITL approvals, per-agent runtime toggles, and configurable execution limits.
- **Documentation first** – Every subsystem has a dedicated guide in `docs/`.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- OpenAI API key (`OPENAI_API_KEY`)
- Microsoft Agent Framework packages (`agent-framework`, its core/azure/mem0 extras); install them with `uv pip install "agent-framework[azure-ai,mem0]"` to enable full Magentic execution

### Install & Configure

```bash
# 1. Clone
git clone https://github.com/Qredence/AgenticFleet.git
cd AgenticFleet
# 2. Configure environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY (plus optional Mem0 settings)
# 3. Install dependencies
uv sync
# 4. Launch the CLI
uv run fleet
```

The CLI provides:

```text
AgenticFleet
________________________________________________________________________
Task                ➤ build a memory strategy for my research bot
Plan · Iteration 1  Facts: … | Plan: …
Progress            Status: In progress | Next speaker: researcher
Agent · researcher  …
Result              …
```

History search (`↑` / `↓` or `Ctrl+R`), checkpoints (`checkpoints`, `resume <id>`), and graceful exits (`quit`) are all built in.

---

## Agents at a Glance

| Agent        | Model default | Purpose                               |
|--------------|---------------|---------------------------------------|
| Orchestrator | `gpt-5`       | Plans, delegates, synthesises         |
| Researcher   | `gpt-5`       | Finds and summarises sources          |
| Coder        | `gpt-5`       | Drafts code and explains run steps    |
| Analyst      | `gpt-5`       | Interprets data and suggests visuals  |

Runtime toggles (`stream`, `store`, `checkpoint`) live in each `agents/<role>/config.yaml` and are attached to the instantiated `ChatAgent` for orchestration to inspect.

---

## Architecture & Workflow

1. The Magentic manager decomposes the task into facts and steps.
2. Progress ledgers decide which specialist agent should speak next.
3. Agent responses stream back into the CLI (deltas buffered, final message rendered once per turn).
4. Optional HITL gates (code execution, file operations, etc.) are enforced via approval handlers.
5. Checkpoints capture state after each round; Mem0 stores long-term knowledge.

Dive deeper:

- `docs/architecture/magentic-fleet.md`
- `docs/features/magentic-fleet-implementation.md`
- `docs/operations/checkpointing.md`
- `docs/operations/mem0-integration.md`

---

## Configuration Essentials

- **Workflow** – `src/agenticfleet/config/workflow.yaml` (models, reasoning effort, checkpoint settings, HITL).
- **Agents** – `src/agenticfleet/agents/<role>/config.yaml` (system prompts, runtime flags).
- **Environment** – `.env` for OpenAI credentials, optional Mem0 (`MEM0_HISTORY_DB_PATH`, `OPENAI_EMBEDDING_MODEL`).

---

## Development Workflow

```bash
# Lint & format
uv run ruff check .
uv run black .
# Type check
uv run mypy src/agenticfleet
# Tests (quick + full)
uv run pytest tests/test_config.py
uv run pytest
```

Additional integration-specific tests live in `tests/test_cli_ui.py` (console parsing) and `tests/test_mem0_context_provider.py` (memory provider).

---

## Documentation Map

The `docs/` directory is structured by intent:

- `getting-started/` – quick reference & command guides.
- `features/` – deep dives on Magentic, HITL, checkpointing.
- `operations/` – repo guidelines, CI, Mem0 configuration.
- `guides/` – step-by-step walkthroughs.
- `overview/` – implementation summary, roadmap, a progress tracker.

See `docs/README.md` for a full index.

---

## Contributing

Pull requests are welcome! Please:

1. Open an issue to discuss substantial changes.
2. Follow the existing commit style (`feat:`, `fix:`, etc.).
3. Run the lint, type-check, and test suite listed above.
4. Update documentation when behaviour changes.

AgenticFleet is released under the [MIT License](./LICENSE).
