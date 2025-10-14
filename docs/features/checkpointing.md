# Workflow Checkpointing

## Overview

AgenticFleet now supports workflow checkpointing, enabling you to save and restore workflow state. This feature provides:

- **Resume Failed Workflows**: Continue from last checkpoint instead of restarting
- **Cost Savings**: Avoid redundant LLM API calls (can save 50-80% on retry costs)
- **Audit Trail**: Complete history of all workflow executions
- **Time-Travel Debugging**: Replay workflows to debug issues
- **User Experience**: Users don't lose progress on failures

## Configuration

Checkpointing is configured in `src/agenticfleet/config/workflow.yaml`:

```yaml
workflow:
  max_rounds: 10
  max_stalls: 3
  max_resets: 2
  timeout_seconds: 300
  checkpointing:
    enabled: true                      # Enable/disable checkpointing
    storage_type: file                 # Options: file, memory
    storage_path: ./checkpoints        # Path for file storage
    cleanup_after_days: 30             # Auto-cleanup (not yet implemented)
    auto_resume_on_failure: false      # Auto-resume (not yet implemented)
```

### Storage Types

- **file**: Persistent storage in JSON files (recommended for production)
- **memory**: In-memory storage (for testing, lost on restart)

## Usage

### Interactive REPL

When you start AgenticFleet, you'll see the checkpoint status:

```
✓ Checkpointing enabled (storage: ./checkpoints)
```

#### List Checkpoints

View all saved checkpoints:

```
🎯 Your task: checkpoints
```

or

```
🎯 Your task: list-checkpoints
```

Output:
```
================================================================================
Available Checkpoints (3)
================================================================================

Checkpoint ID: a1b2c3d4-5e6f-7890-abcd-ef1234567890
  Workflow ID: workflow_abc123
  Timestamp:   2025-10-13 14:30:45
  Round:       3
  Status:      in_progress

Checkpoint ID: e5f6g7h8-9i0j-1234-cdef-567890abcdef
  Workflow ID: workflow_def456
  Timestamp:   2025-10-13 14:25:12
  Round:       5
  Status:      completed
```

#### Resume from Checkpoint

Restore a workflow from a checkpoint and continue:

```
🎯 Your task: resume a1b2c3d4-5e6f-7890-abcd-ef1234567890
🎯 Your task (continuing from checkpoint): Analyze the results and provide a summary
```

The workflow will restore its state (round number, context, last response) and continue from where it left off.

### Programmatic Usage

```python
from agenticfleet.fleet import create_default_fleet

fleet = create_default_fleet()
result = await fleet.run("Analyze sales data")

# Checkpoint restoration is handled by the Magentic workflow's
# CheckpointStorage integration. Pass a checkpoint ID to resume:
result = await fleet.run(
    "Continue analysis",
    resume_from_checkpoint="a1b2c3d4-5e6f-7890-abcd-ef1234567890",
)
```

## Checkpoint Format

Checkpoints are stored as JSON files with the following structure:

```json
{
  "checkpoint_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
  "workflow_id": "workflow_abc123",
  "timestamp": "2025-10-13T14:30:45.123456+00:00",
  "current_round": 3,
  "stall_count": 0,
  "last_response": "DELEGATE: researcher - Search for Python ML libraries",
  "context": {
    "available_agents": {
      "researcher": "Performs web searches and data gathering",
      "coder": "Writes, executes, and debugs code",
      "analyst": "Analyzes data and generates insights"
    },
    "user_query": "Research Python machine learning libraries",
    "last_delegation_result": "Found: scikit-learn, TensorFlow, PyTorch..."
  },
  "metadata": {
    "status": "in_progress",
    "round": 3,
    "user_input": "Research Python machine learning libraries"
  }
}
```

## When Checkpoints are Created

Checkpoints are automatically created:

1. **After each workflow round** - Saves state after orchestrator decision
2. **On completion** - Final checkpoint with `status: completed`
3. **On error** - Checkpoint with `status: error` and error details
4. **On stall** - When workflow detects identical responses
5. **On max rounds** - When workflow reaches round limit

## Benefits in Action

### Scenario 1: Network Failure

```
Round 1: User asks to research Python ML libraries
Round 2: Orchestrator delegates to researcher
Round 3: Researcher starts web search
[Network error occurs]

Resume from checkpoint:
Round 3: Continue from where researcher left off
Round 4: Complete analysis without re-doing rounds 1-2
```

**Cost Savings**: Skip 2 rounds of LLM calls = ~60% cost reduction

### Scenario 2: Debugging

```
# Run workflow
result = await workflow.run("Complex analysis task")

# Review checkpoints to understand what happened
checkpoints = await workflow.list_checkpoints("workflow_abc123")
for cp in checkpoints:
    print(f"Round {cp['current_round']}: {cp['metadata'].get('status')}")
```

### Scenario 3: Long-Running Tasks

```
# Start a complex task
await workflow.run("Analyze 10 years of sales data")

# If it fails after 8 rounds, resume without starting over
await workflow.run(
    "Continue analysis",
    resume_from_checkpoint="last-checkpoint-id"
)
```

## Testing

Run the checkpoint-related tests:

```bash
python -m pytest tests/test_configuration.py -v
```

Test coverage includes:
- Checkpoint storage creation (file, memory, disabled)
- Default Magentic fleet wiring with checkpoint storage

## Architecture

The checkpointing system integrates with Microsoft Agent Framework's checkpoint storage:

```
┌─────────────────────────────────────┐
│   MagenticFleet                     │
│   (via FleetBuilder)                │
│                                     │
│  - run(..., resume_from_checkpoint) │
│  - with_checkpointing(storage)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   CheckpointStorage                 │
│   (FileCheckpointStorage)           │
│                                     │
│  - storage_path: ./checkpoints      │
│  - Saves JSON files                 │
└─────────────────────────────────────┘
```

## Future Enhancements

Phase 2 and 3 features planned:

- [ ] Automatic cleanup of old checkpoints
- [ ] Checkpoint export/import
- [ ] Checkpoint visualization
- [ ] Redis-based distributed storage
- [ ] Azure Cosmos DB storage
- [ ] Automatic retry with checkpointing
- [ ] Checkpoint compression
- [ ] Checkpoint metadata search

## Troubleshooting

### Checkpoints not being created

Check that checkpointing is enabled in `workflow.yaml`:

```yaml
checkpointing:
  enabled: true
```

### Cannot find checkpoint directory

The directory is created automatically, but ensure the parent directory is writable:

```bash
mkdir -p ./checkpoints
chmod 755 ./checkpoints
```

### Checkpoint restore fails

Ensure the checkpoint file exists and is valid JSON:

```bash
ls ./checkpoints/
cat ./checkpoints/<checkpoint-id>.json | python -m json.tool
```

## Related Documentation

- [OPT-02 Issue](../../analysis/issues/opt-02-checkpointing.md) - Original proposal
- [State Management Guide](../../analysis/TODOS/STATE_MANAGEMENT.md) - Framework patterns
- [Workflow Implementation](../../../src/agenticfleet/fleet/magentic_fleet.py) - Code
- [Test Suite](../../../tests/test_configuration.py) - Test coverage
