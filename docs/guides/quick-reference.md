# Quick Reference Guide

## Makefile Commands

### Setup

```bash
make install           # Install Python dependencies with uv
make frontend-install  # Install frontend npm dependencies
make dev-setup         # Full setup (install + frontend + pre-commit)
```

### Development

```bash
make dev               # Run backend (8000) + frontend (5173) together
make backend           # Backend only on port 8000
make frontend-dev      # Frontend only on port 5173
make run               # CLI application

# Or use the CLI directly
agentic-fleet dev                     # Start both servers
agentic-fleet dev --backend-port 8080 # Custom backend port
agentic-fleet dev --no-frontend       # Backend only
agentic-fleet dev --no-backend        # Frontend only
```

### Testing

```bash
make test              # Run backend tests (fast, quiet output)
make test-frontend     # Run frontend unit tests
make test-all          # Run all tests (backend + frontend)
make test-config       # Validate workflow configuration
make test-e2e          # E2E tests (requires dev servers running)
```

### Code Quality

```bash
make check             # Quick check (lint + type-check)
make qa                # Full QA (lint + format + type + all tests)
make lint              # Backend linting (Ruff)
make format            # Backend formatting (Ruff)
make frontend-lint     # Frontend linting (ESLint)
make frontend-format   # Frontend formatting (Prettier)
make type-check        # Type checking (ty)
```

### Tools

```bash
make analyze-history   # Analyze workflow execution history
make evaluate-history  # Run DSPy-based evaluation on history
make self-improve      # Run self-improvement analysis
make clear-cache       # Clear compiled DSPy cache
make clean             # Remove cache and build artifacts
make init-var          # Initialize .var/ directory structure
```

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
uv run agentic-fleet run -m "Your question" --verbose 2>&1 | tee .var/logs/output.log
```

## Analyzing History

```bash
# Quick overview
uv run python -m agentic_fleet.scripts.analyze_history

# All statistics
uv run python -m agentic_fleet.scripts.analyze_history --all

# Specific views
uv run python -m agentic_fleet.scripts.analyze_history --summary        # Overall stats
uv run python -m agentic_fleet.scripts.analyze_history --executions     # List all
uv run python -m agentic_fleet.scripts.analyze_history --last 5         # Last 5 only
uv run python -m agentic_fleet.scripts.analyze_history --routing        # Mode distribution
uv run python -m agentic_fleet.scripts.analyze_history --agents         # Agent usage
uv run python -m agentic_fleet.scripts.analyze_history --timing         # Time breakdown
```

## Viewing Logs

```bash
# Live workflow log
tail -f .var/logs/workflow.log

# Last 50 lines
tail -50 .var/logs/workflow.log

# Search for specific phase
grep "PHASE" .var/logs/workflow.log

# View execution history
tail -n 1 .var/logs/execution_history.jsonl | uv run python -m json.tool | less
```

## Common Queries

```bash
# Count executions
wc -l .var/logs/execution_history.jsonl

# Extract quality scores
tail -n 50 .var/logs/execution_history.jsonl | uv run python -c "import json,sys; [print(f\"{(r.get('task','')[:50])}: {r.get('quality',{}).get('score','?')}/10\") for r in (json.loads(line) for line in sys.stdin) if line.strip()]"

# Average execution time
uv run python -c "import json,sys; rows=[json.loads(l) for l in sys.stdin if l.strip()]; print(f\"Avg: {sum(r.get('total_time_seconds',0) for r in rows)/max(len(rows),1):.2f}s\")" < .var/logs/execution_history.jsonl

# List all execution modes
tail -n 50 .var/logs/execution_history.jsonl | uv run python -c "import json,sys; [print(f\"{(r.get('routing',{}).get('mode','?'))}: {(r.get('task','')[:50])}\") for r in (json.loads(line) for line in sys.stdin) if line.strip()]"
```

## Configuration

```bash
# Edit workflow config
code src/agentic_fleet/src/agentic_fleet/config/workflow_config.yaml

