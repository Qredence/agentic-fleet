# Self-Improvement Guide

## Overview

The DSPy-Enhanced Agent Framework includes automatic self-improvement capabilities that learn from execution history. The system analyzes past executions, identifies high-quality routing decisions, and automatically adds them to the training dataset to improve future performance.

## How It Works

### The Self-Improvement Loop

```
┌─────────────────────────────────────────────────────────┐
│ 1. Execute Tasks                                        │
│    - Users run workflows                                │
│    - Quality scores recorded (0-10 scale)               │
│    - Full execution details saved to history            │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 2. Analyze History                                      │
│    - Self-improvement engine scans history              │
│    - Filters for quality score >= threshold (8.0)      │
│    - Identifies successful routing patterns             │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 3. Generate Training Examples                           │
│    - Converts high-quality executions to DSPy examples  │
│    - Includes: task, agents, mode, tool requirements    │
│    - Deduplicates against existing examples             │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 4. Update Training Data                                 │
│    - Adds new examples to supervisor_examples.json      │
│    - Clears compilation cache                           │
│    - Next execution recompiles with updated data        │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 5. Improved Routing                                     │
│    - DSPy learns from successful patterns               │
│    - Better agent selection                             │
│    - More accurate execution mode choices               │
│    - Improved tool usage decisions                      │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Automatic Self-Improvement

Use the CLI command to trigger self-improvement:

```bash
# Analyze and improve from execution history
uv run agentic-fleet self-improve

# Show statistics without making changes
uv run agentic-fleet self-improve --stats-only

# Customize quality threshold (only learn from excellent executions)
uv run agentic-fleet self-improve --min-quality 9.0

# Limit number of examples to add
uv run agentic-fleet self-improve --max-examples 10

# Combine options
uv run agentic-fleet self-improve --min-quality 8.5 --max-examples 15
```

### Using the Dedicated Script

```bash
# Run self-improvement analysis
uv run python src/agentic_fleet/scripts/self_improve.py

# View statistics only
uv run python src/agentic_fleet/scripts/self_improve.py --stats-only

# Customize parameters
uv run python src/agentic_fleet/scripts/self_improve.py --min-quality 9.0 --max-examples 20 --lookback 50
```

### Programmatic Usage

```python
from agentic_fleet.utils.self_improvement import SelfImprovementEngine

# Create engine
engine = SelfImprovementEngine(
    min_quality_score=8.0,      # Only learn from score >= 8.0
    max_examples_to_add=20,     # Add maximum 20 examples
    history_lookback=100,       # Analyze last 100 executions
)

# Get statistics
stats = engine.get_improvement_stats()
print(f"High-quality executions: {stats['high_quality_executions']}")
print(f"Average quality: {stats['average_quality_score']:.2f}/10")

# Perform self-improvement
added, status = engine.auto_improve(
    examples_file="src/agentic_fleet/data/supervisor_examples.json",
    force_recompile=True  # Clear cache to force relearning
)

print(f"Added {added} new training examples")
```

## Configuration

### Quality Threshold

The minimum quality score to consider an execution as "successful":

```python
engine = SelfImprovementEngine(
    min_quality_score=8.0,  # Default: 8.0 (good quality)
)
```

**Recommendations**:

- **8.0** - Balanced (learns from good executions)
- **9.0** - Strict (learns only from excellent executions)
- **7.0** - Lenient (learns from acceptable executions)

### Maximum Examples

Limit how many examples to add per improvement cycle:

```python
engine = SelfImprovementEngine(
    max_examples_to_add=20,  # Default: 20
)
```

**Recommendations**:

- **10-20** - Gradual learning
- **50-100** - Aggressive learning (use with high quality threshold)

### History Lookback

Number of recent executions to analyze:

```python
engine = SelfImprovementEngine(
    history_lookback=100,  # Default: 100
)
```

## What Gets Learned

The self-improvement system extracts:

1. **Task Patterns**: Types of tasks that were successfully completed
2. **Agent Selection**: Which agents were chosen for specific tasks
3. **Execution Mode**: Whether parallel, sequential, or delegated was optimal
4. **Tool Requirements**: Which tools were needed for success
5. **Task Complexity**: Understanding of simple vs. complex tasks

### Example Training Generation

**Execution in History**:

```json
{
  "task": "Find current Bitcoin price and analyze investment trends",
  "routing": {
    "assigned_to": ["Researcher", "Analyst"],
    "mode": "sequential",
    "tool_requirements": ["TavilySearchTool", "HostedCodeInterpreterTool"]
  },
  "quality": {
    "score": 9.0,
    "missing": "",
    "improvements": ""
  }
}
```

**Generated Training Example**:

```json
{
  "task": "Find current Bitcoin price and analyze investment trends",
  "team": "Researcher: Web research specialist\nAnalyst: Data analysis expert",
  "available_tools": "- TavilySearchTool (available to Researcher)...",
  "context": "Self-improvement: Quality score 9.0/10",
  "assigned_to": "Researcher,Analyst",
  "mode": "sequential",
  "tool_requirements": ["TavilySearchTool", "HostedCodeInterpreterTool"]
}
```

## Best Practices

### 1. Regular Self-Improvement Cycles

Run self-improvement periodically:

```bash
# After every 10-20 executions
uv run agentic-fleet self-improve

