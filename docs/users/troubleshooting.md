# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Problem: "ModuleNotFoundError: No module named 'src'"

**Symptoms**:

```
Traceback (most recent call last):
  File "console.py", line 24, in <module>
    from src.agentic_fleet.dspy_modules.supervisor import DSPySupervisor
ModuleNotFoundError: No module named 'src'
```

**Solution**:

```bash
# Reinstall the package in editable mode using uv
uv pip install -e .
```

**Explanation**: The package uses `package_dir={"": "src"}` which makes packages inside `src/` available at the top level. After structural changes, reinstallation is required.

---

#### Problem: "command not found: uv"

**Solution**:

```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip as fallback
pip install -e .
```

---

#### Problem: "OPENAI_API_KEY not found"

**Solution**:

1. Create `.env` file in project root:

```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

2. Or export directly:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

---

### Testing Issues

#### Problem: "unrecognized arguments: --cov"

**Symptoms**:

```
pytest: error: unrecognized arguments: --cov=src
```

**Solution**:

```bash
# Install pytest-cov
uv pip install pytest-cov

# Or run without coverage
uv run pytest -q tests/
```

---

#### Problem: "ModuleNotFoundError" when running tests

**Solution**:

```bash
# Set PYTHONPATH for proper module resolution
PYTHONPATH=. uv run pytest -q tests/
```

---

#### Problem: "ChatAgent stub should not be used directly in tests"

**Solution**: Use `DummyAgent` from test files instead:

```python
from tests.workflows.test_supervisor_workflow import DummyAgent

workflow.agents = {"Writer": DummyAgent("Writer")}
```

---

### Runtime Issues

#### Problem: "TAVILY_API_KEY not set - Researcher will operate without web search"

**Impact**: Researcher agent cannot perform web searches.

**Solution**:

1. Get free API key: https://tavily.com
2. Add to `.env`:

```bash
echo "TAVILY_API_KEY=tvly-your-key" >> .env
```

**Note**: This is a warning, not an error. The system will work but Researcher won't have web search capability.

---

#### Problem: "Failed to save execution history"

**Symptoms**:

```
HistoryError: Failed to save execution history
```

**Solutions**:

1. Check permissions on `logs/` directory
2. Ensure disk space available
3. Check file is not locked by another process

```bash
# Fix permissions
chmod 755 logs/
```

---

#### Problem: "Cache invalidated, recompiling..."

**Explanation**: Normal behavior when training examples are updated.

**To force cache use**:

```python
workflow = await create_supervisor_workflow(compile_dspy=False)
```

**To clear cache**:

```python
from src.agentic_fleet.utils.compiler import clear_cache
clear_cache()
```

---

### Performance Issues

#### Problem: Slow startup time

**Solutions**:

1. Skip DSPy compilation:

```bash
uv run agentic-fleet run -m "Task" --no-compile
```

2. Use cached compiled module (automatic after first run)

3. Use faster model:

```yaml
# config/workflow_config.yaml
dspy:
  model: gpt-5-mini # Faster than gpt-4.1
```

---

#### Problem: High API costs

**Solutions**:

1. Use cheaper models:

```yaml
dspy:
  model: gpt-5-mini

agents:
  writer:
    model: gpt-5-mini
  reviewer:
    model: gpt-5-mini
```

2. Reduce temperature (fewer tokens):

```yaml
agents:
  researcher:
    temperature: 0.3 # Lower = more deterministic
```

3. Disable pre-analysis tool usage:

```yaml
tools:
  pre_analysis_tool_usage: false
```

---

### Configuration Issues

#### Problem: "Invalid configuration"

**Symptoms**:

```
ConfigurationError: Invalid configuration: ...
```

**Solutions**:

1. Check YAML syntax:

```bash
python3 -c "import yaml; yaml.safe_load(open('config/workflow_config.yaml'))"
```

2. Validate configuration:

```python
from src.agentic_fleet.utils.config_schema import validate_config
from src.agentic_fleet.utils.config_loader import load_config

config = load_config()
validated = validate_config(config)
```

3. Check for typos in field names

---

#### Problem: Temperature out of range

**Symptoms**:

```
ValueError: temperature must be between 0.0 and 2.0
```

**Solution**: Update config:

```yaml
dspy:
  temperature: 0.7 # Must be 0.0-2.0
```

Verify:

```bash
uv run python -c "from src.agentic_fleet.utils.config_schema import validate_config; from src.agentic_fleet.utils.config_loader import load_config; validate_config(load_config())"
```

---

### Import Issues

#### Problem: "cannot import name 'X' from 'src.module'"

**Solution**: After package installation, imports should use top-level package names:

**Incorrect**:

```python
from src.agentic_fleet.workflows import SupervisorWorkflow  # ❌
```

**Correct**:

```python
from agentic_fleet.workflows.supervisor import SupervisorWorkflow  # ✅
```

**For console.py and examples** (not installed as package):

```python
from src.agentic_fleet.workflows.supervisor import SupervisorWorkflow  # ✅
```

---

## Debugging Tips

### Enable Debug Logging

```python
from src.agentic_fleet.utils.logger import setup_logger

setup_logger("dspy_agent_framework", "DEBUG")
```

### Check System State

```python
# View tool registry
print(workflow.tool_registry.get_available_tools())

# View execution history
from src.agentic_fleet.utils.history_manager import HistoryManager
manager = HistoryManager()
stats = manager.get_history_stats()
print(stats)

# View cache info
from src.agentic_fleet.utils.compiler import get_cache_info
info = get_cache_info()
print(info)
```

### Validate Training Examples

```bash
# Check JSON is valid
uv run python -c "import json; data = json.load(open('data/supervisor_examples.json')); print(f'{len(data)} examples loaded')"
```

### Test Individual Components

```bash
# Test DSPy supervisor
uv run python -c "from agentic_fleet.dspy_modules.supervisor import DSPySupervisor; s = DSPySupervisor(); print('Supervisor OK')"

# Test tool registry
uv run python -c "from agentic_fleet.utils.tool_registry import ToolRegistry; r = ToolRegistry(); print('Registry OK')"
```

## Getting Additional Help

1. **Check Documentation**:
   - [User Guide](user-guide.md) - User documentation
   - [API Reference](../developers/api-reference.md) - API details
   - [Configuration](configuration.md) - Config options

2. **View Logs**:
   - `logs/workflow.log` - Detailed execution logs
   - `logs/execution_history.jsonl` - Structured history

3. **Run with Verbose**:

   ```bash
   uv run agentic-fleet run -m "Your task" --verbose
   uv run agentic-fleet run -m "Task" --verbose
   ```

4. **Check Tests**:

   ```bash
   PYTHONPATH=. uv run pytest -v tests/
   ```

5. **Open GitHub Issue**: Include:
   - Error message
   - Configuration (sanitized, no API keys)
   - Python version: `python3 --version`
   - Installed packages: `uv pip list`
