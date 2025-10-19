# YAML Workflows - Quick Reference

## 🚀 Quick Start (3 Steps)

### 1. Create YAML Configuration

```yaml
name: "My Workflow"

manager:
  model: "gpt-4o"
  instructions: "You coordinate AI agents to complete tasks."

agents:
  - name: researcher
    model: "gpt-4o-search-preview"
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool
```

### 2. Load in Python

```python
from agenticfleet.fleet import load_and_build_workflow

workflow = load_and_build_workflow("my_workflow.yaml")
```

### 3. Run Task

```python
result = await workflow.run("Research Python trends and create a chart")
print(result)
```

## 📋 Common Configurations

### Minimal (Required Fields Only)

```yaml
name: "Simple Workflow"

manager:
  model: "gpt-4o"
  instructions: "Coordinate agents"

agents:
  - name: agent1
    model: "gpt-4o"
```

### Standard (Recommended)

```yaml
name: "Standard Workflow"

orchestrator:
  max_round_count: 10

manager:
  model: "gpt-4o"
  instructions: |
    You coordinate these agents:
    - researcher: Searches for information
    - coder: Analyzes data with Python

agents:
  - name: researcher
    model: "gpt-4o-search-preview"
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool

callbacks:
  streaming_enabled: true
```

### Production (All Features)

```yaml
name: "Production Workflow"

orchestrator:
  max_round_count: 20
  max_stall_count: 4
  max_reset_count: 2

manager:
  model: "gpt-4o"
  instructions: "Detailed coordination instructions"

agents:
  - name: researcher
    model: "gpt-4o-search-preview"
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool

callbacks:
  streaming_enabled: true
  log_progress_ledger: true

checkpointing:
  enabled: true
  storage_path: "./checkpoints"

plan_review:
  enabled: true
  require_human_approval: true
```

## 🔑 Field Reference

| Field                                | Required | Default         | Description                       |
| ------------------------------------ | -------- | --------------- | --------------------------------- |
| `name`                               | ✅ Yes   | -               | Workflow display name             |
| `orchestrator.max_round_count`       | ❌ No    | 10              | Max agent interactions            |
| `orchestrator.max_stall_count`       | ❌ No    | 3               | Max stalls before replan          |
| `orchestrator.max_reset_count`       | ❌ No    | 2               | Max replans before giving up      |
| `manager.model`                      | ✅ Yes   | -               | Manager/planner model             |
| `manager.instructions`               | ✅ Yes   | -               | Manager coordination instructions |
| `agents[].name`                      | ✅ Yes   | -               | Unique agent name                 |
| `agents[].type`                      | ✅ Yes   | -               | Agent type (ChatAgent)            |
| `agents[].model`                     | ✅ Yes   | -               | Model ID                          |
| `agents[].description`               | ❌ No    | ""              | Agent role description            |
| `agents[].tools`                     | ❌ No    | []              | List of tool configurations       |
| `callbacks.streaming_enabled`        | ❌ No    | true            | Stream agent responses            |
| `callbacks.log_progress_ledger`      | ❌ No    | true            | Log progress evaluations          |
| `checkpointing.enabled`              | ❌ No    | false           | Enable state persistence          |
| `checkpointing.storage_path`         | ❌ No    | "./checkpoints" | Checkpoint directory              |
| `plan_review.enabled`                | ❌ No    | false           | Enable HITL plan review           |
| `plan_review.require_human_approval` | ❌ No    | false           | Require approval before execution |

## 💡 Tips

### Model Selection

- **Search models**: `gpt-4o-search-preview` → Auto-uses `OpenAIChatClient`
- **Standard models**: `gpt-4o`, `gpt-3.5-turbo` → Auto-uses `OpenAIResponsesClient`

### Workflow Limits

- **Quick tasks**: `max_round_count: 5`
- **Complex tasks**: `max_round_count: 20-30`
- **Adjust stalls**: Higher = more retries before giving up

### Checkpointing

Enable for:

- Long-running workflows (> 10 rounds)
- High-cost tasks (50-80% savings on retries)
- Production environments

### Agent Names

⚠️ **Keep stable** for checkpoint compatibility

- ✅ Good: `researcher`, `coder`, `analyst`
- ❌ Bad: Changing names breaks checkpoints

## 📦 API Functions

```python
from agenticfleet.fleet import (
    load_workflow_from_yaml,      # YAML → dict
    build_workflow_from_config,   # dict → workflow
    load_and_build_workflow,      # YAML → workflow (one step)
)
```

### `load_workflow_from_yaml(yaml_path)`

Returns parsed configuration dictionary.

### `build_workflow_from_config(config, console_callbacks=None)`

Builds workflow from configuration dict.

### `load_and_build_workflow(yaml_path, console_callbacks=None)`

One-step load and build (recommended for most use cases).

## 🛠️ Tools Configuration

### HostedCodeInterpreterTool

```yaml
agents:
  - name: coder
    tools:
      - type: HostedCodeInterpreterTool
```

Executes Python code in sandboxed environment.

## 📚 Examples

See:

- Template: `var/config/workflows/magentic_example.yaml`
- Notebook: `notebooks/yaml_workflow.ipynb`
- Full Guide: `docs/guides/yaml-workflows.md`

## 🐛 Troubleshooting

| Issue                                       | Solution                                              |
| ------------------------------------------- | ----------------------------------------------------- |
| No streaming                                | Set `callbacks.streaming_enabled: true`               |
| Checkpoints don't work                      | Keep agent names stable                               |
| Import error on `HostedCodeInterpreterTool` | Safe to ignore (type-checking only)                   |
| Wrong model client                          | Auto-detected from model name ("search" → ChatClient) |

## 🎯 Common Use Cases

### Research Workflow

```yaml
agents:
  - name: researcher
    model: "gpt-4o-search-preview"
```

### Data Analysis Workflow

```yaml
agents:
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool
```

### Multi-Agent Pipeline

```yaml
agents:
  - name: researcher
    model: "gpt-4o-search-preview"
  - name: coder
    model: "gpt-4o"
    tools:
      - type: HostedCodeInterpreterTool
  - name: analyst
    model: "gpt-4o"
```

## ✅ Validation

```bash
# Test configuration
uv run python tests/test_config.py

# Verify loader
uv run python -c "from agenticfleet.fleet import load_and_build_workflow; print('OK')"
```
