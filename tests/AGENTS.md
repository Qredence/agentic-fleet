# AGENTS.md - Testing

> **Agent instructions for working with the AgenticFleet test suite**

This file provides guidance for AI coding agents working specifically within the `tests/` directory. For general project instructions, see the [root AGENTS.md](../AGENTS.md).

---

## Test Suite Overview

The AgenticFleet test suite covers unit tests, integration tests, configuration validation, and end-to-end tests. All tests use **pytest** and **pytest-asyncio** for async test support.

### Testing Philosophy

- **Focused testing**: Run only related tests, not the entire suite
- **Fast feedback**: Use pytest markers and filters to run specific tests
- **Mock external calls**: Avoid real API calls in unit tests
- **Configuration validation**: Always validate config after changes
- **Type safety**: Tests should be fully typed

---

## Test Organization

```
tests/
├── __init__.py                    # Test package marker
├── conftest.py                    # Shared fixtures
├── test_config.py                 # Configuration validation (CRITICAL)
├── test_configuration.py          # Additional config tests
├── test_magentic_fleet.py         # Core orchestration tests (14 tests)
├── test_approval_manager.py       # HITL approval tests
├── test_checkpoints.py            # Checkpoint storage tests
├── test_cli_ui.py                 # CLI/REPL UI tests
├── test_code_types.py             # Pydantic model tests
├── test_haxui_api.py              # FastAPI endpoint tests
├── test_hitl.py                   # HITL integration tests
├── test_hitl_manual.py            # Manual HITL testing
├── test_mem0_context_provider.py  # Memory provider tests
├── test_reflection_endpoint.py    # Reflection workflow API tests
├── test_workflow_as_agent_api.py  # Workflow-as-agent tests
├── test_hello.py                  # Basic sanity test
├── TESTING-NEXT-STEPS.md          # Testing roadmap
└── e2e/                           # End-to-end tests (Playwright)
```

---

## Running Tests

### Critical Commands

```bash
# ALWAYS run this after config changes (YAML or agent factories)
uv run python tests/test_config.py

# Run all tests (use sparingly—expensive)
uv run pytest -v

# Run specific test file (PREFERRED)
uv run pytest tests/test_magentic_fleet.py -v

# Run specific test function
uv run pytest tests/test_config.py::test_researcher_agent -v

# Run tests matching pattern
uv run pytest tests/test_magentic_fleet.py -k "orchestrator" -v

# Run with verbose output and short traceback
uv run pytest tests/test_config.py -vv --tb=short

# Run with coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Or use make shortcuts
make test              # All tests
make test-config       # Configuration validation only
```

### Test Discovery

pytest discovers tests by:

1. Files matching `test_*.py` or `*_test.py`
2. Classes prefixed with `Test`
3. Functions prefixed with `test_`

---

## Test Configuration

### pytest.ini

```ini
[pytest]
pythonpath = src
asyncio_mode = auto
```

- `pythonpath = src`: Allows importing from `agenticfleet` package
- `asyncio_mode = auto`: Automatic async test detection (no `@pytest.mark.asyncio` needed)

### conftest.py

Shared fixtures live in `conftest.py`:

```python
import pytest
from agenticfleet.config.settings import Settings

@pytest.fixture
def settings() -> Settings:
    """Provide Settings instance for tests."""
    return Settings()

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client to avoid API calls."""
    from unittest.mock import MagicMock
    return MagicMock()
```

---

## Test Patterns

### Unit Test Structure

```python
import pytest
from agenticfleet.core.code_types import CodeExecutionResult

def test_code_execution_result_success():
    """Test successful code execution result."""
    result = CodeExecutionResult(
        success=True,
        output="Hello, World!",
        error=None
    )

    assert result.success is True
    assert result.output == "Hello, World!"
    assert result.error is None
```

### Async Test Pattern

```python
# NO @pytest.mark.asyncio needed (asyncio_mode = auto)
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

### Mocking OpenAI Client

```python
from unittest.mock import MagicMock, AsyncMock
from agent_framework_azure_ai import OpenAIResponsesClient

def test_agent_creation():
    """Test agent factory with mocked client."""
    mock_client = MagicMock(spec=OpenAIResponsesClient)
    mock_client.create_response = AsyncMock(return_value=mock_response)

    # Test agent creation with mock
    agent = create_agent(client=mock_client)
    assert agent is not None