# Or set up a cron job
0 0 * * * cd /path/to/project && uv run agentic-fleet self-improve
```

### 2. Monitor Quality Trends

Check if self-improvement is working:

```bash
# View quality statistics
uv run python src/agentic_fleet/scripts/analyze_history.py --all

# Look for improving average quality scores over time
```

### 3. Gradual Learning

Start with strict thresholds, relax as needed:

```bash
# Week 1: Only learn from excellent executions
uv run agentic-fleet self-improve --min-quality 9.0

# Week 2: Include good executions
uv run agentic-fleet self-improve --min-quality 8.0

# Week 3: Learn from acceptable patterns
uv run agentic-fleet self-improve --min-quality 7.5
```

### 4. Validate After Improvement

After adding examples, test routing:

```bash
# Clear cache to force recompilation
uv run python -c "from agentic_fleet.utils.compiler import clear_cache; clear_cache()"

# Run test task
uv run agentic-fleet run -m "Test task similar to learned patterns" --verbose
```

## Statistics and Monitoring

### View Self-Improvement Potential

```bash
# See how many high-quality executions are available
uv run agentic-fleet self-improve --stats-only
```

Output includes:

- Total executions in history
- High-quality executions (score >= threshold)
- Average quality score
- Quality distribution (excellent/good/acceptable/needs improvement)

### Quality Score Distribution

The system tracks:

- **Excellent (9-10)**: Outstanding executions, learn immediately
- **Good (8-9)**: Solid executions, default learning threshold
- **Acceptable (7-8)**: Decent but room for improvement
- **Needs Improvement (<7)**: Low quality, requires manual intervention or retry

## Deduplication

The system prevents duplicate training examples:

**Fingerprint**: `task + assigned_to + mode`

This ensures:

- Same task with different routing = new example
- Same routing on different tasks = new example
- Exact duplicates = ignored

## Integration with DSPy

Self-improvement works seamlessly with DSPy optimization through a "Lazy Loading" architecture:

1. **Data Preparation (Fast)**: The `self-improve` command analyzes history and updates `src/agentic_fleet/data/supervisor_examples.json`. It does _not_ run the expensive DSPy compilation process itself.
2. **Cache Invalidation**: It clears the compilation cache (`.var/logs/compiled_supervisor.pkl`), signaling that the current model is outdated.
3. **Just-in-Time Optimization**: The _next_ time you run `agentic-fleet run`, the system detects the missing cache and automatically triggers the DSPy compiler.
4. **Result**: The new run uses a fresh model optimized with your latest high-quality examples.

This separation ensures that the `self-improve` command remains instant and lightweight, deferring the heavy lifting to the next execution cycle.

1. **New examples added** to `src/agentic_fleet/data/supervisor_examples.json`
2. **Cache cleared** to force recompilation
3. **Next execution** triggers DSPy BootstrapFewShot compilation
4. **Improved routing** from learned patterns

## Advanced Usage

### Custom Example File

```python
engine = SelfImprovementEngine()

