# Project: AgenticFleet

## Project Overview

AgenticFleet is a multi-agent orchestration system built on the Microsoft Agent Framework. It uses a central "Magentic" planner/manager to coordinate specialized agents (Researcher, Coder, Analyst) to accomplish complex tasks. The project is written in Python and uses `uv` for dependency management. It features an interactive command-line interface (CLI), workflow checkpointing, and human-in-the-loop (HITL) approval mechanisms for safety.

**Key Technologies:**
- **Language:** Python 3.12+
- **Package Manager:** `uv`
- **Core Framework:** Microsoft Agent Framework (`magentic`)
- **CLI:** `rich`, `prompt-toolkit`
- **Configuration:** YAML

**Architecture:**
The system is designed around a central orchestrator that decomposes tasks and delegates them to a fleet of agents.
- **Orchestrator (`MagenticFleet`):** Manages the overall task, breaks it into steps, and synthesizes results.
- **Agents (e.g., `Researcher`, `Coder`, `Analyst`):** Specialized agents that perform specific functions like web searches, code execution, or data analysis.
- **Configuration:** Project-wide settings are in `src/agenticfleet/config/workflow.yaml`, and agent-specific settings (like system prompts and tools) are in `src/agenticfleet/agents/<agent_name>/config.yaml`.
- **Entry Point:** The application is launched via the CLI script at `src/agenticfleet/cli/repl.py`.

## Building and Running

**Prerequisites:**
- Python 3.12+
- `uv` package manager
- An `OPENAI_API_KEY` set in a `.env` file.

**Installation:**
1.  Clone the repository.
2.  Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
3.  Install dependencies:
    ```bash
    uv sync
    ```

**Running the Application:**
To start the interactive CLI:
```bash
uv run fleet
```
or
```bash
uv run agentic-fleet
```

**Running Tests:**
- Run all tests:
  ```bash
  uv run pytest
  ```
- Run a specific test file:
  ```bash
  uv run pytest tests/test_config.py
  ```

## Development Conventions

- **Linting:** `ruff` is used for linting. Run with:
  ```bash
  uv run ruff check .
  ```
- **Formatting:** `black` is used for code formatting. Run with:
  ```bash
  uv run black .
  ```
- **Type Checking:** `mypy` is used for static type checking. Run with:
  ```bash
  uv run mypy src/agenticfleet
  ```
- **Commits:** The project follows the conventional commit style (e.g., `feat:`, `fix:`, `docs:`).
- **Documentation:** The `docs/` directory contains extensive documentation on architecture, features, and operations. Changes in behavior should be accompanied by documentation updates.