```

### Configuration Validation Pattern

```python
from agenticfleet.config.settings import Settings

def test_researcher_agent_config():
    """Validate researcher agent configuration."""
    settings = Settings()
    config = settings.load_agent_config("researcher")

    # Required fields
    assert config["name"] is not None
    assert config["model"] is not None
    assert "system_prompt" in config

    # Tools configuration
    assert "tools" in config
    assert isinstance(config["tools"], list)

    # Runtime flags
    assert "runtime" in config
    assert config["runtime"]["stream"] is True
```

### Testing Checkpoints

```python
from agent_framework import InMemoryCheckpointStorage

def test_checkpoint_save_restore():
    """Test checkpoint save and restore."""
    storage = InMemoryCheckpointStorage()

    # Save checkpoint
    checkpoint_id = storage.save(state)

    # Restore checkpoint
    restored_state = storage.load(checkpoint_id)

    assert restored_state == state
```

---

## Critical Test Files

### test_config.py (MOST IMPORTANT)

**Purpose**: Validates all agent configurations, tool imports, and factory functions.

**When to run**: ALWAYS after:

- Changing YAML configuration files
- Adding/modifying agent factories
- Adding/removing tools
- Changing environment variables

```bash
uv run python tests/test_config.py
```

**What it validates**:

- Environment variables are set
- Agent config files exist and are valid
- All tools can be imported
- Agent factories are callable
- Workflow config is valid
- Fleet can be imported and instantiated

### test_magentic_fleet.py (14 Core Tests)

**Purpose**: Tests core orchestration logic and Magentic workflow.

**Key test areas**:

- Fleet creation and agent registration
- Manager agent configuration
- Callback system wiring
- Checkpoint integration
- Workflow execution

```bash
# Run all orchestration tests
uv run pytest tests/test_magentic_fleet.py -v

# Run specific test
uv run pytest tests/test_magentic_fleet.py::test_fleet_builder_with_agents -v
```

### test_haxui_api.py

**Purpose**: Tests FastAPI web endpoints.

**Key test areas**:

- Health endpoint
- SSE streaming endpoint (`/v1/responses`)
- Conversation listing
- Error handling

```bash
uv run pytest tests/test_haxui_api.py -v
```

### test_reflection_endpoint.py

**Purpose**: Tests Worker/Reviewer reflection workflow API.

**Key test areas**:

- Reflection endpoint (`/v1/workflow/reflection`)
- SSE event streaming
- Worker/Reviewer interaction
- Approval integration

```bash
uv run pytest tests/test_reflection_endpoint.py -v
```

---

## Mocking Strategies

### Mocking LLM Clients

```python
from unittest.mock import MagicMock, AsyncMock
from agent_framework_azure_ai import OpenAIResponsesClient

# Basic mock
mock_client = MagicMock(spec=OpenAIResponsesClient)

# Mock async method
mock_client.create_response = AsyncMock(return_value={
    "choices": [{"message": {"content": "Test response"}}]
})

# Use in test
result = await mock_client.create_response(messages=[...])
```

### Mocking Settings

```python
from unittest.mock import patch

@patch('agenticfleet.config.settings.Settings')
def test_with_mock_settings(mock_settings_class):
    """Test with mocked settings."""
    mock_settings = mock_settings_class.return_value
    mock_settings.openai_api_key = "test-key"

    # Test code that uses settings
    ...
```

### Mocking File Operations

```python
from unittest.mock import patch, mock_open

@patch('builtins.open', mock_open(read_data='test data'))
def test_file_reading():
    """Test file reading with mock."""
    with open('test.txt', 'r') as f:
        data = f.read()
    assert data == 'test data'
```

---

## Fixtures

### Common Fixtures in conftest.py

```python
import pytest
from agenticfleet.config.settings import Settings
from agent_framework import InMemoryCheckpointStorage

@pytest.fixture
def settings() -> Settings:
    """Provide Settings instance."""
    return Settings()

@pytest.fixture
def checkpoint_storage() -> InMemoryCheckpointStorage:
    """Provide in-memory checkpoint storage."""
    return InMemoryCheckpointStorage()

