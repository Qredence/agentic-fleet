# DSPy Optimizer Guide

## Overview

DSPy optimizers automatically improve your prompts and workflows by learning from training examples. This framework supports two optimization strategies:

1. **BootstrapFewShot** (default) - Fast, simple few-shot learning
2. **GEPA** (Generative Prompt Adapter) - Advanced prompt evolution with reflection

## Quick Start

### Enable Optimization

Set in `config/workflow_config.yaml`:

```yaml
dspy:
  optimization:
    enabled: true # Enable compilation
    examples_path: data/supervisor_examples.json
```

### Using BootstrapFewShot (Default)

```bash
# Run workflow - optimization happens automatically
uv run agentic-fleet run -m "Your task here"
```

The framework will:

1. Load training examples from `data/supervisor_examples.json`
2. Compile the reasoner using BootstrapFewShot
3. Cache the optimized module at `logs/compiled_supervisor.pkl`
4. Use the optimized module for all task routing

### Using GEPA Optimizer

```yaml
dspy:
  optimization:
    enabled: true
    use_gepa: true # Switch to GEPA
    gepa_auto: light # or 'medium', 'heavy'
```

Or use the CLI command:

```bash
# Run GEPA optimization once (auto light effort)
uv run agentic-fleet gepa-optimize --auto light

# Alternate: explicit iteration budget (disables --auto)
uv run agentic-fleet gepa-optimize --max-full-evals 60

# Alternate: explicit metric call budget (disables --auto)
uv run agentic-fleet gepa-optimize --max-metric-calls 120

# With history augmentation (still exclusive selection of ONE strategy)
uv run agentic-fleet gepa-optimize --auto medium --use-history --history-min-quality 9.0
```

## Understanding the Optimizers

### BootstrapFewShot

**What it does:**

- Selects best examples from training data
- Adds them as few-shot demonstrations to prompts
- Fast compilation (seconds)
- Good for stable, predictable improvements

**When to use:**

- You have 10-50 good training examples
- You want quick, reliable optimization
- You're just starting with DSPy

**Configuration (choose ONE strategy):**

```yaml
dspy:
  optimization:
    enabled: true
    use_gepa: false # Use BootstrapFewShot
    examples_path: data/supervisor_examples.json
    max_bootstrapped_demos: 4 # Number of examples per prompt
    metric_threshold: 0.8 # Minimum accuracy threshold
```

### GEPA (Generative Prompt Adapter)

**What it does:**

- **Evolves** prompt instructions through reflection
- Generates new examples and tests variations
- Uses a validation set to prevent overfitting
- Slower but can achieve better results

**When to use:**

- You want the best possible performance
- You have time for longer optimization (minutes)
- You have diverse training examples
- BootstrapFewShot results are insufficient

**Configuration:**

```yaml
dspy:
  optimization:
    enabled: true
    use_gepa: true
    # Strategy A (recommended): auto effort level
    gepa_auto: light
    # Strategy B: explicit full eval count (comment out gepa_auto)
    # gepa_max_full_evals: 50
    # Strategy C: explicit metric call count (comment out gepa_auto)
    # gepa_max_metric_calls: 150
    gepa_log_dir: logs/gepa
    gepa_perfect_score: 1.0
    gepa_val_split: 0.2
    gepa_seed: 13
    # Enhanced GEPA settings
    gepa_latency_weight: 0.2 # Penalize slow predictions
    gepa_feedback_weight: 0.7 # Weight of feedback vs metric
```

**Important:** Only set ONE of these:

- `gepa_auto: light/medium/heavy` (recommended)
- `gepa_max_full_evals: <number>`
- `gepa_max_metric_calls: <number>`

## Training Data Format

Create `data/supervisor_examples.json`:

```json
[
  {
    "task": "Research quantum computing applications",
    "team": "Researcher: Web search, citations\nAnalyst: Data analysis\nWriter: Documentation",
    "assigned_to": "Researcher,Analyst",
    "execution_mode": "sequential"
  },
  {
    "task": "2+2",
    "team": "Researcher: Web search\nAnalyst: Math\nWriter: Docs",
    "assigned_to": "Analyst",
    "execution_mode": "delegated"
  }
]
```

