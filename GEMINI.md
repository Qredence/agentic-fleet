---
project_type: code
---

# AgenticFleet

## Project Overview

AgenticFleet is a multi-agent orchestration system built on the Microsoft Agent Framework. It uses a manager/executor pattern (`Magentic`) to coordinate specialized agents, including an Orchestrator, Researcher, Coder, and Analyst. The project provides a command-line interface (CLI) for interacting with the agent fleet, with features like persistent memory (via Mem0), workflow checkpointing, and human-in-the-loop (HITL) safety approvals.

The project is written in Python and uses `uv` for package management. It is designed to be highly configurable, with settings for workflows, agents, and credentials managed through YAML files and environment variables.

## Key Technologies

- **Python**: 3.12+
- **Package Manager**: `uv`
- **AI Framework**: Microsoft Agent Framework (`agent-framework`, `Magentic`)
- **Models**: OpenAI (configurable)
- **Memory**: `Mem0` (optional)
- **CLI**: `rich`, `prompt-toolkit`

## Building and Running

The project uses `uv` for dependency management and running scripts. Key commands are also available as `make` targets.

### Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/Qredence/AgenticFleet.git
    cd AgenticFleet
    ```
2. **Configure Environment:**
    Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
    ```bash
    cp .env.example .env
    ```
3. **Install Dependencies:**
    ```bash
    uv sync
    ```
    Alternatively, use the Makefile:
    ```bash
    make install
    ```

### Running the Application

To start the interactive CLI:
```bash
fleet
```
or
```bash
uv run fleet
```
or
```bash
make run
```

### Running Tests

To run the full test suite:
```bash
uv run pytest
```
or
```bash
make test
```

## Development Conventions

### Code Style & Linting

The project uses `black` for code formatting and `ruff` for linting.

- **Check for issues:**
    ```bash
    make lint
    ```
- **Format code:**
    ```bash
    make format
    ```

### Type Checking

The project uses `mypy` for static type checking.

- **Run type checker:**
    ```bash
    make type-check
    ```

### All Checks

To run all quality checks (linting, formatting, type-checking) at once:
```bash
make check
```

### Pre-commit Hooks

Pre-commit hooks are configured in `.pre-commit-config.yaml` to automatically run checks before committing.

- **Install hooks:**
    ```bash
    make pre-commit-install
    ```

## Project Structure

```
AgenticFleet/
├── src/agenticfleet/    # Main application code
│   ├── cli/             # Interactive REPL and UI
│   ├── config/          # Workflow and settings configuration
│   ├── core/            # Core logic (checkpoints, approvals)
│   └── fleet/           # Agent orchestration (Magentic)
├── tests/               # Unit and integration tests
├── docs/                # Project documentation
├── examples/            # Example scripts
├── pyproject.toml       # Project metadata and dependencies
├── Makefile             # Developer command shortcuts
└── uv.lock              # Pinned dependency versions
```

## Configuration

- **Credentials & Environment:** `.env` (API keys, Mem0 settings)
- **Workflow:** `src/agenticfleet/config/workflow.yaml` (models, checkpointing, HITL)
- **Agent Prompts:** `src/agenticfleet/agents/<role>/config.yaml`
