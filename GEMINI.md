# AgenticFleet

## Project Overview

**AgenticFleet** is a hybrid orchestration runtime combining **DSPy** and the **Microsoft Agent Framework**. It is designed to manage a self-optimizing fleet of specialized AI agents. The system uses DSPy for high-level task analysis, routing, and quality assessment, while the Microsoft Agent Framework handles low-level orchestration, event streaming, and tool execution.

**Key Technologies:**

- **Backend:** Python 3.12+, FastAPI, DSPy, Microsoft Agent Framework, Uvicorn.
- **Frontend:** React, Vite, TypeScript, Tailwind CSS.
- **Package Management:** `uv` (Python), `npm` (Node.js).
- **Database:** Azure Cosmos DB (Optional for history/persistence).

**Architecture:**
The core workflow follows a four-phase pipeline:

1.  **Analysis:** Extracts goals and constraints from the task.
2.  **Routing:** Selects the optimal agents and execution mode (Delegated, Sequential, Parallel, or Handoff).
3.  **Execution:** Agents perform tasks using assigned tools.
4.  **Quality:** Outputs are scored, potentially triggering refinement loops.

## Building and Running

The project uses a `Makefile` to standardize common development tasks.

### Prerequisites

- Python 3.12+
- Node.js & npm
- `uv` (recommended for Python dependency management)
- Git

### Setup

1.  **Install Dependencies:**

    ```bash
    make dev-setup
    ```

    This runs `make install` (Python via `uv`), `make frontend-install` (Node via `npm`), and installs pre-commit hooks.

2.  **Environment Configuration:**
    - Copy `.env.example` to `.env`.
    - Set `OPENAI_API_KEY` (Required).
    - Configure other services (Tavily, Cosmos DB, etc.) as needed.

### Running the Application

- **Full Stack (Backend + Frontend):**

  ```bash
  make dev
  ```

  - Backend: http://localhost:8000
  - Frontend: http://localhost:5173

- **Backend Only:**

  ```bash
  make backend
  ```

- **Frontend Only:**

  ```bash
  make frontend-dev
  ```

- **CLI / TUI:**
  ```bash
  agentic-fleet
  # or
  python -m agentic_fleet.cli.console
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
- **End-to-End Tests:**
  ```bash
  make test-e2e
  ```
- **Quality Checks (Lint/Type/Format):**
  ```bash
  make check
  ```

## Development Conventions

- **Code Style:**
  - **Python:** Follows PEP 8, enforced by `ruff`. Type hinting is required and checked with `mypy`.
  - **Frontend:** Standard Prettier/ESLint configuration.
- **Commit Hooks:** Pre-commit hooks are available and should be installed (`make pre-commit-install`) to ensure code quality before committing.
- **Configuration:**
  - Runtime configuration is managed via `config/workflow_config.yaml`.
  - Secrets and environment-specific variables go in `.env`.
- **Documentation:**
  - `AGENTS.md`: Defines agent roles, capabilities, and tool assignments.
  - `docs/`: Contains detailed architectural and usage documentation.

## Key Files and Directories

- `src/agentic_fleet/`: Main Python source code.
  - `agents/`: Agent implementations.
  - `dspy_modules/`: DSPy signatures and modules.
  - `workflows/`: Orchestration logic.
  - `api/`: FastAPI backend.
- `src/frontend/`: React frontend application.
- `config/`: Configuration files (`workflow_config.yaml`).
- `AGENTS.md`: Agent definition and documentation.
- `Makefile`: Task runner for build and dev commands.
- `pyproject.toml`: Python project configuration and dependencies.
