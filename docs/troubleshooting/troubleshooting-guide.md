# AgenticFleet Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered when developing, deploying, and using AgenticFleet. For development-specific troubleshooting, see the [Agent Development Guide](../development/agent-development.md).

## Table of Contents

- [Installation and Setup Issues](#installation-and-setup-issues)
- [Configuration Problems](#configuration-problems)
- [Agent Development Issues](#agent-development-issues)
- [API and Backend Issues](#api-and-backend-issues)
- [Frontend Issues](#frontend-issues)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)
- [Testing Issues](#testing-issues)

---

## Installation and Setup Issues

### Dependency Installation Failures

**Problem**: `uv sync` fails with dependency conflicts

**Solutions**:
```bash
# Clear cache and retry
uv cache clean
rm -rf .venv
uv sync

# Force reinstall specific package
uv add package_name==version --force-reinstall

# Check Python version compatibility
python --version  # Should be 3.12+
```

**Common Causes**:
- Python version incompatible with dependencies
- Corrupted uv cache
- Conflicting dependencies in lockfile

### Frontend Setup Issues

**Problem**: `npm install` fails or `make dev` frontend errors

**Solutions**:
```bash
# Clear npm cache
npm cache clean --force
rm -rf node_modules
npm install

# Check Node.js version
node --version  # Should be 18+
npm --version  # Should be recent

# Install frontend dependencies separately
cd src/frontend
npm install --legacy-peer-deps
```

**Common Causes**:
- Node.js version too old
- npm registry issues
- Port conflicts (5173 already in use)

### Environment Configuration Issues

**Problem**: Missing or invalid environment variables

**Solutions**:
```bash
# Check environment variables
env | grep -E "(OPENAI_|ENABLE_|OTLP_)"

# Create required .env file
cp .env.example .env
# Edit .env with proper values

# Verify configuration loading
make test-config
```

**Common Causes**:
- Missing `.env` file
- Incorrect API key format
- Invalid environment variable names

---

## Configuration Problems

### YAML Syntax Errors

**Problem**: Configuration validation fails with YAML parsing errors

**Solutions**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('src/agenticfleet/config/workflow.yaml'))"

# Check indentation (YAML requires spaces, not tabs)
# Use YAML linter
pip install yamllint
yamllint src/agenticfleet/config/workflow.yaml
```

**Common Causes**:
- Tabs instead of spaces for indentation
- Missing colons or incorrect formatting
- Unescaped special characters in strings

### Agent Configuration Issues

**Problem**: Agent factory fails or agent not available

**Solutions**:
```bash
# Test specific agent configuration
uv run python -c "
from agenticfleet.config.settings import load_agent_config
config = load_agent_config('researcher')
print(config)
"

# Validate agent factory
make test-config

# Check required fields
agents/agents/<role>/config.yaml should have:
- name, model, system_prompt, tools
```

**Common Causes**:
- Missing required fields in agent config
- Invalid model names
- Incorrect agent factory import paths

### Memory Configuration Issues

**Problem**: Memory provider fails to initialize

**Solutions**:
```bash
# Check Mem0 configuration
echo "AZURE_AI_SEARCH_ENDPOINT: $AZURE_AI_SEARCH_ENDPOINT"
echo "AZURE_AI_SEARCH_KEY: ${AZURE_AI_SEARCH_KEY:+configured}"

# Test memory provider
uv run python -c "
from agenticfleet.context.mem0_provider import Mem0Provider
provider = Mem0Provider()
print('Memory provider status:', provider.is_available())
"
```

**Common Causes**:
- Missing or incorrect Azure credentials
- Invalid endpoint URLs
- Firewall blocking Azure services

---

## Agent Development Issues

### Tool Registration Failures

**Problem**: Tools not appearing in agent's available tools

**Solutions**:
```python
# Check tool import and registration
# In agents/<role>/agent.py:
from .tools.tool1 import create_tool1  # Verify import

# In tool function:
def create_tool1() -> Any:
    return FunctionTool(
        name="tool1_tool",
        description="Clear description",
        function=tool1_function
    )

# Verify tools list contains tool
tools = [create_tool1(), create_tool2()]
print(f"Available tools: {[tool.name for tool in tools]}")
```

**Common Causes**:
- Tool not imported in agent factory
- Tool function not returning FunctionTool instance
- Tool not enabled in config.yaml

### Pydantic Validation Errors

**Problem**: Tool output models fail validation

**Solutions**:
```python
# Check model field definitions
# All fields must have type annotations
class MyToolResult(BaseModel):
    success: bool  # Required field
    result: str    # Required field
    optional_field: Optional[str] = None  # Optional field with default

# Test model validation
from pydantic import ValidationError
try:
    result = MyToolResult(success=True, result="test")
except ValidationError as e:
    print(f"Validation error: {e}")
```

**Common Causes**:
- Missing required fields in model
- Incorrect type annotations
- Field name mismatches

### Agent Not Responding

**Problem**: Agent created but not responding to requests

**Solutions**:
```python
# Check system prompt formatting
# Ensure system_prompt is properly formatted in config.yaml

# Verify model availability
uv run python -c "
from agent_framework.azure_ai import OpenAIResponsesClient
client = OpenAIResponsesClient(model_id='gpt-5')
print('Model available:', client is not None)
"

# Test agent in isolation
from agenticfleet.agents.<role>.agent import create_<role>_agent
agent = create_<role>_agent()
result = agent.process_message('Hello, can you help me?')
print(f'Agent response: {result}')
```

**Common Causes**:
- Invalid or unavailable model
- Empty or malformed system prompt
- Network connectivity issues
- API key problems

---

## API and Backend Issues

### Server Startup Failures

**Problem**: FastAPI server fails to start

**Solutions**:
```bash
# Check port availability
lsof -i :8000  # Check if port 8000 is in use
netstat -an | grep :8000

# Try different port
uv run uvicorn agenticfleet.haxui.api:app --port 8001

# Check dependencies
uv run python -c "
import agenticfleet.haxui.api
print('API module loaded successfully')
"

# Verify configuration
make test-config
```

**Common Causes**:
- Port already in use
- Missing dependencies
- Configuration errors
- Permission issues

### SSE Streaming Issues

**Problem**: Frontend not receiving real-time updates

**Solutions**:
```bash
# Test SSE endpoint directly
curl -N http://localhost:8000/v1/conversations/test/stream \
  -H "Accept: text/event-stream"

# Check CORS configuration
curl -H "Origin: http://localhost:5173" \
  http://localhost:8000/v1/conversations

# Verify event format
# Check that server sends proper SSE format:
data: {"type": "response.output_text.delta", "data": {...}}
```

**Common Causes**:
- CORS configuration blocking frontend
- Firewall blocking SSE connections
- Incorrect event format
- Connection timeouts

### Database/Storage Issues

**Problem**: Conversation storage or checkpointing fails

**Solutions**:
```bash
# Check SQLite file permissions
ls -la var/
chmod 755 var/

# Verify database schema
sqlite3 var/haxui/state.db ".schema"

# Test checkpoint creation
uv run python -c "
from agenticfleet.fleet.checkpoints import FileCheckpointStorage
storage = FileCheckpointStorage('./var/checkpoints')
print('Checkpoint storage:', storage)
"

# Recreate database if corrupted
rm var/haxui/state.db
# Restart server to recreate
```

**Common Causes**:
- File permission issues
- Disk space full
- Database corruption
- Incorrect file paths

---

## Frontend Issues

### Build Failures

**Problem**: `npm run build` fails or produces broken output

**Solutions**:
```bash
# Clear build cache
rm -rf src/frontend/dist
rm -rf src/frontend/node_modules/.cache

# Check TypeScript compilation
cd src/frontend
npm run type-check

# Verify Vite configuration
npm run build --mode development  # More verbose output

# Check for dependency conflicts
npm ls --depth=0  # Check for duplicate dependencies
```

**Common Causes**:
- TypeScript compilation errors
- Dependency version conflicts
- Vite configuration issues
- Insufficient memory during build

### Runtime Errors

**Problem**: Frontend loads but shows errors or blank screen

**Solutions**:
```bash
# Check browser console for JavaScript errors
# Open http://localhost:5173 and check DevTools

# Verify API connection
curl http://localhost:8000/health

# Check network requests in browser DevTools
# Look for failed API calls or CORS errors

# Test with minimal configuration
# Temporarily disable features to isolate issue
```

**Common Causes**:
- API server not running
- CORS configuration issues
- Environment variable problems
- JavaScript errors in components

### State Management Issues

**Problem**: UI not updating correctly or state inconsistencies

**Solutions**:
```typescript
// Check React state updates
console.log('Current state:', state);

// Verify useEffect dependencies
useEffect(() => {
  // Check if dependencies are correct
}, [dependency1, dependency2]);

// Test state updates manually
const testState = { ...previousState, newProperty: 'value' };
setTestState(testState);
```

**Common Causes**:
- Missing dependency arrays in useEffect
- State mutation without proper updates
- Concurrent state updates
- Props drilling issues

---

## Performance Issues

### Slow Agent Responses

**Problem**: Agents taking too long to respond

**Solutions**:
```yaml
# In agents/<role>/config.yaml:
temperature: 0.1    # Lower for more deterministic responses
max_tokens: 2000    # Reduce to limit output length
top_p: 0.9         # Lower for more focused responses

# Enable token usage tracking
ENABLE_OTEL=true
```

**Common Causes**:
- Too high temperature settings
- Excessive token limits
- Network latency
- Model overloading

### Memory Leaks

**Problem**: Memory usage increases over time

**Solutions**:
```bash
# Monitor memory usage
htop  # Look for growing memory usage
uv run python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

# Check for unclosed resources
# Review code for unclosed files, connections, etc.

# Monitor in production
# Use memory profiling tools
pip install memory-profiler
python -m memory_profiler script.py
```

**Common Causes**:
- Unclosed file handles or database connections
- Large objects not garbage collected
- Memory leaks in long-running processes
- Insufficient cleanup in error handling

### High CPU Usage

**Problem**: System CPU usage consistently high

**Solutions**:
```bash
# Profile CPU usage
top -p $$  # Show specific process usage
uv run python -c "
import time
import psutil
for _ in range(60):
    print(f'CPU: {psutil.cpu_percent()}%')
    time.sleep(1)
"

# Identify bottlenecks
# Use Python profiler
uv run python -m cProfile -o profile.stats script.py
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(10)
"
```

**Common Causes**:
- Inefficient algorithms
- Infinite loops
- Blocking operations in async contexts
- Resource contention

---

## Deployment Issues

### Container Deployment Failures

**Problem**: Docker container fails to start or crashes

**Solutions**:
```dockerfile
# Use multi-stage builds for smaller images
FROM python:3.12-slim as builder
# Install dependencies first, then copy code

# Add health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set proper environment variables
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV PYTHONPATH=/app
```

**Common Causes**:
- Missing dependencies in container
- Incorrect environment variables
- Port binding issues
- Resource limits exceeded

### Production Configuration Issues

**Problem**: Production environment has different behavior than development

**Solutions**:
```bash
# Verify configuration
make test-config

# Check environment-specific settings
env | sort

# Test with production configuration
export ENVIRONMENT=production
make test

# Use configuration validation
uv run python -c "
from agenticfleet.config.settings import Settings
settings = Settings()
print('Production config valid:', settings.validate())
"
```

**Common Causes**:
- Missing environment variables
- Different configuration values
- Network/firewall restrictions
- Resource limitations

---

## Testing Issues

### Test Configuration Failures

**Problem**: `make test-config` fails validation

**Solutions**:
```bash
# Check detailed error output
make test-config 2>&1 | tee config_test.log

# Validate individual components
uv run python tests/test_config.py::test_orchestrator_agent -v
uv run python tests/test_config.py::test_researcher_agent -v

# Check YAML syntax
python -c "
import yaml
import sys
try:
    with open('src/agenticfleet/config/workflow.yaml') as f:
        yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f'YAML error: {e}')
    sys.exit(1)
"
```

**Common Causes**:
- Missing required fields in configuration
- Invalid YAML syntax
- Incorrect agent factory imports
- Missing dependencies for tools

### Test Runtime Failures

**Problem**: Tests fail with import or runtime errors

**Solutions**:
```bash
# Run tests with detailed output
uv run pytest -v --tb=short

# Run specific failing test
uv run pytest tests/test_config.py::test_orchestrator_agent -v -s

# Check Python path and dependencies
uv run python -c "
import sys
print('Python path:', sys.path)
import agenticfleet
print('AgenticFleet imported successfully')
"

# Mock external dependencies
# In test files, mock network calls and APIs
from unittest.mock import patch, MagicMock
```

**Common Causes**:
- Missing test dependencies
- Incorrect Python path
- Missing mocks for external services
- Async test configuration issues

### E2E Test Failures

**Problem**: End-to-end tests failing inconsistently

**Solutions**:
```bash
# Check test environment
make dev  # Ensure backend and frontend running

# Run E2E tests with detailed output
make test-e2e 2>&1 | tee e2e.log

# Check browser and network
# Verify browser can reach localhost:8000 and localhost:5173

# Isolate test components
# Run individual test scenarios
npx playwright test --grep "User authentication"
```

**Common Causes**:
- Test environment not properly set up
- Network timing issues
- Browser compatibility problems
- Race conditions in tests

---

## Debugging Tools and Techniques

### Logging Configuration

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export ENABLE_OTEL=true

# View structured logs
tail -f logs/agenticfleet.log | jq '.'
```

### API Testing

```bash
# Test API endpoints directly
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"task": "test task"}'

# Test WebSocket/SSE connections
wscat -c ws://localhost:8000/ws
```

### Configuration Debugging

```python
# Dump loaded configuration
from agenticfleet.config.settings import Settings
settings = Settings()
print(json.dumps(settings.dict(), indent=2))

# Test individual components
from agenticfleet.agents.orchestrator.agent import create_orchestrator_agent
agent = create_orchestrator_agent()
print(f'Agent created: {agent.name}')
```

### Performance Profiling

```bash
# Profile Python code
uv run python -m cProfile -o profile.stats script.py
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
pip install memory-profiler
uv run python -m memory_profiler script.py
```

## Getting Help

### Community Support

- **GitHub Issues**: [Create an issue](https://github.com/Qredence/agentic-fleet/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions)
- **Documentation**: [AgenticFleet Documentation](https://github.com/Qredence/agentic-fleet/tree/main/docs)

### Debug Information to Collect

When reporting issues, please include:

1. **Environment Information**:
   - Operating system and version
   - Python and Node.js versions
   - uv and npm versions
   - Browser/version (for frontend issues)

2. **Configuration**:
   - Relevant environment variables (without sensitive data)
   - Configuration files (YAML) if relevant
   - Custom modifications made

3. **Error Messages**:
   - Complete error messages and stack traces
   - Logs from relevant components
   - Steps to reproduce the issue

4. **Expected vs Actual**:
   - What you expected to happen
   - What actually happened
   - Any workarounds found

This troubleshooting guide should help resolve most common issues. For additional support, don't hesitate to reach out through the community channels provided above.
