# Project AGENTS

## Overview
This repo is bootstrapping the `agentic_fleet` v2.0 architecture (Microsoft Agent Framework + DSPy).

## Repo layout
- `agentic-fleet/` contains the Python package and its source tree.
- `agentic-fleet/src/agentic_fleet/` is the package root.

## Commands
- Tests: `uv run python tests/verify_phase_2.py`, `uv run python tests/verify_phase_3.py`, `uv run python tests/verify_phase_5.py`.
- Lint/format: not configured yet (use `uv run` once configured).
- Dev server: `uv run uvicorn --app-dir src agentic_fleet.main:app --reload`.

## Conventions
- Use `uv` for Python env/deps and for running commands (`uv run ...`).
- Keep all source under `agentic-fleet/src/agentic_fleet/`.
- Update `PLANS.md` when making multi-step changes.
- Database: SQLModel sync engine, initialized on startup; configure `DATABASE_URL` in `.env`.
- DSPy state: set `FLEET_STATE_DIR` to control where optimized planner JSON is stored (default `.context/state`).
- LLM routing: set `FLEET_MODEL_ROUTING=0` to disable per-role routing (tests); configure model aliases with `FLEET_MODEL_ROUTER`, `FLEET_MODEL_PLANNER`, `FLEET_MODEL_WORKER`, `FLEET_MODEL_JUDGE`, or per-team overrides like `FLEET_MODEL_RESEARCH_PLANNER`.
- Provider env vars:
  - DeepInfra (OpenAI-compatible): `DEEPINFRA_API_KEY`, optional `DEEPINFRA_API_BASE_URL`.
  - Gemini (google-genai): `GOOGLE_API_KEY` (or `GEMINI_API_KEY`).
  - ZAI Anthropic (GLM): `ZAI_API_KEY`, `ZAI_ANTHROPIC_BASE_URL`, optional `ZAI_MODEL_NAME`.
