# Comprehensive Logging and History Tracking

## Overview

The DSPy-Enhanced Agent Framework now includes detailed logging and persistent history tracking that captures every phase of workflow execution.

## Features

### 1. Four-Phase Logging Structure

**PHASE 1: DSPy Task Analysis**

- Task complexity assessment (simple/moderate/complex)
- Required capabilities identification
- Estimated steps for completion
- Analysis execution time

**PHASE 2: DSPy Task Routing**

- Execution mode determination (SEQUENTIAL/PARALLEL/DELEGATED)
- Agent assignments with explanations
- Routing decision time

**PHASE 3: Agent Execution**

- Mode-specific execution details:
  - Sequential: Shows pipeline (Agent1 → Agent2 → Agent3)
  - Parallel: Shows concurrent agent workload distribution
  - Delegated: Shows single agent handling entire task
- Real-time agent progress with "Processing..." and "Completed" events
- Total execution time

**PHASE 4: DSPy Quality Assessment**

- Quality score (0-10 scale)
- Missing elements analysis
- Suggested improvements
- Assessment execution time

### 2. Persistent JSON History

All executions are saved to `logs/execution_history.json` with the following structure:

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

- `logs/workflow.log` - Detailed timestamped execution log
- `logs/console_output.log` - Captured console output (when using `tee`)
- `logs/execution_history.json` - Structured execution history

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
uv run agentic-fleet run -m "Your question here" --verbose 2>&1 | tee logs/console_output.log
```

## Configuration

Edit `config/workflow_config.yaml` to customize logging:

```yaml
logging:
  save_history: true # Enable/disable JSON history
  history_file: logs/execution_history.json
  verbose: true # Show detailed phase information
```

## Analyzing Execution History

### View All Executions

```bash
cat logs/execution_history.json | python -m json.tool
```

### Count Total Executions

```bash
cat logs/execution_history.json | python -c "import sys, json; print(len(json.load(sys.stdin)))"
```

### Extract Quality Scores

```bash
cat logs/execution_history.json | python -c "import sys, json; [print(f\"{e['task'][:50]}: {e['quality']['score']}/10\") for e in json.load(sys.stdin)]"
```

### Calculate Average Execution Time

```bash
cat logs/execution_history.json | python -c "import sys, json; data=json.load(sys.stdin); print(f\"Avg: {sum(e['total_time_seconds'] for e in data)/len(data):.2f}s\")"
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

Execution history saved to logs/execution_history.json

================================================================================
WORKFLOW EXECUTION COMPLETED
Total Execution Time: 22.00s
Result Length: 3972 characters
History saved to: logs/execution_history.json
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

- Check that `logs/` directory exists
- Verify `save_history: true` in `workflow_config.yaml`
- Ensure write permissions in `logs/` directory

**Verbose logging not showing:**

- Use `--verbose` flag when running the CLI
- Check `workflow_config.yaml` logging settings
- Verify logger configuration in `src/utils/logger.py`

**JSON parse errors:**

- The history file uses JSON array format
- Each execution is appended as a new object
- Use `python -m json.tool` to validate structure
