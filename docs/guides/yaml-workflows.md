# YAML Workflow Configuration Guide

## Overview

AgenticFleet supports declarative workflow configuration using YAML files, allowing you to define multi-agent workflows without writing Python code. This approach is ideal for:

- Non-Python users who want to configure workflows
- Rapid prototyping and experimentation
- Version-controlled workflow definitions
- Standardized workflow templates

## Quick Start

### 1. Define Workflow in YAML

Create a file `my_workflow.yaml`:

```yaml
name: "My Research Workflow"

orchestrator:
  max_round_count: 10
  max_stall_count: 3
  max_reset_count: 2

manager:
  model: "gpt-4o"
  instructions: |
    You are coordinating specialized AI agents to complete user tasks.

    Available agents:
    - researcher: Searches for information and gathers data
    - coder: Writes and executes Python code for analysis

    Break down tasks into clear steps and delegate to the right agent.

agents:
  - name: researcher
    type: ChatAgent
    model: "gpt-4o-search-preview"
    description: "Searches for information using web search"

  - name: coder
    type: ChatAgent
    model: "gpt-4o"
    description: "Executes Python code for data analysis"
    tools:
      - type: HostedCodeInterpreterTool

callbacks:
  streaming_enabled: true
  log_progress_ledger: true

checkpointing:
  enabled: false
  storage_path: "./checkpoints"

plan_review:
  enabled: false
  require_human_approval: false
```

### 2. Load and Run in Python

```python
from agenticfleet.fleet import load_and_build_workflow

# One-step load and build
workflow = load_and_build_workflow("my_workflow.yaml")

# Run the workflow
result = await workflow.run("Your task here")
print(result)
```

### 3. Load and Run in Jupyter Notebook

See `notebooks/yaml_workflow.ipynb` for a complete example with streaming events.

## Configuration Reference

### Required Fields

#### `name`

Workflow display name.

```yaml
name: "Research and Analysis Workflow"
```

#### `orchestrator`

Controls workflow execution limits.

```yaml
orchestrator:
  max_round_count: 10 # Max total agent interactions
  max_stall_count: 3 # Max consecutive rounds without progress (triggers replan)
  max_reset_count: 2 # Max complete replans before giving up
```

#### `manager`

Configures the planner/orchestrator agent.

```yaml
manager:
  model: "gpt-4o"
  instructions: |
    Multi-line instructions for the manager.
    Explain available agents and delegation strategy.
```

#### `agents`

List of specialist agents.

```yaml
agents:
  - name: researcher # Unique agent name (stable for checkpoints)
    type: ChatAgent # Currently only ChatAgent supported
    model: "gpt-4o" # Model ID (search models use OpenAIChatClient)
    description: "Agent role" # Optional description
    instructions: "..." # Optional agent-specific instructions
    tools: # Optional list of tools
      - type: HostedCodeInterpreterTool
```

**Model Selection Logic:**

- Models with "search" in name → `OpenAIChatClient` (for web search preview models)
- All other models → `OpenAIResponsesClient` (standard chat)

### Optional Fields

#### `callbacks`

Controls workflow observability.

```yaml
callbacks:
  streaming_enabled: true # Stream agent responses in real-time
  log_progress_ledger: true # Log manager's progress evaluations
```

#### `checkpointing`

Enables state persistence for long-running workflows.

```yaml
checkpointing:
  enabled: true
  storage_path: "./checkpoints"
```

**Benefits:**

- Resume after interruptions
- 50-80% cost savings on retries
- Post-mortem debugging

#### `plan_review`

Enables human-in-the-loop plan approval.

```yaml
plan_review:
  enabled: true
  require_human_approval: true
```

**When enabled:**

- Manager prompts for approval before executing plans
- Supports approve/reject/modify decisions

## Advanced Usage

### Programmatic Loading

For more control, use the step-by-step approach:

```python
from agenticfleet.fleet import (
    load_workflow_from_yaml,
    build_workflow_from_config,
)
from agenticfleet.fleet.callbacks import ConsoleCallbacks

# Step 1: Load YAML configuration
config = load_workflow_from_yaml("my_workflow.yaml")

# Step 2: Customize callbacks
callbacks = ConsoleCallbacks()

# Step 3: Build workflow
workflow = build_workflow_from_config(config, console_callbacks=callbacks)

# Step 4: Run with streaming
async for event in workflow.run_stream("Task description"):
    # Process events
    if isinstance(event, WorkflowOutputEvent):
        print(event.data)
```

### Custom Checkpointing

```python
from agent_framework import FileCheckpointStorage
from agenticfleet.fleet import load_workflow_from_yaml, build_workflow_from_config

config = load_workflow_from_yaml("my_workflow.yaml")

# Custom checkpoint storage
storage = FileCheckpointStorage("/custom/path/checkpoints")

# Override config checkpointing
workflow = build_workflow_from_config(config, checkpoint_storage=storage)
```

## Tool Configuration

### Currently Supported Tools

#### HostedCodeInterpreterTool

Executes Python code in a sandboxed environment.

```yaml
agents:
  - name: coder
    tools:
      - type: HostedCodeInterpreterTool
```

**Note:** Tool configuration is currently basic. For advanced tool customization, use the Python FleetBuilder API.

### Adding Custom Tools

The workflow loader will be extended to support custom tool configuration. For now, define custom tools in agent factory functions and use the Python API.

## Best Practices

### 1. Stable Agent Names