# Use custom examples file
engine.auto_improve(
    examples_file="src/agentic_fleet/data/custom_examples.json",
    force_recompile=True
)
```

### Selective Learning

```python
# Only learn from specific execution patterns
from agentic_fleet.utils.history_manager import HistoryManager

manager = HistoryManager()
executions = manager.load_history()

# Filter for specific criteria
research_tasks = [
    ex for ex in executions
    if "research" in ex.get("task", "").lower()
    and ex.get("quality", {}).get("score", 0) >= 9.0
]

# Convert to examples manually
# (implement custom logic as needed)
```

## Troubleshooting

### No High-Quality Executions Found

**Issue**: System says "No high-quality executions to learn from"

**Solutions**:

1. Lower quality threshold: `--min-quality 7.0`
2. Run more tasks to build history
3. Review quality assessments in history:
   ```bash
   uv run python src/agentic_fleet/scripts/analyze_history.py --all
   ```

### Examples Not Improving Routing

**Issue**: Added examples but routing quality isn't improving

**Solutions**:

1. Verify cache was cleared:

   ```bash
   uv run python -c "from agentic_fleet.utils.compiler import clear_cache; clear_cache()"
   ```

2. Check examples were added:

   ```bash
   uv run python -c "import json; print(len(json.load(open('src/agentic_fleet/data/supervisor_examples.json'))))"
   ```

3. Run with compilation enabled:
   ```bash
   uv run agentic-fleet run -m "Task" --compile
   ```

### Duplicate Examples

**Issue**: Same patterns being added repeatedly

**Solution**: The system automatically deduplicates. If you see many similar examples:

1. Review fingerprinting logic in `src/agentic_fleet/utils/self_improvement.py`
2. Manually edit `src/agentic_fleet/data/supervisor_examples.json` to remove unwanted examples

## Performance Considerations

### History Size

Self-improvement scans recent history (default: last 100 executions):

```python
engine = SelfImprovementEngine(
    history_lookback=50,  # Faster analysis
)
```

### Compilation Time

More examples = longer compilation:

- 50 examples: ~2-3 seconds
- 100 examples: ~4-5 seconds
- 200 examples: ~8-10 seconds

**Recommendation**: Keep total examples under 150 for optimal startup time.

## Example Workflow

### Week 1: Initial Usage

```bash
# Run various tasks
uv run agentic-fleet run -m "Research AI trends"
uv run agentic-fleet run -m "Analyze sales data"
uv run agentic-fleet run -m "Write report"
```

### Week 2: First Self-Improvement

```bash
# Check what can be learned
uv run agentic-fleet self-improve --stats-only

# Output: 15 executions, 5 high-quality

# Add successful patterns
uv run agentic-fleet self-improve

# Output: Added 5 new training examples
```

### Week 3: Continued Learning

```bash
# More tasks with improved routing
uv run agentic-fleet run -m "Similar research task"
# Routing should be better/faster

# Periodic improvement
uv run agentic-fleet self-improve

# Output: Added 3 new training examples (+ 2 duplicates filtered)
```

### Month 2: Optimization

```bash
# Review overall improvement
uv run python src/agentic_fleet/scripts/analyze_history.py --all

# Look for:
# - Average quality score trending up
# - More consistent routing decisions
# - Better tool selection
```

## Monitoring Self-Improvement

Track effectiveness:

1. **Quality Scores**: Should increase over time
2. **Routing Consistency**: Similar tasks should route similarly
3. **Tool Usage**: Appropriate tools selected more often
4. **Execution Time**: Should stabilize or improve

## Future Enhancements

Potential improvements to the self-improvement system:

1. **Negative Learning**: Learn from low-quality executions what to avoid
2. **Weighted Examples**: Give higher weight to excellent executions
3. **Domain-Specific Learning**: Separate training sets for different domains
4. **Automated Cycles**: Trigger self-improvement after N executions
5. **A/B Testing**: Compare routing decisions before/after improvement

## Related Documentation

- [User Guide](user-guide.md) - General usage
- [Configuration](configuration.md) - Configuration options
- [API Reference](../developers/api-reference.md) - API documentation
- [Architecture](../developers/architecture.md) - System architecture
