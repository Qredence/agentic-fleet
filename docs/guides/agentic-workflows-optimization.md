# AgenticFleet Custom Engine & Self-Optimization

This project integrates the `agentic-fleet` core as a custom engine for GitHub Agentic Workflows (`gh-aw`). This enables a powerful feedback loop where the fleet's own intelligence is used to automate repository tasks, and the resulting execution data is used to improve the fleet.

## Custom Engine Setup

The custom engine is defined in [.github/workflows/shared/engine-fleet.md](../../.github/workflows/shared/engine-fleet.md). It allows any `.aw.md` workflow to use the `agentic-fleet` CLI instead of the default Copilot engine.

### Benefits

- **Full Control**: Use the project's specific DSPy modules and agents.
- **Multi-Provider**: Support for OpenAI, Azure OpenAI, and Gemini 3.
- **Structured Output**: Uses the `--json` flag to communicate directly with `gh-aw` safe-outputs.

## Self-Optimization Loop

When running as a custom engine, the fleet participates in two types of self-optimization:

### 1. DSPy Module Optimization

Every run captures execution history in `.var/logs/execution_history.jsonl`. You can use this data to optimize the fleet's reasoning in two ways:

#### Bootstrap Mode: Start with No Training Data

GEPA can start with zero initial training data and bootstrap entirely from execution history:

```bash
# Bootstrap mode: Use history as training data (no initial examples needed)
uv run agentic-fleet gepa-optimize --auto light --use-history
```

The system will:

1. Detect no initial training data
2. Automatically harvest high-quality executions (quality ≥8.0)
3. Convert history to training examples
4. Run GEPA optimization using history as the training dataset

#### Augmentation Mode: Enhance Existing Training

GEPA can also augment existing training data with history:

```bash
# Combine initial data + history
uv run agentic-fleet gepa-optimize \
  --examples data/supervisor_examples.json \
  --use-history \
  --history-min-quality 8.0
```

**Benefits:**

- **Cold start**: No need to manually create initial training examples
- **Self-improvement**: System learns from its own high-quality executions
- **Incremental**: Improves as more history accumulates over time

### 2. Workflow Optimization (Q)

The `q` agent ([q.md](../../.github/workflows/q.md)) analyzes logs and audits from all agentic workflows. It can:

- Identify missing tools.
- Suggest permission changes.
- Extract common patterns into shared imports.

## Using Other LLM Providers

To use Gemini 3 or other providers:

1. Set the appropriate API key (e.g., `GEMINI_API_KEY`).
2. Specify the model with a prefix in your workflow or `workflow_config.yaml`:
   ```yaml
   engine:
     model: gemini/gemini-1.5-pro
   ```
   The fleet will automatically route the request to the correct provider via LiteLLM.
