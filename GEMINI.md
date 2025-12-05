# AgenticFleet

## Project Overview

AgenticFleet is a self-optimizing multi-agent orchestration system. It combines **DSPy** for intelligent task routing and optimization with the **Microsoft agent-framework** for robust agent execution. The system features a Python-based backend (FastAPI) and a React-based frontend, allowing users to orchestrate complex workflows involving multiple AI agents (Researcher, Analyst, Coder, etc.).

**Key Technologies:**

- **Backend:** Python 3.12+, DSPy, Microsoft Agent Framework, Azure AI Agents, FastAPI, Uvicorn.
- **Frontend:** React, Vite, Tailwind CSS, TypeScript, Zustand.
- **Package Manager:** `uv` (Python), `npm` (Node.js).
- **Orchestration:** Magentic Fleet pattern with DSPy optimizers.

## Architecture & Directory Structure

- **`src/agentic_fleet/`**: Core backend logic.
  - `agents/`: Agent definitions and implementations.
  - `workflows/`: Orchestration logic (Supervisor, distinct execution modes).
  - `dspy_modules/`: DSPy signatures, modules, and reasoners.
  - `app/`: FastAPI application (API routes, server setup).
  - `cli/`: Typer-based CLI entry point.
  - `tools/`: Tools available to agents (Tavily, browser, code interpreter).
- **`src/frontend/`**: React application source code.
- **`scripts/`**: Utility scripts for benchmarking, evaluation, and server management.
- **`tests/`**: Backend tests using Pytest.
- **`.var/`**: Runtime directory for logs, caches, and local databases (ignored by git).
- **`Makefile`**: Central control for build, test, and dev commands.

## Setup & Installation

The project uses `uv` for Python dependency management and `npm` for the frontend.

1.  **Install Backend Dependencies:**
    ```bash
    make install
    ```
2.  **Install Frontend Dependencies:**
    ```bash
    make frontend-install
    ```
3.  **Environment Setup:**
    - Copy `.env.example` to `.env`.
    - Set `OPENAI_API_KEY` (required) and `TAVILY_API_KEY` (optional).

## Development Workflow

### Running the Application

- **Full Stack Development (Recommended):**
  Runs backend (port 8000) and frontend (port 5173) simultaneously.

  ```bash
  make dev
  ```

- **Backend Only:**

  ```bash
  make backend
  ```

- **Frontend Only:**

  ```bash
  make frontend-dev
  ```

- **CLI Usage:**
  Execute tasks directly from the terminal.
  ```bash
  uv run python -m agentic_fleet
  # Or specific task:
  agentic-fleet run -m "Research AI agents"
  ```

### Testing

- **Backend Tests:**
  ```bash
  make test
  ```
- **Frontend Tests:**
  ```bash
  make test-frontend
  ```
- **Run All Tests:**
  ```bash
  make test-all
  ```
- **End-to-End Tests:**
  Requires the dev server to be running.
  ```bash
  make test-e2e
  ```

### Code Quality

- **Linting:**
  ```bash
  make lint          # Backend (Ruff)
  make frontend-lint # Frontend (ESLint)
  ```
- **Formatting:**
  ```bash
  make format          # Backend (Ruff)
  make frontend-format # Frontend (Prettier)
  ```
- **Type Checking:**
  ```bash
  make type-check    # Backend (Ty)
  ```
- **Full QA Check:**
  Runs all linters, type checkers, and tests.
  ```bash
  make qa
  ```

## Key Configuration Files

- **`pyproject.toml`**: Python dependencies, build config, and tool settings (Ruff, Pytest, Ty).
- **`Makefile`**: Shortcut commands for all development tasks.
- **`src/frontend/package.json`**: Frontend dependencies and scripts.
- **`src/agentic_fleet/config/workflow_config.yaml`**: (If present) Runtime configuration for agents and workflows.

## Conventions

- **Python:** Follows PEP 8 guidelines enforced by `ruff`. Type hints are mandatory and checked by `ty`.
- **Frontend:** React functional components with Hooks. Styling via Tailwind CSS.
- **Commits:** Use clear, descriptive commit messages.
- **Testing:** New features should include accompanying unit tests.
