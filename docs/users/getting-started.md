# Getting Started

## Prerequisites

- **Python**: 3.10 or higher (3.11+ recommended)
- **pip** or **uv**: Package installer (uv recommended for faster installation)
- **Git**: For cloning the repository
- **API Keys**:
  - OpenAI API key (required)
  - Tavily API key (optional but recommended for web search)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Zochory/dspy-agent-framework.git
cd dspy-agent-framework
```

### Step 2: Create Virtual Environment

#### Using uv (recommended - faster)

```bash
uv python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Using venv (standard)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

#### Method 1: Using uv (recommended)

```bash
uv pip install -r requirements.txt
uv pip install -e .
```

#### Method 2: Using pip (alternative)

```bash
pip install -r requirements.txt
pip install -e .
```

**Recommended**: Use `uv` for faster dependency resolution and installation.

### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here

# Optional but recommended for web search
TAVILY_API_KEY=tvly-your-tavily-key-here
```

**Getting API Keys**:

- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://tavily.com (free tier available)

### Step 5: Verify Installation

```bash
# Check CLI command
uv run python console.py --help

# Run tests
PYTHONPATH=. uv run pytest -q tests/
```

You should see:

- CLI help message with commands
- All tests passing

## Quick Start

### Using the CLI

The command-line interface for interacting with the framework:

```bash
# Basic usage
uv run python console.py run -m "Your question here"

# With verbose logging (see all DSPy decisions)
uv run python console.py run -m "Your question here" --verbose

# Save output to file
uv run python console.py run -m "Your question here" --verbose 2>&1 | tee logs/output.log
```

### Programmatic Usage

Integrate into your Python applications:

```python
from src.workflows import create_supervisor_workflow
import asyncio

async def main():
    # Create and initialize workflow
    workflow = await create_supervisor_workflow(compile_dspy=True)

    # Execute a task
    result = await workflow.run("Analyze the impact of AI on software development")

    # Access results
    print(f"Result: {result['result']}")
    print(f"Quality Score: {result['quality']['score']}/10")
    print(f"Routing: {result['routing']['mode']} to {result['routing']['assigned_to']}")

asyncio.run(main())
```

## Post-Installation

### Clear Cache (First Run)

```bash
# Clear any existing cache
uv run python -c "from src.utils.compiler import clear_cache; clear_cache()"
```

### Verify Configuration

```bash
# Check configuration loads correctly
uv run python -c "from src.utils.config_loader import load_config; print(load_config())"
```

### Run First Task

```bash
uv run python console.py run -m "Write a haiku about code quality"
```

## Installation Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution**:

```bash
# Install in editable mode
uv pip install -e .

# For running tests
PYTHONPATH=. uv run pytest tests/
```

### Issue: "command not found: uv"

**Solution**:

```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip as fallback
pip install -e .
```

### Issue: "No module named 'dspy'"

**Solution**:

```bash
# Install requirements first
uv pip install -r requirements.txt
```

## Development Installation

For development, install additional tools:

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Or install dev tools separately
uv pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

## Upgrading

To upgrade to a new version:

```bash
# Pull latest changes
git pull origin main

# Reinstall dependencies
uv pip install -r requirements.txt
uv pip install -e .

# Clear cache to force recompilation
uv run python -c "from src.utils.compiler import clear_cache; clear_cache()"
```

## Uninstallation

```bash
# Remove package
uv pip uninstall dspy-agent-framework

# Remove virtual environment
deactivate
rm -rf venv

# Remove logs and cache (optional)
rm -rf logs/ htmlcov/ .pytest_cache/
```

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

ENV OPENAI_API_KEY=""
ENV TAVILY_API_KEY=""

CMD ["python", "console.py", "run", "-m", "Your task here"]
```

Build and run:

```bash
docker build -t dspy-agent-framework .
docker run -it --env-file .env dspy-agent-framework
```

**Note**: The Docker image uses `uv` for faster dependency installation.

## Next Steps

After installation:

1. Read [User Guide](user-guide.md) for complete usage instructions
2. Review [Configuration](configuration.md) for configuration options
3. Try examples in `examples/` directory
4. See [Troubleshooting](troubleshooting.md) if you encounter issues

## Support

If you encounter issues:

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Ensure Python 3.10+ is installed: `python3 --version`
3. Verify dependencies: `uv pip list | grep dspy`
4. Run tests: `PYTHONPATH=. uv run pytest tests/`
5. Open a GitHub issue with error details