**Required fields:**

- `task` - The user request
- `team` - Available agents and their capabilities
- `assigned_to` - Comma-separated agent names
- `execution_mode` - One of: `sequential`, `parallel`, `delegated`

**Optional fields:**

- `tool_requirements` - List of required tools
- `complexity` - Task complexity level

### Using Execution History as Training Data

GEPA can augment training with high-quality runs from your execution history:

```yaml
dspy:
  optimization:
    use_gepa: true
    gepa_use_history_examples: true # Enable history harvesting
    gepa_history_min_quality: 8.0 # Minimum quality score (0-10)
    gepa_history_limit: 200 # Max examples from history
```

This automatically:

1. Scans `logs/execution_history.jsonl`
2. Extracts runs with `quality.score >= 8.0`
3. Converts them to training examples
4. Adds them to your base examples

## Optimization Metrics

The framework uses a **routing metric** to evaluate optimization:

```python
def routing_metric(example, prediction, trace=None):
    # Check if correct agents assigned
    example_agents = set(example.assigned_to.split(','))
    predicted_agents = set(prediction.assigned_to.split(','))
    correct_assignment = example_agents == predicted_agents

    # Check if correct execution mode
    correct_mode = example.execution_mode == prediction.execution_mode

    # Combined score (80% routing, 20% tools)
    base_score = float(correct_assignment and correct_mode)
    tool_score = 1.0  # Could check tool usage

    # Assertion penalty (if trace available)
    assertion_penalty = 0.0
    if trace and hasattr(trace, 'assertion_failures'):
        assertion_penalty = len(trace.assertion_failures) * 0.1

    return max(0.0, base_score * 0.8 + tool_score * 0.2 - assertion_penalty)
```

**Interpretation:**

- 1.0 = Perfect routing decision
- 0.8 = Correct agents or mode, not both
- 0.0 = Wrong agents and mode
- <0.8 = Penalized for assertion failures (e.g., invalid agent count)

## Cache Management

### Understanding the Cache

Compiled modules are cached at `logs/compiled_supervisor.pkl` to avoid recompilation:

```bash
# View cache info
ls -lh logs/compiled_supervisor.pkl*

# Cache files:
# - compiled_supervisor.pkl       # Pickled module
# - compiled_supervisor.pkl.meta  # Metadata (version, timestamp)
```

### Cache Invalidation

Cache is automatically invalidated when:

- Training examples file (`data/supervisor_examples.json`) is modified
- Optimizer type changes (bootstrap ↔ GEPA)
- Cache version changes (code updates)

### Manual Cache Management

```bash
# Clear cache (forces recompilation)
rm logs/compiled_supervisor.pkl*

# Next run will recompile
uv run agentic-fleet run -m "Test task"
```

Or use the Python API:

```python
from src.agentic_fleet.utils.compiler import clear_cache, get_cache_info

# Get cache metadata
info = get_cache_info()
print(info)
# {
#   'cache_path': 'logs/compiled_supervisor.pkl',
#   'cache_size_bytes': 45678,
#   'cache_mtime': '2025-11-07T10:30:00',
#   'optimizer': 'gepa',
#   'version': 1
# }

# Clear cache
clear_cache()
```

## Workflow Integration

### Automatic Compilation

When you run a workflow, compilation happens automatically during initialization:

```python
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

# Workflow reads config/workflow_config.yaml
workflow = await create_supervisor_workflow()  # Compiles supervisor here

# Run with optimized module
result = await workflow.run("Your task")
```

### Disabling Optimization

For testing or development:

```yaml
dspy:
  optimization:
    enabled: false # Skip compilation
```

Or programmatically:

```python
workflow = await create_supervisor_workflow(compile_dspy=False)
```

## CLI Commands

### Run with Optimization

```bash
# Standard run (uses cached compiled module if available)
uv run agentic-fleet run -m "Analyze multi-agent benefits"

# Force recompilation
rm logs/compiled_supervisor.pkl
uv run agentic-fleet run -m "Same task"
```

