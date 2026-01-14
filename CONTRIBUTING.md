# Contributing to AgenticFleet

First off, thank you for considering contributing to AgenticFleet! 🎉

This document provides guidelines and information about contributing to this project. Following these guidelines helps communicate that you respect the time of the developers managing and developing this open-source project.

## Table of Contents

- [Contributing to AgenticFleet](#contributing-to-agenticfleet)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [Getting Started](#getting-started)
  - [How Can I Contribute?](#how-can-i-contribute)
    - [Reporting Bugs](#reporting-bugs)
    - [Suggesting Enhancements](#suggesting-enhancements)
    - [Your First Code Contribution](#your-first-code-contribution)
    - [Pull Requests](#pull-requests)
  - [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Running Tests](#running-tests)
    - [Running the Dev Server](#running-the-dev-server)
  - [Style Guidelines](#style-guidelines)
    - [Python Code Style](#python-code-style)
    - [Type Checking](#type-checking)
    - [Frontend Code Style](#frontend-code-style)
  - [Project Structure](#project-structure)
  - [Adding New Features](#adding-new-features)
    - [Adding a New Agent](#adding-a-new-agent)
    - [Adding a New Tool](#adding-a-new-tool)
    - [Adding a DSPy Signature](#adding-a-dspy-signature)
  - [Documentation](#documentation)
  - [Getting Help](#getting-help)
  - [Recognition](#recognition)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](docs/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [contact@qredence.ai](mailto:contact@qredence.ai).

## Getting Started

- Make sure you have a [GitHub account](https://github.com/signup)
- Fork the repository on GitHub
- Clone your fork locally
- Set up the development environment (see [Development Setup](#development-setup))

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Use the bug report template** and provide:

- **Clear title** – Summarize the issue in a few words
- **Steps to reproduce** – List the exact steps to reproduce the behavior
- **Expected behavior** – What you expected to happen
- **Actual behavior** – What actually happened
- **Environment details** – OS, Python version, package versions
- **Logs/Screenshots** – If applicable, add logs or screenshots

```bash
# Include the output of:
python --version
uv pip list | grep -E "agentic-fleet|dspy|agent-framework"
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear title** – Describe the enhancement concisely
- **Provide context** – Explain why this enhancement would be useful
- **Describe the solution** – How you envision the feature working
- **Consider alternatives** – Have you considered alternative approaches?

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- [`good first issue`](https://github.com/Qredence/agentic-fleet/labels/good%20first%20issue) – Simple issues for newcomers
- [`help wanted`](https://github.com/Qredence/agentic-fleet/labels/help%20wanted) – Issues that need community help
- [`documentation`](https://github.com/Qredence/agentic-fleet/labels/documentation) – Documentation improvements

### Pull Requests

1. **Fork & Clone**

   ```bash
   git clone https://github.com/YOUR_USERNAME/agentic-fleet.git
   cd agentic-fleet
   ```

2. **Create a Branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

3. **Make Your Changes**
   - Write clear, documented code
   - Add tests for new functionality
   - Update documentation as needed

4. **Run Quality Checks**

   ```bash
   make check    # Lint + type-check
   make test     # Run tests
   make format   # Auto-format code
   ```

5. **Commit Your Changes**

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` – New feature
   - `fix:` – Bug fix
   - `docs:` – Documentation changes
   - `style:` – Formatting (no code change)
   - `refactor:` – Code restructuring
   - `test:` – Adding tests
   - `chore:` – Maintenance tasks

6. **Push & Create PR**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then open a Pull Request on GitHub.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend development)

### Required Secrets (for Maintainers)

If you're a maintainer or running CI workflows locally, ensure these secrets are configured:

| Secret                      | Used By                | Description                                            |
| --------------------------- | ---------------------- | ------------------------------------------------------ |
| `OPENAI_API_KEY`            | Tests, Backend         | OpenAI API access for LLM calls                        |
| `COPILOT_GITHUB_TOKEN`      | CI Doctor, Q workflows | GitHub token with Copilot access for agentic workflows |
| `AZURE_AI_PROJECT_ENDPOINT` | Tests                  | Azure AI endpoint (optional)                           |

> **Note:** Contributors don't need these secrets. CI will skip jobs requiring secrets on external PRs.

### Installation

```bash
# Clone the repository
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Verify installation
agentic-fleet --help
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/workflows/test_supervisor.py -v

# Run with coverage
uv run pytest --cov=src/agentic_fleet --cov-report=html
```

### CI/CD Workflows

GitHub Actions workflows handle automated testing and quality checks:

**Main CI Pipeline (`.github/workflows/ci.yml`)**:

- **Quality**: Runs linting, type checking, and security scanning in parallel
  - Ruff formatter and linter
  - `ty` type checker
  - Bandit security scan (optional, uploads report on failure)
- **Test**: Matrix testing across Python versions (3.12, 3.13) and OS (Linux, macOS)
- **Frontend**: Vitest unit tests for React frontend
- **Build**: Verifies package buildability (runs after all checks pass)

**Auxiliary Workflows**:

- `codeql.yml` - Security analysis (weekly schedule + manual trigger)
- `dependency-review.yml` - Dependency vulnerability checks (manual trigger, non-blocking)
- `docs-sync.aw.md` - Auto-doc generation (manual trigger)

**Removed Workflows** (consolidated or deprecated):

- `label-sync.yml` - No longer needed (labels managed manually)
- `stale.yml` - Removed to reduce noise
- `agentic-workflows.yml` - Merged into main CI pipeline

> **Note**: External contributors can open PRs without secrets. CI will skip jobs requiring secrets automatically.

### Running the Dev Server

```bash
# Backend + Frontend
make dev

# Backend only
make backend

# Frontend only (requires backend running)
make frontend-dev
```

## Style Guidelines

### Python Code Style

We use **Ruff** for linting and formatting:

```bash
# Format code
make format

# Check linting
make lint
```

**Key conventions:**

- **Line length**: 100 characters
- **Imports**: Sorted with isort (via Ruff)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for public APIs

```python
def process_task(task: str, timeout: int = 30) -> dict[str, Any]:
    """Process a task through the workflow pipeline.

    Args:
        task: The task description to process.
        timeout: Maximum time in seconds. Defaults to 30.

    Returns:
        Dictionary containing the result and metadata.

    Raises:
        TaskError: If the task cannot be processed.
    """
    ...
```

### Type Checking

We use **ty** for type checking:

```bash
make type-check
```

### Frontend Code Style

- **TypeScript** with strict mode
- **ESLint** + **Prettier** for formatting
- **React** functional components with hooks

```bash
cd src/frontend
npm run lint
npm run format
```

## Project Structure

```
src/agentic_fleet/
├── agents/           # Agent definitions & AgentFactory
├── workflows/        # Orchestration logic
├── dspy_modules/     # DSPy signatures & typed models
├── tools/            # Tool implementations
├── app/              # FastAPI backend
├── cli/              # CLI commands
├── config/           # Configuration (YAML)
└── utils/            # Shared utilities

src/frontend/         # React/Vite frontend
tests/                # Test files (mirror src structure)
docs/                 # Documentation
```

## Adding New Features

### Adding a New Agent

1. Add configuration in `src/agentic_fleet/config/workflow_config.yaml`:

   ```yaml
   agents:
     your_agent:
       model: gpt-4o
       tools: [TavilyMCPTool]
       temperature: 0.5
   ```

2. Update `agents/coordinator.py` to instantiate the agent
3. Add training examples in `data/supervisor_examples.json`

### Adding a New Tool

1. Create tool in `src/agentic_fleet/tools/your_tool.py`
2. Implement the tool protocol
3. Register in the ToolRegistry (automatic via decorators)
4. Add to agent config to enable

### Adding a DSPy Signature

1. Define in `src/agentic_fleet/dspy_modules/signatures.py`
2. Add typed output model in `typed_models.py` (if needed)
3. Wire up in `reasoner.py`

## Documentation

- Update `README.md` for user-facing changes
- Update architecture docs for structural changes
- Add docstrings to all public functions/classes
- Include code examples where helpful

## Getting Help

- 💬 [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions) – Ask questions
- 🐛 [GitHub Issues](https://github.com/Qredence/agentic-fleet/issues) – Report bugs
- 📖 [Documentation](docs/) – Read the docs

## Recognition

Contributors are recognized in:

- The [Contributors](https://github.com/Qredence/agentic-fleet/graphs/contributors) page
- Release notes for significant contributions
- Our README acknowledgments section

---

Thank you for contributing to AgenticFleet! 🚀