@pytest.fixture
def mock_approval_handler():
    """Mock approval handler for HITL tests."""
    from unittest.mock import AsyncMock
    handler = AsyncMock()
    handler.request_approval = AsyncMock()
    return handler
```

### Using Fixtures

```python
def test_with_settings(settings):
    """Test that uses settings fixture."""
    assert settings.openai_api_key is not None

def test_with_storage(checkpoint_storage):
    """Test that uses checkpoint storage fixture."""
    checkpoint_storage.save({"state": "test"})
    assert len(checkpoint_storage.list()) == 1
```

---

## End-to-End Tests

### Playwright Tests (tests/e2e/)

**Purpose**: Browser-based UI testing for frontend.

**Requirements**:

- Backend must be running (`make haxui-server`)
- Frontend must be running (`make frontend-dev`)

```bash
# Run E2E tests
make test-e2e
# Or: uv run python tests/e2e/playwright_test_workflow.py
```

**E2E test structure**:

```python
from playwright.sync_api import Page, expect

def test_chat_interface(page: Page):
    """Test chat interface workflow."""
    # Navigate to app
    page.goto("http://localhost:5173")

    # Enter message
    page.fill('textarea[placeholder="Type a message..."]', "Hello")
    page.click('button[type="submit"]')

    # Wait for response
    expect(page.locator('.message-assistant')).to_be_visible()
```

---

## Test Data and Fixtures

### Test Data Location

- Mock data: Inline in test files or `tests/.tmp/` (gitignored)
- Fixtures: `tests/conftest.py`
- Config samples: Use actual config files from `src/agenticfleet/config/`

### Environment Variables for Tests

Tests use environment variables from `.env` file. For CI, secrets are stored in GitHub Actions.

**Required for tests**:

- `OPENAI_API_KEY` (or mock it)
- Optional: Azure credentials for integration tests

---

## Writing New Tests

### Step-by-Step

1. **Identify test type**: Unit, integration, E2E?
2. **Create test file**: `test_<module>.py`
3. **Import dependencies**:
   ```python
   import pytest
   from agenticfleet.<module> import <function>
   ```
4. **Write test function**:
   ```python
   def test_<feature>():
       """Test description."""
       result = function_under_test()
       assert result == expected_value
   ```
5. **Mock external calls**:
   ```python
   from unittest.mock import MagicMock
   mock_client = MagicMock()
   ```
6. **Run test**:
   ```bash
   uv run pytest tests/test_<module>.py::test_<feature> -v
   ```

### Test Naming Conventions

- **Test files**: `test_<module>.py`
- **Test functions**: `test_<feature>_<scenario>()`
- **Test classes**: `Test<Module>`

```python
# ✅ GOOD
def test_agent_creation_with_valid_config():
    """Test agent creation with valid configuration."""
    ...

# ❌ BAD
def test1():
    ...
```

---

## Common Test Scenarios

### Testing Agent Factories

```python
from agenticfleet.agents import create_researcher_agent

def test_create_researcher_agent():
    """Test researcher agent factory."""
    agent = create_researcher_agent()

    assert agent is not None
    assert agent.name == "Researcher Agent"
    assert len(agent.tools) > 0
```

### Testing Tool Functions

```python
from agenticfleet.agents.researcher.tools.web_search import web_search_tool

def test_web_search_tool():
    """Test web search tool returns valid response."""
    result = web_search_tool(query="Python testing", limit=5)

    assert result.success is True
    assert len(result.results) <= 5
    assert result.error is None
```

### Testing API Endpoints

```python
from fastapi.testclient import TestClient
from agenticfleet.haxui.api import app