### GEPA Optimization

```bash
# Run GEPA optimization and save
uv run agentic-fleet gepa-optimize

# With options
uv run agentic-fleet gepa-optimize \
  --examples data/supervisor_examples.json \
  --auto light \
  --use-history \
  --history-min-quality 8.5 \
  --history-limit 150 \
  --val-split 0.25
```

### Cache Management

```bash
# View cache status
ls -lh logs/compiled_supervisor.pkl*

# Clear cache
rm logs/compiled_supervisor.pkl*

# View GEPA logs
cat logs/gepa/*.log
```

## Best Practices

### 1. Start with BootstrapFewShot

```yaml
dspy:
  optimization:
    enabled: true
    use_gepa: false
    max_bootstrapped_demos: 4
```

Benefits:

- Fast compilation
- Predictable improvements
- Easy to debug

### 2. Curate Quality Training Examples

**Good example:**

```json
{
  "task": "Research AI safety regulations in EU",
  "team": "Researcher: Web search\nAnalyst: Analysis\nWriter: Reports",
  "assigned_to": "Researcher,Analyst,Writer",
  "execution_mode": "sequential"
}
```

**Why it's good:**

- Specific, realistic task
- Clear agent assignments
- Correct execution mode for the workflow

**Bad example:**

```json
{
  "task": "Do something",
  "team": "Agents",
  "assigned_to": "Someone",
  "execution_mode": "maybe"
}
```

### 3. Diversify Your Examples

Include examples covering:

- Simple tasks (math, facts)
- Moderate tasks (research, analysis)
- Complex tasks (multi-step workflows)
- Different execution modes (sequential, parallel, delegated)
- Various tool requirements

### 4. Use GEPA for Fine-Tuning

After BootstrapFewShot works well:

```yaml
dspy:
  optimization:
    use_gepa: true
    gepa_auto: light # Start conservative
    gepa_use_history_examples: true
```

### 5. Monitor Optimization

Check GEPA logs for insights:

```bash
# View optimization progress
tail -f logs/gepa/optimization.log

# Check if optimization improved metrics
grep "Final metric" logs/gepa/optimization.log
```

### 6. Version Your Examples

Track changes to training data:

```bash
# Version control your examples
git add data/supervisor_examples.json
git commit -m "Add 5 new sequential workflow examples"

# Tag successful optimization runs
git tag -a v1.0-optimized -m "GEPA optimization run 2025-11-07"
```

## Troubleshooting

### Cache Not Being Used

**Symptom:** Every run recompiles

**Causes:**

1. Examples file modified → intentional recompilation
2. Cache metadata missing or corrupt
3. Optimizer changed in config

**Solution:**

```bash
# Check cache validity
python -c "
from src.agentic_fleet.utils.compiler import get_cache_info
print(get_cache_info())
"
```

### GEPA Fails to Compile

**Error:** `Exactly one of max_metric_calls, max_full_evals, auto must be set`

**Cause:** Multiple GEPA limits configured

**Solution:** Use only ONE of these:

```yaml
dspy:
  optimization:
    gepa_auto: light # ← Use this
    # gepa_max_full_evals: 50  # ← Don't set
    # gepa_max_metric_calls: 150  # ← Don't set
```

### Low Optimization Scores

**Symptom:** Metric scores below 0.5

**Causes:**

1. Inconsistent training examples
2. Too few examples
3. Examples don't match actual usage

**Solutions:**

1. Review and clean training data
2. Add more diverse examples (aim for 20+)
3. Use execution history to supplement:
   ```yaml
   gepa_use_history_examples: true
   gepa_history_min_quality: 7.0
   ```

### Long Compilation Time

**Symptom:** GEPA takes >5 minutes

**Causes:**

1. `gepa_auto: heavy` or high eval limits
2. Large training dataset
3. Complex metric function

**Solutions:**

1. Use `gepa_auto: light` for faster runs
2. Reduce `gepa_history_limit` if using history
3. Lower `gepa_max_full_evals` to 30-50

## Advanced Topics

