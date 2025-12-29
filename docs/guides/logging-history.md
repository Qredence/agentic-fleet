# Comprehensive Logging and History Tracking

## Overview

AgenticFleet includes detailed logging and persistent history tracking that captures each workflow phase for
debugging, evaluation, and offline improvement.

## Features

### 1. Five-Phase Workflow Logging

The default pipeline follows:

`analysis → routing → execution → progress → quality`

**PHASE 1: Analysis**

- Task complexity assessment (simple/moderate/complex)
- Required capabilities identification
- Estimated steps for completion
- Analysis execution time

**PHASE 2: Routing**

- Execution mode determination (SEQUENTIAL/PARALLEL/DELEGATED)
- Agent assignments with explanations
- Routing decision time

**PHASE 3: Execution**

- Mode-specific execution details:
  - Sequential: Shows pipeline (Agent1 → Agent2 → Agent3)
  - Parallel: Shows concurrent agent workload distribution
  - Delegated: Shows single agent handling entire task
- Real-time agent progress with "Processing..." and "Completed" events
- Total execution time

**PHASE 4: Progress**

- Determines whether the task is complete or needs iteration
- Records progress signals and loop decisions

**PHASE 5: Quality**

- Quality score (0-10 scale)
- Missing elements analysis
- Suggested improvements
- Assessment execution time

### 2. Persistent JSONL History

All executions are saved to `.var/logs/execution_history.jsonl` by default (one JSON object per line).

```json
{
  "task": "User's original question",
  "start_time": "2025-11-03T05:45:29.487789",
  "dspy_analysis": {
    "complexity": "simple",
    "capabilities": ["capability1", "capability2"],
    "steps": 3,
    "analysis_time_seconds": 1.81
  },
  "routing": {
    "mode": "sequential",
    "assigned_to": ["Agent1", "Agent2"],
    "routing_time_seconds": 1.82
  },
  "quality": {
    "score": 10.0,
    "missing_elements": "None",
    "improvements": "Suggestions...",
    "quality_time_seconds": 3.17
  },
  "result": "Final output from agents...",
  "end_time": "2025-11-03T05:45:51.489465",
  "total_time_seconds": 22.0,
  "execution_summary": {
    "total_routings": 1,
    "routing_history": [...]
  }
}
```

### 3. Multiple Output Channels

**Console Output (Rich UI):**

- Beautiful colored panels showing each agent's work
- Real-time progress indicators
- DSPy decision explanations

**Log Files:**

- `.var/logs/workflow.log` - Detailed timestamped execution log
- `.var/logs/execution_history.jsonl` - Structured execution history (JSONL)
- `.var/logs/console_output.log` - Captured console output (when using `tee`, optional)

## Usage

### Basic Usage (Console Only)

```bash
uv run agentic-fleet run -m "Your question here"
```

### With Verbose Logging

```bash
uv run agentic-fleet run -m "Your question here" --verbose
```

### Capture Console Output to File

```bash
uv run agentic-fleet run -m "Your question here" --verbose 2>&1 | tee .var/logs/console_output.log
```

## Configuration

Edit `src/agentic_fleet/config/workflow_config.yaml` to customize logging:

```yaml
logging:
  save_history: true # Enable/disable JSON history
  history_file: .var/logs/execution_history.jsonl
  verbose: true # Show detailed phase information
```

## Analyzing Execution History

### View All Executions

```bash
tail -n 1 .var/logs/execution_history.jsonl | uv run python -m json.tool
```

### Count Total Executions

```bash
wc -l .var/logs/execution_history.jsonl
```

### Extract Quality Scores

```bash
tail -n 50 .var/logs/execution_history.jsonl | uv run python -c "import json,sys; [print(f\"{(r.get('task','')[:50])}: {r.get('quality',{}).get('score','?')}/10\") for r in (json.loads(line) for line in sys.stdin) if line.strip()]"
```

### Calculate Average Execution Time

```bash
uv run python -c "import json,sys; rows=[json.loads(l) for l in sys.stdin if l.strip()]; print(f\"Avg: {sum(r.get('total_time_seconds',0) for r in rows)/max(len(rows),1):.2f}s\")" < .var/logs/execution_history.jsonl
```

## Example Output

```
================================================================================
STARTING NEW WORKFLOW EXECUTION
Task: What is quantum computing?
Start Time: 2025-11-03T05:45:29.487789
================================================================================

[PHASE 1] DSPy Task Analysis
Invoking DSPy task_analyzer...
  Complexity: simple
  Required Capabilities: Information retrieval, summarization, basic understanding of quantum computing
  Estimated Steps: 3
  Analysis Time: 1.81s

[PHASE 2] DSPy Task Routing
Invoking DSPy task_router...
  Execution Mode: SEQUENTIAL
  Assigned Agents: Researcher, Writer, Reviewer
  Routing Time: 1.82s

[PHASE 3] Agent Execution
Executing in SEQUENTIAL mode through 3 agents
  Pipeline: Researcher → Writer → Reviewer
[Agent progress shown in real-time]
Agent execution completed in 15.19s

[PHASE 4] DSPy Quality Assessment
Invoking DSPy quality_assessor...
  Quality Score: 10.0/10
  Missing Elements: None
  Suggested Improvements: [suggestions]
  Assessment Time: 3.17s

Execution history saved to .var/logs/execution_history.jsonl

================================================================================
WORKFLOW EXECUTION COMPLETED
Total Execution Time: 22.00s
Result Length: 3972 characters
History saved to: .var/logs/execution_history.jsonl
================================================================================
```

## Key Insights from Logging

1. **DSPy Intelligence**: See how DSPy analyzes task complexity and makes routing decisions
2. **Execution Modes**: Understand when parallel, sequential, or delegated execution is chosen
3. **Agent Pipeline**: Visualize the flow of information through agents
4. **Quality Control**: Track DSPy's quality assessment and refinement suggestions
5. **Performance Metrics**: Measure time spent in each phase for optimization

## Troubleshooting

**History file not created:**

- Check that `.var/logs/` directory exists (or run `make init-var`)
- Verify `save_history: true` in `workflow_config.yaml`
- Ensure write permissions in `.var/logs/` directory

**Verbose logging not showing:**

- Use `--verbose` flag when running the CLI
- Check `workflow_config.yaml` logging settings
- Verify logger configuration in `src/agentic_fleet/utils/logger.py`

**JSON parse errors:**

- The default history file is JSONL (one JSON object per line)
- Use `tail -n 1 .var/logs/execution_history.jsonl | uv run python -m json.tool` to validate an entry
