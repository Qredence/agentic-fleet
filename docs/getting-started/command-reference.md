# AgenticFleet Command Reference

⚠️ **CRITICAL**: Always prefix Python commands with `uv run`

## 📦 Installation & Setup

| Task | Command |
|------|---------|
| Sync dependencies | `uv sync` |
| Install in dev mode | `uv pip install -e ".[dev]"` |
| Add new dependency | `uv add package-name` |
| Add dev dependency | `uv add --dev package-name` |

## 🚀 Running the Application

| Method | Command |
|--------|---------|
| Console script | `uv run agentic-fleet` |
| Module execution | `uv run python -m agenticfleet` |
| Programmatic | See examples below |
| HITL demo | `make demo-hitl` |

### Programmatic Usage

```python
# In your Python script
from agenticfleet import create_default_fleet

workflow = create_default_fleet()
result = await workflow.run("Your task here")
```

Then run:

```bash
uv run python your_script.py
```

## 🧪 Testing

| Task | Command |
|------|---------|
| Run all tests | `uv run pytest` |
| Run specific file | `uv run pytest tests/unit/test_agents/test_orchestrator.py` |
| Run with name filter | `uv run pytest -k "test_orchestrator"` |
| Run with coverage | `uv run pytest --cov=agenticfleet --cov-report=html` |
| Run verbose | `uv run pytest -v` |

## 🎨 Code Quality

| Task | Command |
|------|---------|
| Format code | `uv run black .` |
| Format specific dirs | `uv run black src/ tests/` |
| Check formatting | `uv run black . --check` |
| Lint code | `uv run ruff check .` |
| Auto-fix linting | `uv run ruff check --fix .` |
| Type check | `uv run mypy src/agenticfleet` |

## ✅ Pre-Commit Checklist

Run these before committing:

```bash
uv run black .
uv run ruff check --fix .
uv run mypy src/agenticfleet
uv run pytest
```

Or use pre-commit hooks:

```bash
uv run pre-commit run --all-files
```

## 🔍 Validation & Debugging

| Task | Command |
|------|---------|
| Validate config | `uv run python tests/test_config.py` |
| Test agent creation | `uv run python -c "from agenticfleet.agents import create_orchestrator_agent; create_orchestrator_agent()"` |
| Check version | `uv run python -c "from agenticfleet import __version__; print(__version__)"` |
| List packages | `uv pip list` |
| Show dep tree | `uv pip tree` |

## 🧹 Maintenance

| Task | Command |
|------|---------|
| Clean cache files | `find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null` |
| Clean .pyc files | `find . -type f -name "*.pyc" -delete` |
| Update dependencies | `uv sync --upgrade` |
| Lock dependencies | `uv lock` |

## 🐍 Python Environment

| Task | Command |
|------|---------|
| Show Python version | `uv python list` |
| Create venv | `uv venv` (done automatically by uv) |
| Activate venv manually | `source .venv/bin/activate` (macOS/Linux) |
| Check installed packages | `uv pip list` |

## 📝 Development Workflows

### Adding a New Feature

```bash
# 1. Create a new branch
git checkout -b feature/your-feature

# 2. Make changes to code

# 3. Install any new dependencies
uv add new-package

# 4. Run tests to ensure nothing broke
uv run pytest

# 5. Format and lint
uv run black .
uv run ruff check --fix .
uv run mypy src/agenticfleet

# 6. Commit changes
git add .
git commit -m "Add: Your feature description"
```

### Debugging Agent Issues

```bash
# Test specific agent
uv run python -c "
from agenticfleet.agents import create_researcher_agent
agent = create_researcher_agent()
print(f'Agent: {agent.name}')
print(f'Tools: {len(agent.tools)} tools')
"

# Check agent config
uv run python -c "
from agenticfleet.config import settings
cfg = settings.load_agent_config('orchestrator')
print(cfg)
"
```

### Running Interactive Python Shell

```bash
# Standard Python REPL with project context
uv run python

# Then in Python:
>>> from agenticfleet.agents import *
>>> agent = create_orchestrator_agent()
>>> print(agent.name)
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `uv sync` |
| Stale cache | `find . -type d -name "__pycache__" -exec rm -rf {} +` |
| Type errors | `uv run mypy --install-types` |
| Dependency conflicts | `uv sync --reinstall` |
| Python version issues | Check `uv python list` and `.python-version` |

## 📚 Quick Examples

### Test a Simple Query

```bash
uv run python -c "
import asyncio
from agenticfleet.fleet import create_default_fleet

async def test():
    fleet = create_default_fleet()
    result = await fleet.run('What is 2+2?')
    print(result)

asyncio.run(test())
"
```

### Check All Agents Initialize

```bash
uv run python -c "
from agenticfleet.agents import (
    create_orchestrator_agent,
    create_researcher_agent,
    create_coder_agent,
    create_analyst_agent,
)

o = create_orchestrator_agent()
r = create_researcher_agent()
c = create_coder_agent()
a = create_analyst_agent()

print(f'✅ All agents created: {o.name}, {r.name}, {c.name}, {a.name}')
"
```

## 🚫 Common Mistakes to Avoid

### ❌ DON'T DO THIS

```bash
python main.py                  # Wrong: Uses system Python
pip install package             # Wrong: Wrong environment
pytest                          # Wrong: May test wrong code
python -m pytest                # Wrong: System Python
```

### ✅ DO THIS INSTEAD

```bash
uv run python -m agenticfleet   # Correct: Project Python
uv add package                  # Correct: Project environment
uv run pytest                   # Correct: Tests installed package
uv run python -m pytest         # Correct: Project Python
```

## 📖 Additional Resources

- **Main Documentation**: `README.md`
- **Architecture**: `docs/overview/implementation-summary.md`
- **Migration Guide**: `docs/migrations/src-layout-migration.md`
- **Quick Reference**: `docs/getting-started/quick-reference.md`
- **GitHub Copilot Instructions**: `.github/copilot-instructions.md`

---

**Remember**: When in doubt, prefix with `uv run` ✨