Keep agent names consistent across workflow versions for checkpoint compatibility:

```yaml
# ✅ Good - stable names
agents:
  - name: researcher
  - name: coder

# ❌ Bad - changing names breaks checkpoints
agents:
  - name: researcher_v2
  - name: code_executor
```

### 2. Clear Manager Instructions

Provide explicit delegation rules:

```yaml
manager:
  instructions: |
    You coordinate these agents:

    1. researcher: Use for web search, gathering facts, finding sources
       - When to use: "Find information about...", "Research..."

    2. coder: Use for data analysis, calculations, visualizations
       - When to use: "Calculate...", "Analyze data...", "Create chart..."

    Always break complex tasks into clear steps.
```

### 3. Model Selection

- **Search models** (`gpt-4o-search-preview`): For web research agents
- **Standard models** (`gpt-4o`): For analysis, coding, planning
- **Preview models**: Use exact names from your Azure OpenAI deployment

```yaml
agents:
  - name: researcher
    model: "gpt-4o-search-preview" # Automatically uses OpenAIChatClient

  - name: analyst
    model: "gpt-4o" # Automatically uses OpenAIResponsesClient
```

### 4. Workflow Limits

Adjust based on task complexity and cost tolerance:

```yaml
# Quick tasks (low cost)
orchestrator:
  max_round_count: 5
  max_stall_count: 2

# Complex tasks (higher cost tolerance)
orchestrator:
  max_round_count: 30
  max_stall_count: 5
```

### 5. Enable Checkpointing for Long Tasks

```yaml
checkpointing:
  enabled: true # ← Enable for tasks > 10 rounds
```

Benefits:

- Resume after crashes
- Lower retry costs
- Better debugging

## Examples

### Example 1: Simple Research Workflow

```yaml
name: "Quick Research"

orchestrator:
  max_round_count: 5

manager:
  model: "gpt-4o"
  instructions: "You coordinate a researcher agent. Delegate search tasks to them."

agents:
  - name: researcher
    model: "gpt-4o-search-preview"
    description: "Searches for information"

callbacks:
  streaming_enabled: true
```

### Example 2: Data Analysis Workflow

```yaml
name: "Data Analysis Pipeline"

orchestrator:
  max_round_count: 15
  max_stall_count: 3

manager:
  model: "gpt-4o"
  instructions: |
    You coordinate coder and analyst agents.
    - coder: Runs Python for data processing
    - analyst: Reviews results and draws conclusions

agents:
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool

  - name: analyst
    model: "gpt-4o"

callbacks:
  streaming_enabled: true
  log_progress_ledger: true

checkpointing:
  enabled: true
  storage_path: "./analysis_checkpoints"
```

### Example 3: Production Workflow with HITL

```yaml
name: "Production Research Workflow"

orchestrator:
  max_round_count: 20
  max_stall_count: 4
  max_reset_count: 2

manager:
  model: "gpt-4o"
  instructions: |
    Production-grade coordinator with full observability.

agents:
  - name: researcher
    model: "gpt-4o-search-preview"
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool
  - name: analyst
    model: "gpt-4o"

callbacks:
  streaming_enabled: true
  log_progress_ledger: true

checkpointing:
  enabled: true
  storage_path: "/var/checkpoints/production"

plan_review:
  enabled: true
  require_human_approval: true
```

## Troubleshooting

### Import Error: `agent_framework.tools.hosted_code_interpreter`

This is a type-checking warning and can be safely ignored. The tool imports at runtime when needed.

### Workflow Not Streaming

Check `callbacks.streaming_enabled` is `true` in your YAML:

```yaml
callbacks:
  streaming_enabled: true # ← Must be true for streaming
```

### Agent Names Changed, Checkpoints Don't Work

Agent names must remain stable. If you changed names:

1. Update agent names back to original values
2. Or delete old checkpoints and start fresh

### Wrong Model Client Used

The loader auto-detects based on model name:

- "search" in name → `OpenAIChatClient`
- Everything else → `OpenAIResponsesClient`

Override by using the Python API for custom client configuration.

## API Reference

### `load_workflow_from_yaml(yaml_path)`

Load YAML configuration file.

**Parameters:**

- `yaml_path` (str | Path): Path to YAML file

**Returns:**

- `dict[str, Any]`: Parsed configuration dictionary

**Raises:**

- `FileNotFoundError`: YAML file doesn't exist
- `yaml.YAMLError`: Invalid YAML syntax

### `build_workflow_from_config(config, console_callbacks=None)`

Build workflow from configuration dictionary.

**Parameters:**

- `config` (dict): Configuration from `load_workflow_from_yaml()`
- `console_callbacks` (ConsoleCallbacks | None): Optional callbacks for observability

**Returns:**

- Configured Magentic workflow

### `load_and_build_workflow(yaml_path, console_callbacks=None)`

One-step load and build.

**Parameters:**

- `yaml_path` (str | Path): Path to YAML file
- `console_callbacks` (ConsoleCallbacks | None): Optional callbacks

**Returns:**

- Configured Magentic workflow ready to run

## See Also

- [Magentic Fleet Architecture](../architecture/magentic-fleet.md)
- [Magentic Fleet Features](../features/magentic-fleet.md)
- [Human-in-the-Loop Guide](./human-in-the-loop.md)
- [Checkpointing Guide](../features/checkpointing.md)
- Example workflow: `var/config/workflows/magentic_example.yaml`
- Example notebook: `notebooks/yaml_workflow.ipynb`