### Custom Metrics

Edit `src/agentic_fleet/utils/compiler.py` to define custom routing metrics:

```python
def routing_metric(example, prediction, trace=None):
    # Your custom scoring logic
    agent_match = example.assigned_to == prediction.assigned_to
    mode_match = example.execution_mode == prediction.execution_mode

    # Custom: penalize wrong tool selection
    tool_penalty = 0.0
    if hasattr(example, 'tool_requirements'):
        # Check if predicted tools match required tools
        tool_penalty = 0.1 if not tools_match(example, prediction) else 0.0

    score = float(agent_match and mode_match)
    return max(0.0, score - tool_penalty)
```

### Programmatic Compilation

Use the compiler directly:

```python
from src.agentic_fleet.utils.compiler import compile_supervisor
from src.agentic_fleet.dspy_modules.reasoner import DSPyReasoner

# Create supervisor
supervisor = DSPyReasoner()

# Compile with BootstrapFewShot
compiled = compile_supervisor(
    supervisor,
    examples_path="data/supervisor_examples.json",
    optimizer="bootstrap",
    use_cache=True
)

# Or compile with GEPA
compiled = compile_supervisor(
    supervisor,
    examples_path="data/supervisor_examples.json",
    optimizer="gepa",
    gepa_options={
        "auto": "medium",
        "use_history_examples": True,
        "history_min_quality": 8.5,
        "history_limit": 100,
        "val_split": 0.2
    }
)
```

### A/B Testing Optimizers

Compare BootstrapFewShot vs. GEPA:

```bash
# Test BootstrapFewShot
vim config/workflow_config.yaml  # Set use_gepa: false
rm logs/compiled_supervisor.pkl
uv run python console.py evaluate --dataset data/evaluation_tasks.jsonl
mv logs/evaluation/evaluation_summary.json results_bootstrap.json

# Test GEPA
vim config/workflow_config.yaml  # Set use_gepa: true
rm logs/compiled_supervisor.pkl
uv run python console.py evaluate --dataset data/evaluation_tasks.jsonl
mv logs/evaluation/evaluation_summary.json results_gepa.json

# Compare
python -c "
import json
b = json.load(open('results_bootstrap.json'))
g = json.load(open('results_gepa.json'))
print('Bootstrap avg quality:', b['metrics']['quality_score']['mean'])
print('GEPA avg quality:', g['metrics']['quality_score']['mean'])
"
```

## Typed Signatures & Assertions (v0.6.9+)

### Typed Pydantic Output Models

DSPy 3.x supports Pydantic models as output field types, providing:

- JSON schema enforcement
- Automatic validation and type coercion
- Better error messages on parse failures

**Enable typed signatures** (default: enabled):

```yaml
dspy:
  optimization:
    use_typed_signatures: true # Use Pydantic output models
```

**Available typed signatures:**

| Signature                 | Output Model               | Purpose                                 |
| ------------------------- | -------------------------- | --------------------------------------- |
| `TypedTaskAnalysis`       | `TaskAnalysisOutput`       | Task complexity and capability analysis |
| `TypedTaskRouting`        | `RoutingDecisionOutput`    | Agent assignment and execution mode     |
| `TypedEnhancedRouting`    | `RoutingDecisionOutput`    | Advanced routing with tool planning     |
| `TypedQualityAssessment`  | `QualityAssessmentOutput`  | Result quality scoring                  |
| `TypedProgressEvaluation` | `ProgressEvaluationOutput` | Progress evaluation with action         |
| `TypedToolPlan`           | `ToolPlanOutput`           | Tool execution ordering                 |
| `TypedWorkflowStrategy`   | `WorkflowStrategyOutput`   | Workflow mode selection                 |

**Output model example:**

```python
from agentic_fleet.dspy_modules.typed_models import RoutingDecisionOutput

# Models validate and normalize automatically
decision = RoutingDecisionOutput(
    assigned_to="Writer, Researcher",  # Auto-coerced to list
    execution_mode="DELEGATED",        # Auto-normalized to lowercase
    reasoning="Simple writing task",
)

assert decision.assigned_to == ["Writer", "Researcher"]
assert decision.execution_mode == "delegated"
```

