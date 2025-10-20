# Installation Guide

This guide walks you through installing AgenticFleet on your system.

---

## System Requirements

### Minimum Requirements

- **Python:** 3.12 or higher
- **Operating System:** Linux, macOS, or Windows (WSL2 recommended)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 2GB for dependencies and caches

### Required Software

1. **Python 3.12+**
   ```bash
   python --version  # Should show 3.12 or higher
   ```

2. **uv Package Manager**

   AgenticFleet uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management.

   **Install uv:**
   ```bash
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Verify installation:
   ```bash
   uv --version
   ```

3. **Git** (for cloning the repository)
   ```bash
   git --version
   ```

### API Keys

AgenticFleet requires an OpenAI API key. Optional services may need additional keys.

- **Required:** [OpenAI API Key](https://platform.openai.com/api-keys)
- **Optional:** Azure OpenAI credentials (for Mem0 memory)
- **Optional:** Azure AI Search (for vector storage)

---

## Installation Methods

### Method 1: From Source (Recommended)

Best for development and customization.

```bash
# 1. Clone the repository
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# 2. Install dependencies
make install
# Or manually: uv sync --all-extras

# 3. Verify installation
uv run fleet --version
```

### Method 2: Using uv

Install as a Python package with uv.

```bash
# Install from PyPI (when published)
uv pip install agentic-fleet

# Or install from Git repository
uv pip install git+https://github.com/Qredence/agentic-fleet.git
```

### Method 3: Development Installation

For contributing to AgenticFleet.

```bash
# 1. Clone and navigate
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# 2. Install in editable mode with dev dependencies
uv sync --all-extras

# 3. Install pre-commit hooks
uv run pre-commit install

# 4. Run tests to verify
make test
```

---

## Configuration

### 1. Environment Variables

Create your environment configuration file:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-...

# Optional: Model Configuration
OPENAI_MODEL=gpt-4o
OPENAI_RESPONSES_MODEL_ID=gpt-5-codex

# Optional: Azure OpenAI (for Mem0)
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_SEARCH_ENDPOINT=https://...
AZURE_AI_SEARCH_KEY=...
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME=text-embedding-ada-002

# Optional: Observability
ENABLE_OTEL=false
OTLP_ENDPOINT=http://localhost:4317

# Optional: Mem0 Memory
MEM0_HISTORY_DB_PATH=./var/mem0.db
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional: Logging
LOG_LEVEL=INFO
```

### 2. Verify Configuration

Run the configuration test:

```bash
make test-config
# Or: uv run python tests/test_config.py
```

This validates:
- Environment variables are set correctly
- Agent configurations are valid
- All required dependencies are installed
- Tool imports work properly

---

## First Run

### Interactive CLI

Launch the interactive command-line interface:

```bash
# Using make
make run

# Using uv
uv run fleet

# Direct invocation
uv run python -m agenticfleet
```

You should see:

```
╔══════════════════════════════════════════════════════════════════╗
║                         AgenticFleet v0.5.3                      ║
║                   Multi-Agent Orchestration                      ║
╚══════════════════════════════════════════════════════════════════╝

Type 'help' for commands or Ctrl+C to exit.

fleet> _
```

### Quick Test

Try a simple task:

```
fleet> What is 2 + 2? Be concise.
```

The system should:
1. Create a plan
2. Delegate to an agent
3. Return the result

---

## Troubleshooting

### Common Issues

#### 1. Python Version Too Old

**Error:** `Python 3.12+ required`

**Solution:**
```bash
# Check version
python --version

# Install Python 3.12+ using pyenv
pyenv install 3.12
pyenv global 3.12
```

#### 2. uv Not Found

**Error:** `command not found: uv`

**Solution:**
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (Linux/macOS)
export PATH="$HOME/.cargo/bin:$PATH"

# Restart shell
exec $SHELL
```

#### 3. OpenAI API Key Not Set

**Error:** `OpenAI API key not found`

**Solution:**
```bash
# Check if .env exists
cat .env

# Ensure OPENAI_API_KEY is set
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

#### 4. Import Errors

**Error:** `ModuleNotFoundError: No module named 'agenticfleet'`

**Solution:**
```bash
# Reinstall dependencies
uv sync --all-extras

# Verify installation
uv run python -c "import agenticfleet; print(agenticfleet.__version__)"
```

#### 5. Permission Errors

**Error:** `Permission denied` when creating checkpoints

**Solution:**
```bash
# Create necessary directories
mkdir -p var/checkpoints var/logs

# Fix permissions
chmod 755 var/checkpoints var/logs
```

### Getting Help

If you encounter issues:

1. **Check logs:** `cat logs/agenticfleet.log`
2. **Run diagnostics:** `make test-config`
3. **Search issues:** [GitHub Issues](https://github.com/Qredence/agentic-fleet/issues)
4. **Ask for help:** [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions)

---

## Next Steps

Now that you have AgenticFleet installed:

1. **[Quick Start Guide](quickstart.md)** – Run your first workflow
2. **[Configuration Guide](configuration.md)** – Customize agents and workflows
3. **[Working with Agents](../guides/agents.md)** – Understand the specialist agents
4. **[Command Reference](command-reference.md)** – Learn all available commands

---

## Uninstallation

To remove AgenticFleet:

```bash
# Remove the repository
cd ..
rm -rf agentic-fleet

# Remove uv cache (optional)
rm -rf ~/.cache/uv

# Remove Python virtual environments (optional)
rm -rf ~/.local/share/uv/python
```

---

**Need help?** Contact us at <contact@qredence.ai> or [open an issue](https://github.com/Qredence/agentic-fleet/issues).
