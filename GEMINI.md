# AgenticFleet

AgenticFleet is a production-ready multi-agent orchestration system that automatically routes tasks to specialized AI agents and orchestrates their execution through a self-optimizing pipeline. It combines **DSPy** for intelligent task routing and **Microsoft Agent Framework** for robust agent execution.

## Project Structure

- **Backend (`src/agentic_fleet`)**: Python-based orchestration engine.
  - `agents/`: Agent definitions and factory.
  - `workflows/`: Workflow orchestration (Supervisor, Executors).
  - `dspy_modules/`: DSPy signatures, modules, and optimization logic.
  - `app/`: FastAPI backend for the web interface.
  - `cli/`: Command-line interface (`typer`).
  - `config/`: Configuration handling (`workflow_config.yaml`).
- **Frontend (`src/frontend`)**: React/Vite web interface for monitoring and interacting with agents.
- **Documentation (`docs/`)**: Comprehensive guides for users and developers.
- **Tests (`tests/`)**: Backend tests (`pytest`). Frontend tests are in `src/frontend/src/tests`.

## Key Technologies

- **Language:** Python 3.12+ (Backend), TypeScript (Frontend).
- **Package Management:** `uv` (Python), `npm` (Frontend).
- **Core Frameworks:** Microsoft Agent Framework, DSPy, FastAPI, React, Vite, Tailwind CSS.
- **Tools:** Tavily (Search), OpenTelemetry (Tracing), Azure AI Evaluation.

## Building and Running

The project uses a `Makefile` to simplify common development tasks.

### Setup

1.  **Install Dependencies:**
    ```bash
    make dev-setup  # Installs python dependencies (via uv), frontend dependencies (npm), and pre-commit hooks
    ```
2.  **Configuration:**
    - Copy `.env.example` to `.env`.
    - Set `OPENAI_API_KEY` (required).
    - Optionally set `TAVILY_API_KEY` for web search capabilities.

### Development

- **Full Stack (Backend + Frontend):**

  ```bash
  make dev
  ```

  - Backend: http://localhost:8000
  - Frontend: http://localhost:5173

- **CLI Usage:**

  ```bash
  make run  # Starts the interactive CLI
  # Or directly:
  uv run agentic-fleet run -m "Your task"
  ```

- **Backend Only:**

  ```bash
  make backend
  ```

- **Frontend Only:**
  ```bash
  make frontend-dev
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
- **All Tests:**
  ```bash
  make test-all
  ```

## Development Conventions

### Python (Backend)

- **Dependency Management:** strictly use `uv`.
  - Sync: `make sync`
- **Linting & Formatting:** `ruff`.
  - Check: `make lint`
  - Fix: `make format`
- **Type Checking:** `ty` (or `pyright`/`mypy` via `ty`).
  - Check: `make type-check`

### TypeScript (Frontend)

- **Linting:** `eslint`.
  - Check: `make frontend-lint`
- **Formatting:** `prettier`.
  - Format: `make frontend-format`

### Architecture Notes

- **DSPy Integration:** DSPy is used for high-level reasoning (routing, analysis). Modules are compiled offline.
- **Agent Framework:** Microsoft's framework handles the low-level agent execution loop and event stream.
- **Configuration:** All runtime settings are in `src/agentic_fleet/config/workflow_config.yaml`.
