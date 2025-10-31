# AGENTS.md

## Scope

This guide applies to everything inside `docs/`. Use it whenever you edit developer documentation, API references, or architecture notes. Markdown files here are consumed by humans and coding agents alike, so accuracy, relative linking, and command hygiene (`uv run …` for Python tooling) are non-negotiable.

## Directory Map

- `docs/api/` — FastAPI endpoints, backend integration, and error-handling guides.
- `docs/cli/` — Workflow CLI usage and implementation notes.
- `docs/configuration-guide.md` — Central reference for environment variables and YAML configs.
- `docs/responsive-design-implementation.md` — Frontend UI/UX considerations.

## Authoring Guidelines

- Prefer concise, task-focused sections. Link to source files (e.g. `src/agentic_fleet/api/workflows/service.py`) using relative paths so links remain valid in forks.
- Commands interacting with Python must include the `uv run` prefix (e.g. `uv run pytest`). JavaScript tooling should run via npm scripts from the correct directory.
- Describe configuration changes in terms of `config/workflows.yaml` and agent-specific YAML, not hardcoded Python constants.
- Highlight required environment variables explicitly; reference `.env.example` instead of restating secrets inline.
- When documenting Azure Cosmos DB or other cloud dependencies, reiterate the partitioning and retry guidance listed in `.env.example` and `azurecosmosdb.instructions.md`.
- Use fenced code blocks for multi-line examples, and leave a blank line before and after tables to satisfy markdown lint heuristics.

## Previewing & Validation

- Install optional tooling with `npm install --global markdownlint-cli` if you want live linting, but it is not a hard dependency.
- Ensure links resolve by opening docs in VS Code's Markdown preview (`⌘K V`).
- Run `uv run python tools/scripts/validate_agents_docs.py` from the repo root after adjusting any AGENTS or docs content; the script warns about missing tables, `uv run` omissions, or undocumented sections.
- If you introduce new command sequences, test them locally before publishing. For example, validate backend snippets with `uv run python -m agentic_fleet` and frontend snippets from `src/frontend`.

## Contribution Checklist

1. Confirm the relevant section already exists; prefer updating existing guidance over duplicating content.
2. Keep headings sentence case (e.g. “FastAPI error handling” rather than title case) to align with the rest of the docs set.
3. When adding screenshots or assets, place them inside `assets/` and reference them relatively.
4. Update cross-references (e.g. README or root `AGENTS.md`) if new workflows, scripts, or commands are introduced.
5. Re-run `make validate-agents` (calls the documentation audit script) and address any reported findings before submitting a PR.

## Escalation

Documentation questions usually map to one of three code owners:

- Backend workflows → see `src/agentic_fleet/AGENTS.md`.
- Frontend/app shell → see `src/frontend/AGENTS.md`.
- Release process, CI, or repo-wide policy → refer back to the root `AGENTS.md` and `.github` workflows.
