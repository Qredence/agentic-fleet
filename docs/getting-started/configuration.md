# Configuration Guide

Complete reference for configuring AgenticFleet.

---

## Overview

AgenticFleet uses a layered configuration system:

1. **Environment Variables** (`.env`) – Credentials and global settings
2. **Workflow Configuration** (`config/workflow.yaml`) – Orchestration settings
3. **Agent Configuration** (`agents/<role>/config.yaml`) – Per-agent settings

---

## Environment Variables

### Location

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### Required Variables

```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-your-api-key-here
```

### Model Configuration

```bash
# Default model for agents
OPENAI_MODEL=gpt-4o

# Model for code generation
OPENAI_RESPONSES_MODEL_ID=gpt-5-codex

# Temperature (0.0-2.0, default: 0.2)
OPENAI_TEMPERATURE=0.2
```

### Azure OpenAI (Optional)

Required for Mem0 memory integration:

```bash
# Azure AI Project
AZURE_AI_PROJECT_ENDPOINT=https://your-project.openai.azure.com/

# Azure AI Search (vector storage)
AZURE_AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_AI_SEARCH_KEY=your-search-key

# Azure OpenAI Models
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME=text-embedding-ada-002
```

### Memory Configuration

```bash
# Mem0 history database
MEM0_HISTORY_DB_PATH=./var/mem0.db

# Embedding model for memory
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Observability

```bash
# Enable OpenTelemetry tracing
ENABLE_OTEL=false

# OTLP endpoint (for Jaeger, Prometheus, etc.)
OTLP_ENDPOINT=http://localhost:4317

# Service name for traces
OTEL_SERVICE_NAME=agenticfleet
```

### Logging

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file location
LOG_FILE=logs/agenticfleet.log
```

### Development Settings

```bash
# Enable debug mode
DEBUG=false

# Enable verbose logging
VERBOSE=false
```

---

## Workflow Configuration

### Location

`src/agenticfleet/config/workflow.yaml`

### Structure

```yaml
fleet:
  # Manager/Orchestrator settings
  manager:
    model: gpt-5
    temperature: 0.2
    max_tokens: 4096
    instructions: |
      You are the orchestrator for a multi-agent system...

  # Orchestration limits
  orchestrator:
    max_round_count: 30      # Maximum workflow rounds
    max_stall_count: 3       # Rounds before replanning
    max_reset_count: 2       # Complete restarts allowed

  # Plan review settings
  plan_review:
    require_human_approval: false
    approval_timeout_seconds: 300

  # Callback configuration
  callbacks:
    streaming_enabled: true
    plan_logging: true
    progress_tracking: true
    tool_monitoring: true
    final_answer_capture: true

# Human-in-the-Loop settings
human_in_the_loop:
  enabled: true
  approval_timeout_seconds: 300

  # Operations requiring approval
  require_approval_for:
    - code_execution
    - file_operations
    - api_calls
    - database_operations

  # Trusted operations (auto-approved)
  trusted_operations:
    - web_search
    - data_analysis
    - read_operations

# Checkpointing settings
checkpointing:
  enabled: true
  storage_type: file  # or 'memory'
  storage_path: ./var/checkpoints
  auto_save: true
  max_checkpoints: 50
```

### Key Settings Explained

#### Orchestration Limits

```yaml
max_round_count: 30
```
- Maximum number of workflow rounds before termination
- Prevents infinite loops
- Higher values allow more complex tasks
- Typical range: 10-50

```yaml
max_stall_count: 3
```
- Number of rounds without progress before replanning
- Triggers manager to create new strategy
- Lower values = faster recovery from stuck states
- Typical range: 2-5

```yaml
max_reset_count: 2
```
- Number of complete workflow restarts allowed
- Used when replanning fails
- Higher values = more resilience
- Typical range: 1-3

#### Callback Settings

```yaml
streaming_enabled: true
```
- Enable real-time output streaming
- Shows agent responses as they're generated
- Disable for batch processing

```yaml
plan_logging: true
```
- Log manager's planning decisions
- Useful for debugging workflow logic
- Minimal performance impact

```yaml
tool_monitoring: true
```
- Track tool execution
- Audit safety-sensitive operations
- Recommended for production

---

## Agent Configuration

### Location

Per-agent configs in `src/agenticfleet/agents/<role>/config.yaml`

Example: `src/agenticfleet/agents/researcher/config.yaml`

### Structure

```yaml
agent:
  # Agent identity
  name: researcher
  description: "Specialized agent for research and information gathering"

  # Model configuration
  model: gpt-5  # Falls back to OPENAI_MODEL env var
  temperature: 0.2
  max_tokens: 4096

  # System prompt
  system_prompt: |
    You are a specialized research agent with expertise in...

    Your responsibilities:
    - Gather information from available sources
    - Summarize findings clearly and concisely
    - Cite sources when applicable

    Available tools: web_search_tool

  # Runtime flags
  stream: true          # Stream responses
  store: true           # Store in memory
  checkpoint: true      # Include in checkpoints

  # Tools configuration
  tools:
    - name: web_search_tool
      enabled: true
      config:
        max_results: 10
        timeout: 30
```

