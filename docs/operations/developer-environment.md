# Developer Environment (uv-first)

Last updated: October 12, 2025

This guide captures the uv-first tooling, editor configuration, and automation that were put in place during the 0.5.0 release cycle.

## Project tooling
- `pyproject.toml` defines strict mypy options, Ruff linting via `[tool.ruff.lint]`, and dev dependencies grouped under `[dependency-groups]`.
- `Makefile` wraps the most common commands (`make install`, `make sync`, `make check`, `make pre-commit-install`, etc.).
- `.pre-commit-config.yaml` runs Ruff formatting, Ruff linting, Black, mypy, and hygiene hooks locally and in pre-commit.ci.
- `.vscode/settings.json` enforces the Python extension as the default formatter and enables Ruff fix-on-save; `.vscode/tasks.json` exposes uv-powered tasks for sync, lint, test, and run.

## GitHub Actions
The CI workflow (`.github/workflows/ci.yml`) executes on pushes and PRs:
- Python 3.12 / 3.13 matrix with uv caching.
- Lint (Ruff), format check (Black), type check (mypy – non-blocking), configuration validation, and pytest.
- Optional safety scanning hook.

## Quick start
```bash
cp .env.example .env          # configure OPENAI_API_KEY et al.
make install                  # uv sync + tooling bootstrap
make pre-commit-install       # enable git hooks
make test-config              # runs settings + workflow config assertions
make check                    # lint + format + type check + tests
```

## Known follow-ups
- Ten mypy warnings remain (missing stubs and return annotations); track in issue backlog.
- Temperature settings are retained in agent configs for future runtime overrides once supported.
