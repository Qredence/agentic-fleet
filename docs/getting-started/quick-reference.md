# AgenticFleet Quick Reference

**Version:** 0.5.1
**Last Updated:** October 16, 2025

Use this page as the fastest path from a fresh clone to a productive workstation.

---

## First-Time Setup

```bash
cp .env.example .env              # Add OPENAI_API_KEY and optional Mem0 settings
uv sync                           # Install runtime + dev dependencies
uv run python tests/test_config.py  # Smoke-test configuration (pytest suite)
uv run fleet                      # Launch the interactive CLI
```

> Legacy entry points such as `python main.py` have been retired. Always run
> the packaged CLI (`fleet` / `agentic-fleet`) or the module form
> `uv run python -m agenticfleet`.

---

## Everyday Commands

| Task | Recommended Command |
|------|---------------------|
| Launch CLI | `uv run fleet` |
| Run with workflow flag | `uv run fleet --workflow=magentic` *(default)* |
| Run full pytest suite | `make test` *(wraps `uv run pytest -v`)* |
| Config smoke test only | `make test-config` *(wraps `uv run python tests/test_config.py`)* |
| Format & lint | `make format` then `make lint` |
| Static checks bundle | `make check` *(ruff + mypy)* |
| Clean caches | `make clean` |
| Install/update deps | `make install` *(first run)*, `make sync` *(subsequent sync)* |

All `make` targets are thin wrappers around `uv` commands defined in the root `Makefile`.

---

## Key Files & Folders

| Path | Description |
|------|-------------|
| `src/agenticfleet/cli/repl.py` | Console entry point invoked by `fleet` / `agentic-fleet`. |
| `src/agenticfleet/config/workflow.yaml` | Workflow-level limits, checkpointing, HITL settings. |
| `src/agenticfleet/config/settings.py` | Environment loader and config helpers. |
| `src/agenticfleet/agents/<role>/config.yaml` | Per-agent prompts, tooling, runtime flags. |
| `src/agenticfleet/fleet/magentic_fleet.py` | Magentic orchestration wrapper and factory (`create_default_fleet`). |
| `tests/test_config.py` | End-to-end configuration smoke tests. |
| `docs/` | Architecture, feature, and operations guides (see `docs/README.md`). |
| `Makefile` | Shortcut commands for development workflows. |

---

## Agent Roster (Defaults)

| Agent | Config File | Default Model | Enabled Tools | Purpose |
|-------|-------------|---------------|---------------|---------|
| Orchestrator | `src/agenticfleet/agents/orchestrator/config.yaml` | `gpt-5` | — | Plans tasks, selects speakers, synthesises results. |
| Researcher | `src/agenticfleet/agents/researcher/config.yaml` | `gpt-5` | `web_search_tool` | Performs external research with inline citations. |
| Coder | `src/agenticfleet/agents/coder/config.yaml` | `gpt-5` | — *(draft-only)* | Drafts code and runbooks; execution stays manual. |
| Analyst | `src/agenticfleet/agents/analyst/config.yaml` | `gpt-5` | `data_analysis_tool`, `visualization_suggestion_tool` | Interprets data and recommends visuals. |

Tweak models, runtime flags, or tool availability by editing the corresponding YAML file, then rerun `uv run python tests/test_config.py` to validate.

---

## Configuration Reference

- **Environment:** `.env` (copied from `.env.example`) supplies `OPENAI_API_KEY`, optional Mem0 and Azure identity settings.
- **Workflow:** `src/agenticfleet/config/workflow.yaml`
  - `workflow.max_rounds`, `max_stalls`, `max_resets`, `timeout_seconds`
  - `checkpointing` → storage path (`./checkpoints`) and retention
  - `human_in_the_loop` → approval gates for high-risk operations
- **Memory:** Enable persistent Mem0 in `workflow.checkpointing` and the agent runtime sections (`checkpoint: true`).
- **Console Options:** CLI accepts `--workflow`, reserved for backwards compatibility; all values defer to Magentic orchestration.

---

## Testing & Quality Gates

```bash
make test-config        # Sanity check configs, factories, imports
make test               # Full pytest run (async + CLI + mem0 suites)
make lint               # Ruff lint rules (pycodestyle, pyflakes, pyupgrade)
make format             # Ruff --fix + Black
make type-check         # Mypy (src-only)
make check              # Lint + mypy bundle
```

Spot-check specific tests with `uv run pytest tests/<file>.py -k "<expression>"`.

---

## CLI Tips

- **History & Search:** Use ↑ / ↓ to cycle prompts, `Ctrl+R` to fuzzy-search history.
- **Checkpointing:** `checkpoints` lists saved states, `resume <id>` continues a run.
- **Status Panel:** The console streams plan deltas, agent turns, and final answers.
- **Exit:** Type `quit`, `exit`, or press `Ctrl+C` and confirm.

---

## Troubleshooting Cheatsheet

| Symptom | Quick Fix |
|---------|-----------|
| `OPENAI_API_KEY not set` | Confirm `.env` exists or export the key before running the CLI. |
| Missing dependencies | `make sync` (or `uv sync`) to reinstall from `uv.lock`. |
| Stale caches or weird imports | `make clean` then rerun tests. |
| CLI refuses to start | Run `uv run python tests/test_config.py` to validate configs and API credentials. |
| Mem0/context issues | Check `var/memories/` directory and review `docs/operations/mem0-integration.md`. |

For deeper diagnostics, see `docs/runbooks/troubleshooting.md`.
