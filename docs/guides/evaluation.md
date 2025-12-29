# Evaluation Framework Guide

The evaluation framework enables batch assessment of multi-agent workflow performance across a dataset of tasks using configurable metrics. This guide covers both standard evaluation and history-based evaluation workflows.

## Overview

The evaluation framework allows you to:

- **Quantify workflow quality** and consistency across multiple tasks
- **Track regressions** or improvements over time
- **Detect output drift** by comparing against baseline snapshots
- **Provide actionable signals** for routing, refinement, and self-improvement

## Quick Start

### Standard Evaluation

```bash
# Run evaluation on a dataset
uv run python console.py evaluate --max-tasks 5
```

### History-Based Evaluation

```bash
# 1. Extract evaluation dataset from execution history
uv run python scripts/create_history_evaluation.py

# 2. Run evaluation on historical tasks
uv run python console.py evaluate \
  --dataset data/history_evaluation_tasks.jsonl \
  --max-tasks 5
```

## Dataset Format

A dataset is a JSONL file (`*.jsonl`) with one JSON object per line:

```jsonl
{"id": "task1", "message": "Research benefits of multi-agent workflows", "keywords": ["multi-agent", "workflow", "benefits"]}
{"id": "task2", "message": "Explain DSPy routing advantages", "keywords": ["DSPy", "routing", "advantages"]}
```

**Fields:**

| Field              | Required | Description                                    |
| ------------------ | -------- | ---------------------------------------------- |
| `id`               | no       | Unique identifier (auto-assigned if missing)   |
| `message` / `task` | yes      | Input passed to workflow.run()                 |
| `keywords`         | no       | Keywords required for `keyword_success` metric |
| `required_tools`   | no       | Reserved for future tool usage metrics         |

**History Evaluation Format:**

When extracted from history, tasks include additional fields:

```json
{
  "task": "what is quantum computing",
  "expected_output": "Quantum computing uses quantum-mechanical phenomena...",
  "expected_quality_score": 7.0,
  "expected_keywords": [
    "algorithm",
    "computing",
    "entanglement",
    "quantum",
    "qubit"
  ],
  "metadata": {
    "history_index": 4,
    "execution_time": 67.13,
    "complexity": "moderate",
    "routing_mode": "sequential"
  }
}
```

## Configuration

Enable and tune via `src/agentic_fleet/config/workflow_config.yaml`:

```yaml
evaluation:
  enabled: true
  dataset_path: data/evaluation_tasks.jsonl
  output_dir: .var/logs/evaluation
  metrics:
    - quality_score
    - keyword_success
    - latency_seconds
    - routing_efficiency
    - refinement_triggered
    - relevance_score
    - token_count
    - estimated_cost_usd
    - output_drift
  max_tasks: 0 # 0 = no limit
  stop_on_failure: false
```

## Metrics

### Core Metrics

| Metric                 | Type  | Description                                                   |
| ---------------------- | ----- | ------------------------------------------------------------- |
| `quality_score`        | float | Internal quality score parsed from workflow metadata (0-10)   |
| `keyword_success`      | 0/1   | All listed `keywords` found in output text (case-insensitive) |
| `latency_seconds`      | float | Workflow execution time per task                              |
| `routing_efficiency`   | float | Unique agents used / assigned (proxy for efficiency)          |
| `refinement_triggered` | 0/1   | Refinement suggestions present in metadata                    |

### Enhanced Metrics (Option B Upgrade)

| Metric               | Type        | Description                                                                                |
| -------------------- | ----------- | ------------------------------------------------------------------------------------------ |
| `relevance_score`    | float (0–1) | Fraction of provided keywords found in the output (semantic coverage proxy)                |
| `token_count`        | int         | Approximate token count via lightweight regex tokenizer                                    |
| `estimated_cost_usd` | float       | Estimated model cost using flat blended rate (0.0005 / 1K tokens)                          |
| `output_drift`       | 0/1/None    | Drift indicator vs baseline snapshot hash (0 = identical, 1 = changed, None = no baseline) |