def test_health_endpoint():
    """Test health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert "status" in response.json()
```

### Testing Async Functions

```python
async def test_async_workflow():
    """Test async workflow execution."""
    from agenticfleet.fleet.magentic_fleet import MagenticFleet

    fleet = MagenticFleet()
    result = await fleet.run("Test task")

    assert result is not None
```

---

## Debugging Tests

### Verbose Output

```bash
# Show print statements and full traceback
uv run pytest tests/test_config.py -vv -s
```

### Run Single Test

```bash
# Run one specific test
uv run pytest tests/test_config.py::test_researcher_agent -vv
```

### Use pytest --pdb

```bash
# Drop into debugger on failure
uv run pytest tests/test_config.py --pdb
```

### Print Debugging

```python
def test_debug():
    """Test with debug output."""
    result = function()
    print(f"Debug: result={result}")  # Will show with -s flag
    assert result is not None
```

---

## CI/CD Testing

### GitHub Actions Workflow

Tests run automatically in CI via `.github/workflows/ci.yml`:

1. **Lint & format checks** (Ruff, Black)
2. **Type checking** (mypy, continues on error)
3. **Tests** (Python 3.12 & 3.13, Ubuntu/macOS/Windows)
4. **Package build** verification
5. **Security scan** (Bandit)

### CI Test Matrix

```yaml
matrix:
  os: [ubuntu-latest, macos-latest, windows-latest]
  python-version: ["3.12", "3.13"]
```

### Running Tests Locally Like CI

```bash
# Install dependencies
uv sync --all-extras

# Lint
uv run ruff check .

# Format check
uv run black --check .

# Type check
uv run mypy .

# Run tests
uv run pytest -v
```

---

## Test Coverage

### Measuring Coverage

```bash
# Run with coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Generate HTML report
uv run pytest --cov=src/agenticfleet --cov-report=html
# View: open htmlcov/index.html
```

### Coverage Goals

- **Core modules**: >80% coverage
- **Utilities**: >90% coverage
- **API endpoints**: >70% coverage
- **Integration**: Focus on critical paths

---

## Best Practices

### ✅ DO

- Run focused tests: `uv run pytest tests/test_<module>.py -k "test_name"`
- Mock external API calls to avoid costs and flakiness
- Use fixtures for shared setup code
- Validate configuration after every config change
- Write descriptive test names and docstrings
- Type hint test functions and fixtures
- Use `asyncio_mode = auto` (no `@pytest.mark.asyncio` decorator)

### ❌ DON'T

- Don't run entire test suite on every change (expensive)
- Don't make real API calls in unit tests
- Don't skip test configuration validation (`test_config.py`)
- Don't use `pytest.mark.asyncio` decorator (unnecessary with `asyncio_mode = auto`)
- Don't commit test data to git (use `.tmp/` for temporary files)
- Don't hardcode API keys in tests (use env vars or mocks)

---

## Troubleshooting

### Import Errors

```bash
# Ensure pythonpath is set correctly
# Check pytest.ini: pythonpath = src

# Install in development mode
uv sync --all-extras
```

### Async Test Issues

```bash
# Ensure asyncio_mode = auto in pytest.ini
# Remove @pytest.mark.asyncio decorators
```

### Mock Not Working

```python
# Ensure spec is correct
from unittest.mock import MagicMock
mock = MagicMock(spec=ActualClass)

# Use AsyncMock for async methods
from unittest.mock import AsyncMock
mock.async_method = AsyncMock(return_value=result)
```

### Test Hangs

```bash
# Set timeout
uv run pytest tests/test_config.py --timeout=30
```

---

## Quick Command Reference

```bash
# Configuration validation (CRITICAL after config changes)
uv run python tests/test_config.py

# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_magentic_fleet.py -v

# Run specific test function
uv run pytest tests/test_config.py::test_researcher_agent -v

# Run tests matching pattern
uv run pytest -k "orchestrator" -v

# Verbose output with short traceback
uv run pytest -vv --tb=short

# Show print statements
uv run pytest -s

# Run with coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Drop into debugger on failure
uv run pytest --pdb

# Run E2E tests (requires backend + frontend running)
make test-e2e
```

---

## References

- **Root AGENTS.md**: `../AGENTS.md` (general project instructions)
- **pytest Documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **unittest.mock**: https://docs.python.org/3/library/unittest.mock.html
- **Playwright**: https://playwright.dev/python/

---

## Test-Specific Notes

- **Always use `uv run`** prefix for pytest commands
- **Configuration validation is critical**—run `test_config.py` after every config change
- **Run focused tests**—don't waste time running the entire suite
- **Mock external calls**—avoid real API calls in unit tests
- **Type safety**—tests should be fully typed like production code
- **No `@pytest.mark.asyncio`**—`asyncio_mode = auto` handles it
- **Use fixtures**—share setup code via `conftest.py`
- **Test coverage is tracked**—aim for >80% on core modules
- **CI runs all checks**—lint, format, type, test, build, security
