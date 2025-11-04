# AgenticFleet Testing Specification

## Overview

This document specifies the comprehensive testing strategy and infrastructure for AgenticFleet, covering all aspects from unit testing to load testing, with specific focus on the unique challenges of testing multi-agent orchestration systems.

## Testing Philosophy

### Core Principles

1. **Mock External Dependencies**: Never hit real APIs in tests - all external services (OpenAI, Azure, etc.) are mocked
2. **Configuration Validation**: Every test must validate YAML configuration and agent factory wiring
3. **Type Safety**: All tests must pass MyPy strict type checking
4. **Isolation**: Tests should be independent and runnable in any order
5. **Performance Awareness**: Load testing validates system behavior under stress

### Testing Without API Costs

All LLM interactions are mocked using `OpenAIResponsesClient` patches, enabling comprehensive testing without incurring API costs:

```python
# Standard pattern for mocking LLM clients
@pytest.fixture
def mock_openai_client():
    with patch('agent_framework.azure_ai.OpenAIResponsesClient') as mock_client:
        mock_client.return_value = MockClient()
        yield mock_client
```

## Test Infrastructure

### Backend Testing Stack

**Testing Framework**: pytest with async support
**Type Checking**: MyPy strict mode (100% compliance requirement)
**Code Quality**: Ruff linting + Black formatting
**Coverage**: pytest-cov with target >80% coverage

### Frontend Testing Stack

**Testing Framework**: Vitest (unit) + Playwright (E2E)
**Type Checking**: TypeScript strict mode
**Code Quality**: ESLint + Prettier
**Build Testing**: Vite production build validation

## Test Categories

### 1. Configuration Tests (`tests/test_config.py`)

**Purpose**: Validate YAML configuration and agent factory wiring
**Critical Scenarios**:

- YAML syntax validation
- Agent factory exports
- Workflow resolution hierarchy
- Environment variable integration

**Key Tests**:

```python
def test_workflow_factory_validation():
    """Validate that all agents can be instantiated from config"""
    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()
    assert len(workflows) > 0

    for workflow_id in workflows:
        workflow = factory.create_workflow(workflow_id)
        assert workflow is not None

def test_yaml_configuration_resolution():
    """Test hierarchical configuration override system"""
    # Tests AF_WORKFLOW_CONFIG → config/workflows.yaml → packaged workflow.yaml
```

### 2. Magentic Integration Tests

#### `tests/test_magentic_integration.py`

**Purpose**: Test Microsoft Agent Framework Magentic pattern integration
**Critical Scenarios**:

- PLAN → EVALUATE → ACT → OBSERVE cycle execution
- Agent spawning and coordination
- Progress ledger management
- Event streaming integration

#### `tests/test_magentic_backend_integration.py`

**Purpose**: Full backend integration with mocked agents
**Critical Scenarios**:

- End-to-end workflow execution
- Multi-agent coordination
- Error recovery and reset mechanisms
- Checkpoint system validation

### 3. API Tests

#### `tests/test_api_responses_streaming.py`

**Purpose**: Validate Server-Sent Events (SSE) streaming implementation
**Critical Scenarios**:

- Event formatting and buffering
- Multi-line JSON structure handling
- Connection management
- Error propagation in streams

#### `tests/test_api_health.py`, `tests/test_api_entities.py`

**Purpose**: Basic API endpoint validation
**Critical Scenarios**:

- Health check endpoints
- Workflow discovery API
- Error handling and status codes

### 4. Workflow Tests (`tests/test_workflow_factory.py`)

**Purpose**: Validate workflow creation and configuration
**Critical Scenarios**:

- YAML resolution and parsing
- Agent factory integration
- Tool registration and validation
- Configuration error handling

### 5. Event System Tests

#### `tests/test_event_bridge.py`

**Purpose**: Validate event bridging between backend and frontend
**Critical Scenarios**:

- Event schema consistency
- Event filtering and routing
- Progress tracking events
- Error event handling

### 6. Utility and Integration Tests

**Files**: `test_console.py`, `test_static_file_serving.py`, `test_error_handling.py`
**Purpose**: Test auxiliary functionality
**Critical Scenarios**:

- CLI interface functionality
- Static file serving for frontend assets
- Error handling and recovery
- Memory integration (optional)

## Load Testing Infrastructure

### Location: `tests/load_testing/`

### Tools and Frameworks

**Primary Tools**:

- **Locust**: Python-based load testing framework
- **k6**: JavaScript-based load testing for frontend
- **Custom Dashboards**: Real-time monitoring and visualization

### Test Scenarios

#### 1. Smoke Test (`--scenario smoke_test`)

**Purpose**: Quick validation that system is functioning
**Load**: 1 concurrent user, short duration
**Validation**: Basic workflow execution completes successfully

#### 2. Normal Load Test (`--scenario normal_load`)

**Purpose**: Validate performance under expected load
**Load**: 10-50 concurrent users, sustained execution
**Validation**: Response times remain acceptable, no errors

#### 3. Stress Test (`--scenario stress_test`)

**Purpose**: Find breaking points and validate error handling
**Load**: 100+ concurrent users, aggressive ramp-up
**Validation**: Graceful degradation, proper error handling

### Load Testing Commands

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