### DSPy Assertions for Routing Validation

Assertions enable automatic retries with refined prompts when outputs don't meet constraints.

**Hard assertions** (will retry on failure):

```python
from agentic_fleet.dspy_modules.assertions import (
    assert_valid_agents,
    assert_valid_tools,
    assert_mode_agent_consistency,
)

# Validate agents exist in team
assert_valid_agents(["Writer"], ["Writer", "Researcher"])  # OK
assert_valid_agents(["Unknown"], ["Writer", "Researcher"])  # Fails

# Validate tools are available
assert_valid_tools(["TavilySearchTool"], ["TavilySearchTool", "Browser"])  # OK

# Validate mode matches agent count
from agentic_fleet.utils.models import ExecutionMode
assert_mode_agent_consistency(ExecutionMode.DELEGATED, 1)  # OK (delegated = 1 agent)
assert_mode_agent_consistency(ExecutionMode.DELEGATED, 2)  # Fails
```

**Soft suggestions** (hints for optimization):

```python
from agentic_fleet.dspy_modules.assertions import (
    suggest_valid_agents,
    suggest_task_type_routing,
)

# Suggest valid agents (won't fail, just logs)
suggest_valid_agents(["Writer"], ["Writer", "Researcher"])

# Suggest task-type specific routing
suggest_task_type_routing(
    task="Research AI trends",
    assigned_agents=["Researcher"],
    tool_requirements=["TavilySearchTool"],
)
```

**Task type detection:**

```python
from agentic_fleet.dspy_modules.assertions import detect_task_type

detect_task_type("Research quantum computing")  # "research"
detect_task_type("Write a Python function")     # "coding"
detect_task_type("Analyze the sales data")      # "analysis"
detect_task_type("Write a blog post")           # "writing"
detect_task_type("Hello, how are you?")         # "general"
```

**Assertions decorator:**

```python
from agentic_fleet.dspy_modules.assertions import with_routing_assertions

@with_routing_assertions(_max_backtracks=3)
def route_task(task: str) -> dict:
    # If routing fails assertions, DSPy will retry up to 3 times
    return {"assigned_to": ["Writer"], "mode": "delegated"}
```

### Routing Cache

Cache routing decisions to avoid redundant LLM calls:

```yaml
dspy:
  optimization:
    enable_routing_cache: true # Enable caching
    cache_ttl_seconds: 300 # 5 minute TTL
```

**Programmatic cache management:**

```python
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

reasoner = DSPyReasoner(enable_routing_cache=True, cache_ttl_seconds=300)

# First call: LLM invocation
result1 = reasoner.route_task("Research AI", team={"Researcher": "..."})

# Second call (same task/team): cached result
result2 = reasoner.route_task("Research AI", team={"Researcher": "..."})

# Clear cache when needed
reasoner.clear_routing_cache()
```

## Related Documentation

- [Configuration](../users/configuration.md) - Full config reference
- [Evaluation Guide](evaluation.md) - Evaluation framework
- [Self-Improvement](../users/self-improvement.md) - Self-improvement workflows

## Summary

**Quick Checklist:**

- ✅ Enable `dspy.optimization.enabled: true` in config
- ✅ Create quality training examples in `data/supervisor_examples.json`
- ✅ Start with BootstrapFewShot (`use_gepa: false`)
- ✅ Test with evaluation framework
- ✅ Upgrade to GEPA if needed (`use_gepa: true, gepa_auto: light`)
- ✅ Use execution history for continuous improvement (`gepa_use_history_examples: true`)
- ✅ Monitor cache and clear when needed
- ✅ Version control your training examples

**Common Commands:**

```bash
# Run with optimization
uv run agentic-fleet run -m "Task"

# GEPA optimize
uv run agentic-fleet gepa-optimize --auto light

# Clear cache
rm logs/compiled_supervisor.pkl*

# Evaluate performance
uv run agentic-fleet evaluate --dataset data/evaluation_tasks.jsonl
```
