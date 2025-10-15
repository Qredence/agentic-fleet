# Repository Guidelines

## Project Structure & Module Organization

Each role-specific factory lives under `agents/<role>/agent.py`, keeping prompts and tool wiring close to the code they power. Shared defaults stay in `config/workflow_config.yaml`, while `config/settings.py` loads `.env` secrets and exposes helpers like `settings.load_agent_config()`. Place orchestration glue in `workflows/`, long-form notes in `docs/`, and mirror module paths under `tests/` (for example `tests/test_researcher_agent.py`).

## Build, Test, and Development Commands

Install dependencies with `uv sync`, or `uv pip install -e ".[dev]"` when adjusting packaging. Run suites via `uv run pytest` (filter with `uv run pytest -k researcher`), and finish every branch with `uv run black .`, `uv run ruff check .`, and `uv run mypy agents config`. To verify wiring quickly, run `uv run python -c "from agents.orchestrator_agent.agent import create_orchestrator_agent; create_orchestrator_agent()"`; a successful instantiation confirms credentials and configs.

## Coding Style & Naming Conventions

ALWAYS USE uv to run and manage python packages execution etc. Black and Ruff enforce a 100-character limit and Python 3.12 targets (`pyproject.toml`). Name factories and tools imperatively (`create_<role>_agent`, `run_<action>_tool`) and keep docstrings in the Google style referenced in `agents/coder_agent/agent_config.yaml`. YAML configs should use snake-case keys (`max_rounds`, `analysis_types`), live in source control, and keep secrets in `.env`.

## Testing Guidelines

Use `pytest` (and `pytest.mark.asyncio` for coroutines) and patch `agent_framework.openai.OpenAIResponsesClient` to avoid real network calls. Name files `test_<feature>.py`, place shared fixtures in `tests/conftest.py`, and add regression coverage for new tools or workflow branches. Focus assertions on delegation logic and config parsing so failures stay actionable.

## Commit & Pull Request Guidelines

Recent history favors short, imperative subjects (for example `Bump actions/setup-python from 5 to 6`). Keep commits focused, reference issues with `#123`, and explain config or workflow changes in the body. Pull requests should describe impact, list affected agents/configs, and include `pytest`, `ruff`, and `mypy` outputs; attach visuals only when updating stakeholder docs.

## Agent Configuration & Security Tips

Never commit API keys—`config/settings.py` raises if `OPENAI_API_KEY` is missing, so create a local `.env` first. Adjust behavior via each `agents/<role>/agent_config.yaml`, documenting new tool toggles and keeping temperatures conservative for determinism. When updating orchestration limits in `config/workflow_config.yaml`, call out the change in your PR so teammates stay in sync.

## Versioning & Releases

Before tagging a release:

1. Bump the version in **all** of the following: `pyproject.toml`, `src/agenticfleet/__init__.py`, and the badge/version callout near the top of `README.md`.
2. Update `docs/releases/` with a dated changelog entry summarising user-facing changes.
3. Regenerate build artefacts (`uv build` or the CI workflow) only after the bumps are committed to avoid stale wheels.
4. Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/agenticfleet` locally; capture the green outputs in the release PR description.
5. Before pushing, run `make clean` so `dist/`, `__pycache__/`, and other transient folders never hit version control. CI will fail fast if artefacts sneak into a branch.