### Per-Agent Settings

#### Researcher Agent

```yaml
# src/agenticfleet/agents/researcher/config.yaml
agent:
  name: researcher
  model: gpt-5
  temperature: 0.2
  tools:
    - name: web_search_tool
      enabled: true
```

**Purpose:** Information gathering, research, summarization

#### Coder Agent

```yaml
# src/agenticfleet/agents/coder/config.yaml
agent:
  name: coder
  model: gpt-5-codex  # Specialized code model
  temperature: 0.1    # Lower for deterministic code
  tools:
    - name: code_interpreter_tool
      enabled: true
```

**Purpose:** Code generation, debugging, execution

#### Analyst Agent

```yaml
# src/agenticfleet/agents/analyst/config.yaml
agent:
  name: analyst
  model: gpt-5
  temperature: 0.3
  tools:
    - name: data_analysis_tool
      enabled: true
    - name: visualization_suggestion_tool
      enabled: true
```

**Purpose:** Data analysis, visualization, insights

---

## Tool Configuration

### Enabling/Disabling Tools

In agent config:

```yaml
tools:
  - name: web_search_tool
    enabled: true    # Enable/disable tool
    config:
      # Tool-specific configuration
      max_results: 10
      timeout: 30
```

### Tool-Specific Settings

#### Code Interpreter

```yaml
- name: code_interpreter_tool
  enabled: true
  config:
    sandbox: true          # Run in sandboxed environment
    timeout: 30            # Execution timeout (seconds)
    allowed_modules:       # Whitelist imports
      - math
      - json
      - datetime
```

#### Web Search

```yaml
- name: web_search_tool
  enabled: true
  config:
    max_results: 10       # Results per query
    timeout: 30           # Request timeout
    mock_mode: true       # Use mock data (default)
```

#### Data Analysis

```yaml
- name: data_analysis_tool
  enabled: true
  config:
    confidence_threshold: 0.7
    max_samples: 1000
```

---

## Advanced Configuration

### Custom Models Per Agent

Override default models for specific agents:

```yaml
# workflow.yaml
agents:
  researcher:
    model: gpt-4o
  coder:
    model: gpt-5-codex
  analyst:
    model: o1-preview
```

### Reasoning Effort

For o1-series models:

```yaml
agent:
  model: o1-preview
  reasoning_effort: high  # low, medium, high
```

### Token Limits

Control output length:

```yaml
agent:
  max_tokens: 2048        # Response length limit
  max_completion_tokens: 4096  # Total conversation limit
```

### Streaming Configuration

```yaml
agent:
  stream: true
  stream_options:
    include_usage: true
```

---

## Configuration Best Practices

### Development

```yaml
# Shorter iterations for faster feedback
max_round_count: 15
max_stall_count: 2

# Verbose logging
LOG_LEVEL=DEBUG
streaming_enabled: true
plan_logging: true
```

### Production

```yaml
# Longer iterations for complex tasks
max_round_count: 50
max_stall_count: 5

# Performance logging only
LOG_LEVEL=INFO
streaming_enabled: false
plan_logging: false
```

### Testing

```yaml
# Minimal rounds for fast tests
max_round_count: 5
max_stall_count: 1

# Mock external services
mock_mode: true
```

---

## Validation

### Test Configuration

Run validation after changes:

```bash
make test-config
# Or: uv run python tests/test_config.py
```

Checks:
- ✅ Environment variables present
- ✅ YAML syntax valid
- ✅ Agent models accessible
- ✅ Tools importable
- ✅ Factory functions callable

### Configuration Schema

Use the schema validator:

```python
from agenticfleet.config import validate_config

# Validate workflow config
validate_config("workflow.yaml")

# Validate agent config
validate_config("agents/researcher/config.yaml")
```

---

## Troubleshooting

### Invalid YAML Syntax

**Error:** `yaml.scanner.ScannerError`

**Fix:**
```bash
# Validate YAML syntax
uv run python -c "import yaml; yaml.safe_load(open('config/workflow.yaml'))"
```

### Missing Environment Variables

**Error:** `Environment variable X not found`

**Fix:**
```bash
# Check .env file
cat .env | grep VARIABLE_NAME

# Set temporarily
export VARIABLE_NAME=value
```

### Model Not Found

**Error:** `Model 'xyz' not found`

**Fix:**
- Check model name spelling
- Verify API key has access to model
- Fall back to available model (gpt-4o, gpt-5)

---

## Examples

### Minimal Configuration

```yaml
# workflow.yaml (minimal)
fleet:
  manager:
    model: gpt-5
  orchestrator:
    max_round_count: 20
```

### Full Production Configuration

See `config/workflow.yaml` for complete example with all options.

---

## Next Steps

- **[Agent Guide](../guides/agents.md)** – Customize agent behavior
- **[HITL Configuration](../guides/human-in-the-loop.md)** – Set up approvals
- **[Tool Development](../advanced/tool-development.md)** – Create custom tools

---

**Questions?** See [Troubleshooting](../runbooks/troubleshooting.md) or [open an issue](https://github.com/Qredence/agentic-fleet/issues).
