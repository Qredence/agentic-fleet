# AgenticFleet Testing Guide

Comprehensive guide for testing AgenticFleet applications, including best practices, test patterns, and quality standards.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Writing Tests](#writing-tests)
6. [Mock Strategy](#mock-strategy)
7. [Performance Testing](#performance-testing)
8. [Load Testing](#load-testing)
9. [Quality Assurance](#quality-assurance)
10. [CI/CD Integration](#cicd-integration)
11. [Troubleshooting](#troubleshooting)

---

## Testing Philosophy

AgenticFleet follows a **comprehensive testing strategy** that ensures high-quality, reliable software across all application layers. Our testing approach is based on these principles:

### Core Principles

1. **Test-First Development**: Write tests before or alongside production code
2. **Comprehensive Coverage**: Target >80% line coverage across all critical paths
3. **Mock External Dependencies**: Never rely on external services in tests
4. **Fast Feedback**: Keep unit tests fast (<1s) and integration tests reasonable (<10s)
5. **Realistic Scenarios**: Test actual user workflows and edge cases
6. **Automated Quality Gates**: Prevent regressions through automated testing

### Testing Pyramid

```
    E2E Tests (10%) - Critical user workflows
   ──────────────────────────────────────
  Integration Tests (20%) - Service interactions
 ────────────────────────────────────────────────
Unit Tests (70%) - Fast, isolated component testing
```

---

## Test Structure

### Directory Organization

```
tests/
├── test_config.py                      # Configuration validation (CRITICAL)
├── test_improvement_implementation.py  # Enhanced testing utilities
├── test_automation.py                  # Automated test execution
├── load_testing/                       # Performance and load testing
│   ├── locustfile.py                  # Locust load test scenarios
│   ├── run_load_tests.py              # Load test orchestration
│   ├── config.py                      # Load test configuration
│   ├── monitoring.py                  # Performance monitoring
│   └── dashboard.py                   # Performance dashboard
├── test_api_*.py                       # API endpoint tests
├── test_backend_*.py                   # Backend integration tests
├── test_magentic_*.py                  # Magentic workflow tests
├── test_workflow_*.py                  # Workflow management tests
├── test_*_integration.py               # Integration test files
└── test_*_e2e.py                       # End-to-end test files
```

### Test File Naming Conventions

- **Unit Tests**: `test_<module_name>.py` (e.g., `test_response_aggregator.py`)
- **Integration Tests**: `test_<feature>_integration.py` (e.g., `test_magentic_integration.py`)
- **API Tests**: `test_api_<endpoint>.py` (e.g., `test_api_responses.py`)
- **E2E Tests**: `test_<workflow>_e2e.py` (e.g., `test_backend_e2e.py`)
- **Load Tests**: `load_<scenario>.py` or under `load_testing/` directory

---

## Running Tests

### Basic Test Execution

```bash
# Run all tests
make test
# or
uv run pytest -v

# Run specific test file
uv run pytest tests/test_config.py -v

# Run tests with coverage
uv run pytest --cov=src/agentic_fleet --cov-report=html

# Run configuration validation only
make test-config
```

### Test Categories

```bash
# Run only unit tests
uv run pytest -m "not integration and not e2e"

# Run only integration tests
uv run pytest -m "integration"

# Run only performance tests
uv run pytest -m "performance"

# Run tests with specific markers
uv run pytest -k "config"
```

### Advanced Test Execution

```bash
# Run tests in parallel
uv run pytest -n auto

# Run with performance profiling
uv run pytest --profile

# Run with detailed output
uv run pytest -vv --tb=long

# Stop on first failure
uv run pytest -x

# Run failed tests only
uv run pytest --lf
```

---

## Test Categories

### 1. Unit Tests

Fast, isolated tests that verify individual components work correctly.

**Characteristics:**

- Run in <1 second
- No external dependencies
- Mock all external services
- Test single responsibility

**Example:**

```python
def test_response_aggregator_accumulation():
    """Test content accumulation across multiple deltas."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Hello"}},
        {"type": "message.delta", "data": {"delta": " World"}}
    ]

    # Test implementation
    assert "Hello World" in aggregator.get_final_response()
```

### 2. Integration Tests

Test how components work together while maintaining reasonable execution speed.

**Characteristics:**

- Run in <10 seconds
- Test service interactions
- Mock external APIs
- Validate data flows

**Example:**

```python
@pytest.mark.asyncio
async def test_workflow_service_integration():
    """Test workflow service integration with database."""
    service = WorkflowService()

    workflow_id = await service.create_workflow("Test task")
    status = await service.get_workflow_status(workflow_id)

    assert status["status"] == "created"
```

### 3. End-to-End Tests

Complete workflow testing from user perspective.

**Characteristics:**

- Test realistic user scenarios
- Include all system components
- May be slower (10-60 seconds)
- Test error recovery

**Example:**

```python
@pytest.mark.e2e
def test_complete_chat_workflow():
    """Test complete chat workflow from creation to response."""
    client = TestClient(create_app())

    # Create conversation
    conv_resp = client.post("/v1/conversations")
    conv_id = conv_resp.json()["id"]

    # Send chat message
    chat_resp = client.post("/v1/chat", json={
        "conversation_id": conv_id,
        "message": "Hello, world!"
    })

    assert chat_resp.status_code == 200
    assert len(chat_resp.json()["messages"]) == 2
```

---

## Writing Tests

### Test Structure Pattern

Follow the **Arrange-Act-Assert** pattern for clear, readable tests:

```python
def test_specific_behavior():
    """Test description following Given-When-Then pattern."""
    # Arrange - Setup test data and mocks
    mock_client = create_mock_client()
    test_data = {"input": "test value"}

    # Act - Execute the behavior being tested
    result = service.process_data(mock_client, test_data)

    # Assert - Verify the expected outcome
    assert result.success is True
    assert result.output == "expected value"
    mock_client.process.assert_called_once_with(test_data)
```

### Test Fixtures

Use pytest fixtures for reusable test setup:

```python
@pytest.fixture
def mock_workflow_factory():
    """Create mock workflow factory."""
    factory = Mock(spec=WorkflowFactory)
    factory.list_available_workflows.return_value = [
        {"id": "test", "name": "Test Workflow", "agent_count": 3}
    ]
    return factory

@pytest.fixture
def workflow_service(mock_workflow_factory):
    """Create workflow service with mocked dependencies."""
    return WorkflowService(factory=mock_workflow_factory)
```

### Async Testing

For async functions, use `pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_service_method():
    """Test async service method execution."""
    service = AsyncService()

    result = await service.process_async_data("input")

    assert result.status == "completed"
```

### Error Testing

Always test error conditions and edge cases:

```python
def test_error_handling():
    """Test proper error handling for invalid input."""
    service = DataService()

    with pytest.raises(ValueError, match="Invalid input"):
        service.process_data(None)

    # Verify error is logged appropriately
    mock_logger.error.assert_called_once()
```

---

## Mock Strategy

### External Service Mocking

Never call external services in tests. Always mock them:

```python
@pytest.fixture
def mock_openai_client():
    """Create comprehensive OpenAI client mock."""
    client = Mock()
    agent = AsyncMock()

    # Setup realistic response patterns
    agent.run.return_value = Mock(
        content="Test response",
        tool_calls=[],
        usage=Mock(
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75
        )
    )

    client.create_agent.return_value = agent
    return client
```

### Database Mocking

For database operations, use test databases or mocks:

```python
@pytest.fixture
async def test_db():
    """Create isolated test database."""
    # Create temporary database
    test_db_path = tempfile.mktemp(suffix=".db")

    # Setup schema
    db = DatabaseConnection(test_db_path)
    await db.setup_schema()

    yield db

    # Cleanup
    await db.close()
    os.unlink(test_db_path)
```

### HTTP Client Mocking

For HTTP requests, use proper mocking:

```python
@pytest.fixture
def mock_http_client():
    """Create mock HTTP client."""
    client = Mock()

    # Setup response mocking
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"status": "success"}
    response.raise_for_status.return_value = None

    client.get.return_value = response
    client.post.return_value = response

    return client
```

---

## Performance Testing

### Response Time Testing

Add performance assertions to critical tests:

```python
def test_api_response_time():
    """Test API response time meets SLA requirements."""
    import time

    start_time = time.time()

    response = client.get("/v1/workflows")

    execution_time = (time.time() - start_time) * 1000

    assert response.status_code == 200
    assert execution_time < 2000, f"Response time {execution_time}ms exceeds SLA"
```

### Memory Testing

Test for memory leaks in long-running processes:

```python
def test_memory_usage():
    """Test service doesn't leak memory over time."""
    import psutil
    import gc

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # Run operation multiple times
    for _ in range(1000):
        service.process_data("test")
        gc.collect()  # Force garbage collection

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Memory increase should be minimal (< 10MB)
    assert memory_increase < 10 * 1024 * 1024, f"Memory leak detected: {memory_increase} bytes"
```

### Concurrency Testing

Test thread safety and concurrent access:

```python
def test_concurrent_access():
    """Test service handles concurrent requests safely."""
    import threading
    import queue

    results = queue.Queue()

    def worker():
        try:
            result = service.process_data("concurrent_test")
            results.put(result)
        except Exception as e:
            results.put(e)

    # Create multiple threads
    threads = [threading.Thread(target=worker) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Check all results are successful
    success_count = 0
    while not results.empty():
        result = results.get()
        if not isinstance(result, Exception):
            success_count += 1

    assert success_count == 10, f"Only {success_count}/10 requests succeeded"
```

---

## Load Testing

### Load Test Scenarios

AgenticFleet includes comprehensive load testing using Locust:

```python
class AgenticFleetUser(HttpUser):
    """Simulates typical user behavior."""

    wait_time = between(1, 3)

    @task(3)
    def send_chat_message(self):
        """Primary chat functionality."""
        self.client.post("/v1/chat", json={
            "message": "Test message",
            "conversation_id": self.conversation_id
        })

    @task(1)
    def get_workflows(self):
        """Workflow discovery."""
        self.client.get("/v1/workflows")
```

### Running Load Tests

```bash
# Setup load testing environment
make load-test-setup

# Run smoke test (quick validation)
make load-test-smoke

# Run normal load test
make load-test-load

# Run stress test
make load-test-stress

# Start performance dashboard
make load-test-dashboard
```

### Load Test Configuration

Configure load testing scenarios in `tests/load_testing/config.py`:

```python
LOAD_TEST_SCENARIOS = {
    "smoke_test": {
        "users": 5,
        "spawn_rate": 1,
        "duration": "2m",
        "description": "Quick smoke test validation"
    },
    "normal_load": {
        "users": 50,
        "spawn_rate": 5,
        "duration": "10m",
        "description": "Normal production load"
    },
    "stress_test": {
        "users": 200,
        "spawn_rate": 20,
        "duration": "15m",
        "description": "Stress test to find limits"
    }
}
```

---

## Quality Assurance

### Code Coverage

Maintain high test coverage across the codebase:

```bash
# Generate coverage report
uv run pytest --cov=src/agentic_fleet --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Coverage Targets:**

- **Overall Coverage**: >80%
- **Core Modules**: >90%
- **API Endpoints**: >85%
- **Workflow Logic**: >90%

### Configuration Validation

Critical configuration testing to prevent deployment failures:

```python
def test_workflow_configuration_validation():
    """Validate all workflow configurations are correct."""
    validator = ConfigurationValidator()
    results = validator.validate_workflow_configuration()

    assert results["valid"], f"Configuration errors: {results['errors']}"
    assert results["workflows_validated"] > 0
```

Run configuration validation:

```bash
make test-config
```

### Contract Testing

Ensure API responses match expected contracts:

```python
def test_api_contract_compliance():
    """Test API responses match OpenAPI specification."""
    tester = ContractTestingFramework()

    response = client.get("/v1/workflows")

    assert tester.validate_response_contract(
        "/v1/workflows",
        response.json(),
        response.status_code
    )
```

---

## CI/CD Integration

### GitHub Actions

Automated testing is integrated into GitHub Actions:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          make install

      - name: Run configuration validation
        run: make test-config

      - name: Run tests
        run: |
          make test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

Ensure code quality before commits:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: uv run pytest
        language: system
        pass_filenames: false
        always_run: true

      - id: test-config
        name: test-config
        entry: uv run python -c "from agentic_fleet.utils.factory import WorkflowFactory; WorkflowFactory().list_available_workflows()"
        language: system
        pass_filenames: false
        always_run: true
```

Install pre-commit hooks:

```bash
make pre-commit-install
```

---

## Troubleshooting

### Common Issues

#### 1. Tests Fail with uv Cache Errors

```bash
# Clean uv cache
uv cache clean

# Resync dependencies
make sync

# Run tests again
make test
```

#### 2. Configuration Tests Fail

```bash
# Check configuration file exists
ls -la src/agentic_fleet/workflow.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('src/agentic_fleet/workflow.yaml'))"

# Run configuration validation
make test-config
```

#### 3. Load Tests Can't Connect to Backend

```bash
# Ensure backend is running
make backend

# Check health endpoint
curl http://localhost:8000/health

# Run smoke test
make load-test-smoke
```

#### 4. Import Errors in Tests

```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Install dependencies
make install

# Verify installation
uv run python -c "import agentic_fleet; print('✅ Import successful')"
```

### Debug Mode

Run tests with detailed debugging:

```bash
# Verbose output
uv run pytest -vv --tb=long

# Debug with pdb
uv run pytest --pdb

# Stop on first failure
uv run pytest -x --tb=long

# Run specific test with debug
uv run pytest tests/test_config.py::test_workflow_factory_initialization -vvvs
```

### Performance Profiling

Profile test execution to identify bottlenecks:

```bash
# Install profiler
uv add pytest-profiling

# Run with profiling
uv run pytest --profile-svg

# View profile
open profile.svg
```

---

## Best Practices Summary

### ✅ Do's

1. **Write tests first** - Test-driven development
2. **Mock external dependencies** - Never rely on external services
3. **Use descriptive test names** - Clear behavior description
4. **Follow Arrange-Act-Assert** - Clear test structure
5. **Test error conditions** - Verify proper error handling
6. **Keep tests fast** - Unit tests <1s, integration <10s
7. **Use fixtures** - Reusable test setup
8. **Validate configuration** - Prevent deployment failures
9. **Monitor test performance** - Ensure SLAs are met
10. **Maintain coverage** - >80% across critical paths

### ❌ Don'ts

1. **Don't test external services** - Mock them instead
2. **Don't write slow tests** - Keep them fast and focused
3. **Don't ignore test failures** - Address all issues
4. **Don't hardcode test data** - Use factories and fixtures
5. **Don't skip edge cases** - Test boundary conditions
6. **Don't use sleep in tests** - Use proper async patterns
7. **Don't share state between tests** - Ensure isolation
8. **Don't ignore configuration validation** - It's critical
9. **Don't forget performance testing** - SLA validation
10. **Don't skip load testing** - Ensure scalability

---

## Resources

- **pytest Documentation**: <https://docs.pytest.org/>
- **Locust Load Testing**: <https://locust.io/>
- **Mock Documentation**: <https://docs.python.org/3/library/unittest.mock.html>
- **Coverage.py**: <https://coverage.readthedocs.io/>
- **Test Automation**: <https://test-automation.io/>

For specific questions or issues, refer to the test files in the `tests/` directory or consult the development team.
