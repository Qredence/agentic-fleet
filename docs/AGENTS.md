# AGENTS.md

## Scope

This guide applies to everything inside `docs/`. Reference it whenever you author architecture notes,
API references, CLI usage docs, or supporting design specs. All root-level invariants from
`../AGENTS.md` apply here—especially the requirement to run Python commands through `uv run …` and to
keep documentation synchronized with the codebase.

## Directory Map

- `docs/api/` — FastAPI endpoint contracts, streaming semantics, error handling, and integration
  examples.
- `docs/cli/` — Typer CLI walkthroughs, scripted workflow samples, and troubleshooting.
- `docs/configuration-guide.md` — Central reference for environment variables, workflow resolution
  order, and deployment knobs.
- `docs/responsive-design-implementation.md` — Frontend layout constraints, breakpoints, and design
  tokens consumed by the SPA.
- `docs/release-checklist.md`, `docs/testing-playbook.md` (if present) — link these back into PR
  templates or `README.md` when updated.

## Writing Standards

- Keep sections task-focused and prefer relative links to code (`../src/agentic_fleet/api/...`) so
  forks and documentation previews remain valid.
- Commands that touch Python, pytest, or Ruff **must** include `uv run`. JavaScript tooling belongs in
  `src/frontend` and should be invoked through the provided npm scripts.
- Describe the configuration chain accurately: `AF_WORKFLOW_CONFIG` (absolute path) → packaged
  `src/agentic_fleet/workflows.yaml`. Mention the relevant `agents/*.py` modules exposing
  `get_config()` whenever you document a workflow.
- Highlight required environment variables explicitly. Point to `.env.example` instead of copying
  secrets, and reference cloud-specific guidance (for example
  `docs/azurecosmosdb.instructions.md`) when applicable.
- Use fenced code blocks for multi-line examples and leave blank lines around tables to satisfy the
  markdown lint heuristic enforced by `validate_agents_docs.py`.
- When adding diagrams or screenshots, store them in `assets/` and use relative paths so GitHub,
  Markdown preview, and docs tooling stay in sync.

### Agent Lifecycle Hooks

To support agents that need to manage stateful resources (e.g., database connections, temporary files), the framework provides optional lifecycle hooks through the `AgentLifecycle` protocol. Agents can implement `warmup()` and `teardown()` methods to initialize and release resources at the beginning and end of a workflow run.

- **`warmup()`**: Called once before the agent processes any messages. Use this hook to acquire resources, initialize connections, or perform any setup required for the agent to function.
- **`teardown()`**: Called once after the workflow run is complete, including in cases of errors or interruptions. This hook should be used to release resources, close connections, and perform cleanup tasks to prevent resource leaks.

#### Example Implementation

Here is an example of a simple agent that manages a temporary file during its lifecycle:

```python
import tempfile
from pathlib import Path
from typing import Protocol

class AgentLifecycle(Protocol):
    def warmup(self) -> None:
        ...

    def teardown(self) -> None:
        ...

class FileProcessingAgent:
    def __init__(self):
        self._temp_file = None
        self._file_path = None

    def warmup(self) -> None:
        """Create a temporary file for the workflow run."""
        self._temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+")
        self._file_path = Path(self._temp_file.name)
        print(f"Agent warmed up. Temporary file created at: {self._file_path}")

    def teardown(self) -> None:
        """Close and delete the temporary file."""
        if self._temp_file:
            self._temp_file.close()
            self._file_path.unlink()
            print(f"Agent torn down. Temporary file {self._file_path} removed.")

    def process(self, message: str) -> str:
        """Processes a message and writes it to the temporary file."""
        if not self._file_path:
            return "Error: Agent has not been warmed up."

        self._file_path.write_text(message)
        return f"Message written to {self._file_path}"

```

The workflow runner will automatically detect if an agent implements these methods and call them at the appropriate times.

## Previewing & Validation

- Optional: install `markdownlint-cli` (`npm install --global markdownlint-cli`) for local linting.
- Open files in VS Code’s Markdown preview (`⌘K V`) before merging to verify anchors and relative
  links.
- Run `uv run python tools/scripts/validate_agents_docs.py` (or `make validate-agents`) after any doc
  edits. Address blocking errors before publishing; warnings should be triaged in follow-up tasks.
- Exercise new command sequences locally. Validate backend snippets with `uv run python -m agentic_fleet`
  and frontend sequences from `src/frontend`.

## Update Triggers

- New endpoint, workflow, or CLI behaviour needs a corresponding update in `docs/api/` or `docs/cli/`.
- Configuration changes (env vars, YAML overrides, secrets management) must update
  `docs/configuration-guide.md` and cross-reference the root `AGENTS.md`.
- UI/UX adjustments that affect responsive behaviour or mock flows should refresh the relevant doc
  under `docs/`.
- Any material change in documentation structure should also touch the root index (README) and the
  AGENTS guides for backend, tests, or frontend if they reference the same feature.

## Escalation

- Backend workflows and orchestration concerns: start with `src/agentic_fleet/AGENTS.md`.
- Frontend shell or streaming UI questions: see `src/frontend/AGENTS.md`.
- Test coverage, fixtures, or load scenarios: reference `tests/AGENTS.md`.
- Repository-wide process, CI, or release policy: fall back to the root `AGENTS.md` and the automation
  notes in `.github/`.