**Interpreting Results:**

- High `relevance_score` with low `quality_score`: coverage without depth → refine.
- Rising `token_count` and stable `quality_score`: verbosity creep.
- `output_drift=1` + improved `quality_score`: beneficial evolution.
- `output_drift=1` + decreased `quality_score`: investigate regression.
- Increasing `estimated_cost_usd` without quality gains: optimize routing or reduce unnecessary refinement.

## Running Evaluations

### Standard Evaluation

```bash
# Run with defaults from config
uv run agentic-fleet evaluate

# Limit number of tasks
uv run agentic-fleet evaluate --max-tasks 5

# Custom dataset
uv run agentic-fleet evaluate --dataset data/custom_eval.jsonl

# Override metrics
uv run agentic-fleet evaluate --metrics quality_score,latency_seconds

# Early stop on failed success metric
uv run agentic-fleet evaluate --stop-on-failure
```

### History-Based Evaluation

```bash
# 1. Extract evaluation dataset from history
uv run python scripts/create_history_evaluation.py

# 2. Run evaluation
uv run agentic-fleet evaluate \
  --dataset data/history_evaluation_tasks.jsonl \
  --max-tasks 10

# 3. Review results
cat .var/logs/evaluation/evaluation_summary.json
```

## Output Artifacts

| File                                           | Purpose                                |
| ---------------------------------------------- | -------------------------------------- |
| `.var/logs/evaluation/evaluation_report.jsonl` | Per-task metrics (stream friendly)     |
| `.var/logs/evaluation/evaluation_summary.json` | Aggregated statistics (means, min/max) |
| `.var/logs/evaluation/baseline_snapshot.json`  | First-run canonical output hashes      |

## Baseline Snapshots

On first evaluation run, a baseline snapshot is created at `.var/logs/evaluation/baseline_snapshot.json`:

**What it stores:**

- Output hashes for each task
- Timestamp of baseline creation
- Metric values at baseline

**Detecting drift:**

- Subsequent runs compare current output hashes against baseline
- `output_drift` metric is `true` if hash differs, `false` if identical
- Review drifted tasks manually to determine if changes are improvements or regressions

**Resetting baseline:**

```bash
# Delete old baseline
rm .var/logs/evaluation/baseline_snapshot.json

# Next evaluation run creates new baseline
uv run agentic-fleet evaluate \
  --dataset data/history_evaluation_tasks.jsonl \
  --max-tasks 5
```

## Programmatic Usage

```python
import asyncio
from agentic_fleet.evaluation import Evaluator
from agentic_fleet.utils.config_loader import load_config
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

async def main():
    cfg = load_config()
    async def wf_factory():
        workflow = await create_supervisor_workflow(compile_dspy=False)
        return workflow

    evaluator = Evaluator(
        workflow_factory=wf_factory,
        dataset_path=cfg["evaluation"]["dataset_path"],
        output_dir=cfg["evaluation"]["output_dir"],
        metrics=cfg["evaluation"]["metrics"],
    )
    summary = await evaluator.run()
    print(summary)

asyncio.run(main())
```

## Extending Metrics

Add a new function to `src/agentic_fleet/evaluation/metrics.py`:

```python
def metric_custom(task, metadata):
    """Custom metric that returns a numeric value."""
    # Your logic here
    return value

METRIC_FUNCS["custom"] = metric_custom
```

Then include `custom` in `evaluation.metrics` list in your config.

## History-Based Evaluation Workflow

### Regular Regression Testing

Add to your development workflow:

```bash
# After making framework changes
uv run pytest -q  # Run unit tests first

# Then evaluate on historical tasks
uv run agentic-fleet evaluate \
  --dataset data/history_evaluation_tasks.jsonl \
  --max-tasks 10

# Review summary for unexpected changes
cat .var/logs/evaluation/evaluation_summary.json
```

### Updating the Evaluation Dataset

Re-extract from history after significant runs:

```bash
# Add new workflow executions to history.jsonl (happens automatically)
uv run agentic-fleet run -m "New complex task"

# Re-extract evaluation dataset to include new tasks
uv run python scripts/create_history_evaluation.py

# Re-run evaluation with expanded dataset
uv run agentic-fleet evaluate \
  --dataset data/history_evaluation_tasks.jsonl
```

## Best Practices

1. **Keep datasets small and focused** (10–50 tasks) for rapid iteration
2. **Track historical summaries** (commit `evaluation_summary.json` snapshots) to detect regressions
3. **Pair evaluations with self-improvement** (`agentic-fleet self-improve`) for continuous routing optimization
4. **Disable tracing** if evaluating latency exclusively (`tracing.enabled: false`)
5. **Use history evaluation** for regression testing after code changes
6. **Reset baseline** after intentional improvements to outputs

## Troubleshooting

| Issue                             | Cause                                | Resolution                                                      |
| --------------------------------- | ------------------------------------ | --------------------------------------------------------------- |
| Empty summary                     | Dataset path incorrect               | Verify `evaluation.dataset_path` exists                         |
| Keywords not detected             | Case mismatch or punctuation         | Ensure keywords lowercase or adjust list                        |
| Low routing efficiency always 1.0 | Proxy metric needs enhancement       | Extend metric to track actual agent event usage                 |
| Empty or small dataset            | Insufficient history records         | Run more workflow tasks to populate history                     |
| All metrics null                  | Metric functions not implemented     | Check `src/evaluation/metrics.py` for active implementations    |
| High output drift                 | Model non-determinism or regressions | Manually review drifted outputs; reset baseline if improvements |

## Roadmap

- Tool usage metrics (required vs. actual tools)
- Content style/readability metrics
- Statistical significance tracking across runs
- Confidence threshold drift detection
- LLM-judged semantic relevance, groundedness, coherence
- Agent/tool usage analytics

## DSPy-Based History Evaluation Script

For quick evaluation of execution history without running the full evaluation framework, use the standalone `evaluate_history.py` script:

### Quick Start

```bash
# Evaluate all records in execution_history.jsonl
uv run python scripts/evaluate_history.py
```

### What It Does

1. **Reads** `.var/logs/execution_history.jsonl` (task + result pairs)
2. **Scores** each interaction using DSPy's `ChainOfThought` with an `AnswerQuality` signature
3. **Outputs** results to `.var/logs/evaluation_results.jsonl`

### Scoring Rubric

The script uses an explicit rubric prioritizing correctness:

| Score | Meaning                                      |
| ----- | -------------------------------------------- |
| 9-10  | Correct, complete, and well-formatted        |
| 7-8   | Correct with minor omissions or style issues |
| 5-6   | Partially correct or incomplete              |
| 3-4   | Mostly incorrect but shows understanding     |
| 1-2   | Incorrect, irrelevant, or fails to answer    |

**Key principle:** For simple factual tasks (math, definitions), a correct short answer scores 9-10.

### Output Format

Each result includes:

```json
{
  "workflow_id": "abc-123",
  "task": "What is 2+2?",
  "result": "4",
  "dspy_score": 10.0,
  "dspy_is_correct": "yes",
  "dspy_is_complete": "yes",
  "dspy_reasoning": "The answer is correct and complete.",
  "existing_score": 10.0
}
```

### High-Quality Dataset Export

After evaluation, extract high-scoring examples for DSPy training:

```bash
# Filter examples with score >= 7 and correct answers
# (automatically created during evaluation analysis)
cat .var/logs/high_quality_examples.jsonl
```

### Configuration

The script uses `gpt-5-nano` by default. To change the model, edit `scripts/evaluate_history.py`:

```python
lm = dspy.LM(model="openai/gpt-5-mini", api_key=api_key)  # or other model
```

## Related Documentation

- [DSPy Optimizer Guide](dspy-optimizer.md) - Using optimization with evaluation
- [Self-Improvement Guide](../users/self-improvement.md) - Learning from evaluation results
- [Logging and History Guide](logging-history.md) - Understanding execution history
