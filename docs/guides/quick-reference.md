# Quick Reference Guide

## Running Workflows

```bash
# Basic execution (Auto-mode)
uv run agentic-fleet run -m "Your question"

# Force Handoff mode (fast research)
uv run agentic-fleet run -m "Quick query" --mode handoff

# Force Standard mode (robust analysis)
uv run agentic-fleet run -m "Deep analysis" --mode standard

# Force Discussion mode (group chat)
uv run agentic-fleet run -m "Brainstorm ideas for a new product" --mode discussion

# With detailed logging
uv run agentic-fleet run -m "Your question" --verbose

# Save output to file
uv run agentic-fleet run -m "Your question" --verbose 2>&1 | tee logs/output.log
```

## Analyzing History

```bash
# Quick overview
uv run python src/agentic_fleet/scripts/analyze_history.py

# All statistics
uv run python src/agentic_fleet/scripts/analyze_history.py --all

# Specific views
uv run python src/agentic_fleet/scripts/analyze_history.py --summary        # Overall stats
uv run python src/agentic_fleet/scripts/analyze_history.py --executions     # List all
uv run python src/agentic_fleet/scripts/analyze_history.py --last 5         # Last 5 only
uv run python src/agentic_fleet/scripts/analyze_history.py --routing        # Mode distribution
uv run python src/agentic_fleet/scripts/analyze_history.py --agents         # Agent usage
uv run python src/agentic_fleet/scripts/analyze_history.py --timing         # Time breakdown
```

## Viewing Logs

```bash
# Live workflow log
tail -f logs/workflow.log

# Last 50 lines
tail -50 logs/workflow.log

# Search for specific phase
grep "PHASE" logs/workflow.log

# View execution history
cat logs/execution_history.json | python -m json.tool | less
```

## Common Queries

```bash
# Count executions
cat logs/execution_history.json | python -c "import sys, json; print(len(json.load(sys.stdin)))"

# Extract quality scores
cat logs/execution_history.json | python -c "import sys, json; [print(f'{e[\"task\"][:50]}: {e[\"quality\"][\"score\"]}/10') for e in json.load(sys.stdin)]"

# Average execution time
cat logs/execution_history.json | python -c "import sys, json; data=json.load(sys.stdin); print(f'Avg: {sum(e[\"total_time_seconds\"] for e in data)/len(data):.2f}s')"

# List all execution modes
cat logs/execution_history.json | python -c "import sys, json; [print(f'{e[\"routing\"][\"mode\"]}: {e[\"task\"][:50]}') for e in json.load(sys.stdin)]"
```

## Configuration

```bash
# Edit workflow config
code config/workflow_config.yaml

# Key settings:
# - dspy.optimization.enabled: true/false
# - logging.save_history: true/false
# - logging.verbose: true/false
```

## Common Tasks

### Test a simple query

```bash
uv run agentic-fleet run -m "What is 2+2?" --verbose
```

### Test multi-agent workflow

```bash
uv run agentic-fleet run -m "Research quantum computing and write a summary" --verbose
```

### Check last 10 executions

```bash
uv run python src/agentic_fleet/scripts/analyze_history.py --executions --last 10
```

### View routing statistics

```bash
uv run python src/agentic_fleet/scripts/analyze_history.py --routing --agents
```

### Monitor execution in real-time

```bash
uv run agentic-fleet run -m "Your complex task" --verbose 2>&1 | tee logs/live.log
# In another terminal:
tail -f logs/workflow.log
```

## Troubleshooting

### No output showing

- Check if `--verbose` flag is used
- Verify `logging.verbose: true` in config/workflow_config.yaml
- Check logs/workflow.log for errors

### History not saving

- Ensure `logging.save_history: true` in config
- Check logs/ directory exists and is writable
- Verify logs/execution_history.json is valid JSON

### Slow execution

- Check network connectivity (OpenAI API, Tavily API)
- Review timing breakdown: `python src/agentic_fleet/scripts/analyze_history.py --timing`
- Consider adjusting max_rounds in config

### Quality scores always 10/10

- This is normal for simple tasks
- Try more complex multi-step queries
- Check quality assessment in logs for improvement suggestions

## Files and Directories

```
agentic-fleet/
├── src/agentic_fleet/cli/console.py                # Typer CLI entrypoint (exposed as `agentic-fleet`)
├── src/agentic_fleet/scripts/analyze_history.py    # History analysis tool
├── config/
│   └── workflow_config.yaml      # Main configuration
├── logs/
│   ├── workflow.log              # Detailed execution log
│   ├── execution_history.json    # Structured history
│   └── console_output.log        # Saved console output
├── data/
│   └── supervisor_examples.json  # DSPy training data
└── src/
    ├── agentic_fleet/workflows/  # Workflow definitions
    ├── agentic_fleet/dspy_modules/ # DSPy signatures and modules
    └── agentic_fleet/utils/      # Logging and compilation utilities
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
# Required
TAVILY_API_KEY=tvly-...

# Optional
DSPY_COMPILE=true               # Enable/disable DSPy compilation
LOG_LEVEL=INFO                  # Logging level
```

## Tips and Best Practices

1. **Use verbose mode** during development to see all DSPy decisions
2. **Analyze history regularly** to understand agent behavior patterns
3. **Monitor timing breakdown** to identify performance bottlenecks
4. **Review quality assessments** for improvement suggestions
5. **Keep execution history** for training and debugging
6. **Use tee** to save console output while viewing it live
7. **Check logs/** directory for detailed debugging information
