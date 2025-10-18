# Repository Guidelines

## Project Structure & Module Organization
- `src/agenticfleet/` contains the core packages (`agents`, `core`, `fleet`, `workflows`, `config`, `cli`); extend these modules rather than introducing parallel trees so new orchestrations inherit shared utilities.
- Feature samples and walkthroughs live in `examples/`, while reusable prompts, state, and scratch data reside in `memories/`, `logs/`, and `var/`; keep new artefacts small and add README notes when behaviour or schema changes.
- Contributor-facing references, API docs, and architecture notes land in `docs/` (see `docs/guides/quickstart.md` before expanding capabilities), and every feature should ship with matching coverage under `tests/test_*.py`.

## Build, Test, and Development Commands
- `make install` (first setup) or `make sync` keeps the `uv` environment aligned with `pyproject.toml`/`uv.lock`; if you skip Makefiles, run `uv sync --all-extras`.
- Run `make run` (alias for `uv run python -m agenticfleet`) to exercise the CLI, and `make demo-hitl` to replay the HITL example pipeline.
- Quality gates: `make lint` (Ruff), `make format` (Ruff --fix + Black), `make type-check` (MyPy), and `make check` to bundle them; gate every PR with `make test` or `uv run pytest -k <pattern>` when iterating.

## Coding Style & Naming Conventions
- Target Python 3.12 with strict typing—module and function names stay `snake_case`, classes use `PascalCase`, and keep public APIs exported via the nearest `__init__.py`.
- Black enforces a 100-character line length; Ruff handles import order (`I` rules) and pyupgrade hints, so refrain from manual reordering.
- Load configuration through Pydantic and `.env` parsing in `agenticfleet.config`; avoid direct `os.getenv` calls outside this layer and document new keys in `docs/`.

## Testing Guidelines
- Pytest with `pytest-asyncio` is the default; mark coroutine tests with `@pytest.mark.asyncio` and rely on project fixtures from `tests/conftest.py`.
- Name files `test_<feature>.py` and prefer deterministic fakes over live Azure/OpenAI calls; stash canned transcripts or agent state under `tests/data/`.
- Capture coverage locally with `uv run pytest --cov=src/agenticfleet --cov-report=term-missing` whenever orchestration or workflow logic changes materially.

## Commit & Pull Request Guidelines
- Follow the conventional-commit style used in history (`fix(ci): …`, `docs: …`, etc.), keeping subjects ≤72 characters and adding context in the body or via linked issues.
- Each PR should list the checks you executed, describe behavioural changes, and attach CLI transcripts or JSON payloads for API-facing work.
- Update `docs/` or example notebooks when user-facing flows shift, and call out backwards-incompatible changes in the PR description.

## Security & Configuration Tips
- Never commit populated `.env`; use `.env.example` as the authoritative inventory of required secrets (e.g., Azure identity, Redis, OpenAI keys).
- Sanitize local recordings in `memories/`, `logs/`, and `var/` before pushing, and prefer Key Vault or managed identity wiring for production credentials.
- Review `SECURITY.md` and `docs/guides/getting_started.md` before touching authentication, agent memory persistence, or external service adapters.
