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
  `src/frontend/src` and should be invoked through the provided npm scripts.
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

## Previewing & Validation

- Optional: install `markdownlint-cli` (`npm install --global markdownlint-cli`) for local linting.
- Open files in VS Code’s Markdown preview (`⌘K V`) before merging to verify anchors and relative
  links.
- Run `uv run python tools/scripts/validate_agents_docs.py` (or `make validate-agents`) after any doc
  edits. Address blocking errors before publishing; warnings should be triaged in follow-up tasks.
- Exercise new command sequences locally. Validate backend snippets with `uv run python -m agentic_fleet`
  and frontend sequences from `src/frontend/src`.

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
