# Contributing to AgenticFleet

Thanks for your interest in improving AgenticFleet! This document summarizes the workflow and
project-specific conventions you should follow before opening a pull request.

## 1. Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) (preferred package manager)
- An Azure AI project with deployed chat + embedding models
- Required secrets configured in `.env` (copy from `.env.example`)

## 2. Local Setup

```bash
# Clone and enter the repository
git clone https://github.com/Qredence/AgenticFleet.git
cd AgenticFleet

# Install dependencies (creates/updates .venv)
uv sync

# Prepare environment variables
cp .env.example .env  # then edit with your credentials
```

## 3. Development Workflow

1. Create a feature branch from `main` (`git checkout -b feat/short-description`).
2. Make focused changes; keep prompts in `agents/<role>/config.yaml`, not in Python files.
3. Respect the orchestration contract in `src/agenticfleet/workflows/multi_agent.py`
   (`DELEGATE:` / `FINAL_ANSWER:` markers, stall counters, etc.).
4. Update or add documentation under `docs/` when patterns or workflows change.

## 4. Quality Gates

Before pushing, always run:

```bash
uv run python tests/test_config.py   # Config + factory smoke tests (6/6 must pass)
uv run pytest -q                     # Full test suite
uv run black .                       # Formatting (100-char max enforced)
uv run ruff check .                  # Lint (Py312 rules)
uv run mypy src/agenticfleet         # Type checking
```

Prefer `make check` / `make test-config` for chained commands (see `Makefile`). Patch networked
services (`OpenAIResponsesClient`, tool functions) in tests to keep suites deterministic.

## 5. Coding Standards

- Agents are created via factories in `src/agenticfleet/agents/<role>/agent.py` using
  `ChatAgent` + `OpenAIResponsesClient`.
- Tools live in `agents/<role>/tools/`, return Pydantic models, and are toggled via each
  `config.yaml`.
- Workflow state lives on `MultiAgentWorkflow`; extend the `context` dict instead of introducing
  globals.
- Follow naming conventions outlined in `docs/operations/repository-guidelines.md`.

## 6. Commit & PR Guidelines

- Use short, imperative commit subjects (for example, `feat: add analyst tool toggle`).
- Reference related issues (`#123`) in commit bodies or PR descriptions.
- Summarize behavior changes, affected agents/configs, and include test command outputs in the PR.
- Keep PRs focused; split unrelated changes into separate branches.

## 7. Documentation & Release Notes

- Update `README.md`, `docs/overview/implementation-summary.md`, or relevant runbooks when behavior
  changes.
- For user-facing changes, add a note to `docs/releases/` (create a new dated file if needed).

## 8. Reporting Security Issues

Do **not** open public issues for suspected vulnerabilities. Instead, follow the instructions in
[`SECURITY.md`](SECURITY.md).

## 9. License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).

Thank you for helping us build better multi-agent systems! 🙌