# Key settings:
# - dspy.optimization.enabled: true/false
# - logging.save_history: true/false
# - logging.verbose: true/false
# - workflow.quality.enable_refinement: false  # Disable refinement loops
# - workflow.quality.max_refinement_rounds: 0  # No refinement loops
# - dspy.routing_model: gpt-5-mini            # Fast model for routing decisions
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
uv run python -m agentic_fleet.scripts.analyze_history --executions --last 10
```

### View routing statistics

```bash
uv run python -m agentic_fleet.scripts.analyze_history --routing --agents
```

### Monitor execution in real-time

```bash
uv run agentic-fleet run -m "Your complex task" --verbose 2>&1 | tee .var/logs/live.log
# In another terminal:
tail -f .var/logs/workflow.log
```

## Troubleshooting

### No output showing

- Check if `--verbose` flag is used
- Verify `logging.verbose: true` in src/agentic_fleet/config/workflow_config.yaml
- Check `.var/logs/workflow.log` for errors

### History not saving

- Ensure `logging.save_history: true` in config
- Check `.var/logs/` directory exists and is writable (or run `make init-var`)
- Verify `.var/logs/execution_history.jsonl` contains valid JSON per line

### Slow execution

- Check network connectivity (OpenAI API, Tavily API)
- Review timing breakdown: `uv run python -m agentic_fleet.scripts.analyze_history --timing`
- Clear DSPy cache after config changes: `make clear-cache` or `uv run python -m agentic_fleet.scripts.manage_cache --clear`
- The 5-phase pipeline (v0.6.6) should complete in ~2 minutes for complex queries
- Consider using `gpt-5-mini` for routing via `routing_model` config

### Quality scores always 10/10

- This is normal for simple tasks
- Try more complex multi-step queries
- Check quality assessment in logs for improvement suggestions

## Files and Directories

```
agentic-fleet/
├── src/agentic_fleet/
│   ├── cli/console.py            # Typer CLI entrypoint
│   ├── app/                      # FastAPI backend
│   │   ├── main.py               # App entry point
│   │   └── routers/              # API routes
│   ├── workflows/                # Workflow orchestration
│   ├── dspy_modules/             # DSPy signatures and modules
│   └── utils/                    # Utilities
├── src/frontend/                 # React frontend
├── src/agentic_fleet/scripts/
│   └── evaluate_history.py       # DSPy evaluation script
├── config/
│   └── workflow_config.yaml      # Main configuration
├── .var/                         # Runtime data (gitignored)
│   ├── logs/
│   │   ├── execution_history.jsonl
│   │   └── evaluation_results.jsonl
│   ├── cache/dspy/               # DSPy compilation cache
│   └── data/                     # Persistent data
└── src/agentic_fleet/data/
    └── supervisor_examples.json  # DSPy training data
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

## API Endpoints

### Health & Status

```bash
# Health check
curl http://localhost:8000/health
# Returns: {"status": "ok", "checks": {...}, "version": "<package version>"}

# Readiness check
curl http://localhost:8000/ready
```

### WebSocket Chat

```bash
# Connect to WebSocket
wscat -c ws://localhost:8000/api/ws/chat

# Send message
{"message": "Hello", "conversation_id": "abc-123"}

# Cancel streaming
{"type": "cancel"}
```

### REST API

```bash
# List conversations
curl http://localhost:8000/api/conversations

# Create conversation
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "New Chat"}'

# List agents
curl http://localhost:8000/api/v1/agents

# List sessions
curl http://localhost:8000/api/sessions
```

## Tips and Best Practices

1. **Use verbose mode** during development to see all DSPy decisions
2. **Analyze history regularly** to understand agent behavior patterns
3. **Monitor timing breakdown** to identify performance bottlenecks
4. **Review quality assessments** for improvement suggestions
5. **Keep execution history** for training and debugging
6. **Use tee** to save console output while viewing it live
7. **Check .var/logs/** directory for detailed debugging information
8. **Clear DSPy cache** after changing signatures, prompts, or training examples
9. **Pipeline phases**: analysis → routing → execution → progress → quality
10. **Smart fast-path**: Simple tasks (math, factual questions) bypass routing for <1s responses