## Frontend Testing

### Unit Testing with Vitest

**Location**: `src/frontend/src/` alongside components
**Framework**: Vitest with @testing-library/react
**Coverage**: Component logic, hooks, utilities

### Integration Testing

**API Client Testing**: Mock API responses and validate client behavior
**State Management**: Test Zustand stores and hook interactions
**Event Parsing**: Validate SSE event parsing and UI updates

### End-to-End Testing with Playwright

**Scenarios**:

- Complete workflow execution from UI
- Real-time updates during long-running workflows
- Error handling and recovery from UI perspective
- Cross-browser compatibility

## Testing Workflow

### Development Testing

```bash
# Run specific test file during development
uv run pytest tests/test_config.py -v

# Run focused tests with keyword filtering
uv run pytest -k "magentic"

# Run with coverage reporting
uv run pytest --cov=src/agenticfleet --cov-report=term-missing

# Frontend unit tests
cd src/frontend && npm run test

# Frontend build test
cd src/frontend && npm run build
```

### CI/CD Testing Pipeline

```bash
# Complete quality gate (used in GitHub Actions)
make check          # lint + format + type-check
make test-config    # configuration validation
make test           # full test suite
```

### Pre-commit Testing

Automated hooks ensure code quality before commits:

- Black formatting validation
- Ruff linting
- MyPy type checking
- Import sorting

## Test Data and Fixtures

### Mock Data Patterns

**Agent Responses**: Standardized mock responses following OpenAI format
**Workflow Events**: Consistent event structure for frontend testing
**Configuration Variants**: Different YAML configurations for edge case testing

### Test Isolation

Each test must:

- Clean up after execution
- Not depend on other tests' state
- Use unique identifiers to avoid conflicts
- Mock external dependencies consistently

## Performance Benchmarks

### Target Performance Metrics

**API Response Times**:

- Health checks: <100ms
- Workflow initiation: <500ms
- Event streaming: <50ms per event

**Load Testing Targets**:

- Concurrent workflows: 50+ without degradation
- Response time percentiles: p95 <2s, p99 <5s
- Error rate: <1% under normal load

**Resource Usage**:

- Memory: <512MB per backend instance
- CPU: <70% under normal load
- Database: <1000 operations per second

## Testing Best Practices

### Test Design Principles

1. **Arrange-Act-Assert Pattern**: Clear test structure
2. **Descriptive Test Names**: Test names should describe the scenario
3. **Single Responsibility**: Each test validates one specific behavior
4. **Data-Driven Testing**: Use parameterized tests for multiple scenarios

### Mock Strategy

1. **Consistent Mocks**: Use fixtures for common mock objects
2. **Realistic Data**: Mock responses should match real API structure
3. **Error Scenarios**: Include negative test cases with error conditions
4. **Edge Cases**: Test boundary conditions and unusual inputs

### Maintenance Guidelines

1. **Update Tests with Code**: Every new feature requires corresponding tests
2. **Review Test Coverage**: Regular coverage analysis to identify gaps
3. **Performance Regression**: Monitor test execution times
4. **Test Documentation**: Keep test documentation current with code changes

## Troubleshooting Test Issues

### Common Test Failures

1. **Configuration Validation Errors**:
   - Check YAML syntax and agent factory exports
   - Verify environment variables in test environment
   - Run `make test-config` for detailed error information

2. **Import Errors**:
   - Verify `uv sync` completed successfully
   - Check Python path configuration
   - Ensure all dependencies are installed

3. **Mock Failures**:
   - Verify mock patch paths are correct
   - Check that mock objects have required attributes
   - Validate mock return values match expected structure

4. **Async Test Issues**:
   - Use proper async/await patterns
   - Ensure test fixtures handle async cleanup
   - Verify event loop management in tests

## Test Evolution

### Phase 1: Foundation (Completed)

- Basic test infrastructure setup
- Configuration validation tests
- API endpoint testing
- Mock LLM client integration

### Phase 2: Integration (Completed)

- Magentic pattern integration tests
- Event streaming validation
- End-to-end workflow testing
- Load testing infrastructure

### Phase 3: Enhancement (Current)

- Performance benchmarking
- Cross-browser testing
- Accessibility testing
- Security testing

### Future Roadmap

1. **Visual Regression Testing**: Automated UI consistency checks
2. **Chaos Engineering**: Failure injection testing
3. **A/B Testing Infrastructure**: Feature flag testing
4. **Contract Testing**: API contract validation

## Success Metrics

### Coverage Targets

- **Code Coverage**: >80% for backend modules
- **Type Safety**: 100% MyPy compliance
- **Test Reliability**: <1% flaky test rate
- **Performance**: All benchmarks met consistently

### Quality Gates

- All tests must pass before deployment
- No new regressions in performance
- Configuration validation must succeed
- Security scanning must pass

## Conclusion

This comprehensive testing specification ensures AgenticFleet maintains high quality and reliability throughout its development lifecycle. The testing strategy balances thoroughness with efficiency, enabling rapid development while preventing regressions and ensuring production readiness.

The mock-based approach eliminates external dependencies and costs, while the load testing infrastructure validates system behavior under realistic conditions. This testing foundation supports the system's evolution from prototype to enterprise-grade production deployment.
