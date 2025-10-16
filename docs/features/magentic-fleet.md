# Magentic Fleet Implementation

## Overview

AgenticFleet now includes a complete Magentic One workflow implementation using the Microsoft Agent Framework. This provides an advanced orchestration pattern with intelligent planning, dynamic delegation, and human-in-the-loop capabilities.

## Architecture

### Core Components

1. **MagenticFleet** (`src/agenticfleet/fleet/magentic_fleet.py`)
   - Main orchestrator class wrapping the Magentic workflow
   - Uses `StandardMagenticManager` for intelligent planning
   - Integrates with checkpoint storage and approval handlers
   - Provides async `run()` method for task execution

2. **FleetBuilder** (`src/agenticfleet/fleet/fleet_builder.py`)
   - Fluent API wrapper around Microsoft's `MagenticBuilder`
   - Configures manager, agents, checkpointing, and callbacks
   - Handles OpenAI client creation and configuration
   - Supports custom agent injection for testing

3. **Event Callbacks** (`src/agenticfleet/fleet/callbacks.py`)
   - `streaming_agent_response_callback` - Real-time agent output
   - `plan_creation_callback` - Manager plan logging
   - `progress_ledger_callback` - Progress tracking
   - `tool_call_callback` - Tool execution monitoring
   - `final_answer_callback` - Result logging

### Workflow Cycle

The Magentic workflow follows this coordination pattern:

```
1. PLAN: Manager analyzes task and creates structured plan
   - Gathers known facts from task description
   - Identifies information gaps
   - Creates action plan with clear steps

2. EVALUATE: Manager creates progress ledger (JSON)
   - Checks if request is satisfied
   - Detects infinite loops or stalls
   - Assesses if progress is being made
   - Selects next agent to speak
   - Provides specific instruction/question

3. ACT: Orchestrator delegates to selected agent
   - Routes instruction to appropriate specialist
   - Agent executes using its tools
   - Agent returns response with findings

4. OBSERVE: Response added to chat history
   - Manager sees full conversation context
   - Evaluates whether task is complete
   - Decides whether to continue or replan

5. REPEAT: Until completion or limits reached
   - Max rounds: 30 (configurable)
   - Max stalls: 3 (replans if stuck)
   - Max resets: 2 (complete restart)
```

## Configuration

### Workflow Settings (`src/agenticfleet/config/workflow.yaml`)

```yaml
workflow:
  max_rounds: 10
  max_stalls: 3
  max_resets: 2
  timeout_seconds: 300
  checkpointing:
    enabled: true
    storage_type: file
    storage_path: ./checkpoints
    cleanup_after_days: 30
    auto_resume_on_failure: false
  human_in_the_loop:
    enabled: true
    approval_timeout_seconds: 300
    auto_reject_on_timeout: false
    require_approval_for:
      - code_execution
      - file_operations
      - external_api_calls
      - sensitive_data_access
    trusted_operations:
      - web_search
      - data_analysis

fleet:
  manager:
    model: "gpt-5"
    reasoning:
      effort: high
    instructions: |
      You are coordinating a fleet of specialized AI agents to solve complex tasks.
  orchestrator:
    max_round_count: 15
    max_stall_count: 3
    max_reset_count: 2
  plan_review:
    enabled: true
    require_human_approval: false
  callbacks:
    streaming_enabled: true
    log_progress_ledger: true
    log_tool_calls: true
```

### Agent Participants

The default fleet includes four specialist roles:

1. **Orchestrator**
   - Description: Coordinates delegation and synthesises final answers.
   - Model: `gpt-5`
   - Tools: None (planning-only role).

2. **Researcher**
   - Description: Performs web search and source synthesis.
   - Model: `gpt-5`
   - Tools: `web_search_tool`

3. **Coder**
   - Description: Drafts code and explains manual execution steps.
   - Model: `gpt-5`
   - Tools: None *(code execution is currently disabled)*.

4. **Analyst**
   - Description: Analyses structured data and recommends visualisations.
   - Model: `gpt-5`
   - Tools: `data_analysis_tool`, `visualization_suggestion_tool`

## Usage

### CLI Mode Selection

```bash
# Use Magentic Fleet workflow (default)
uv run fleet --workflow=magentic

# Legacy flag (deprecated, maps to Magentic)
uv run fleet --workflow=legacy
```

### Programmatic Usage

```python
from agenticfleet.fleet.magentic_fleet import create_default_fleet
import asyncio

async def main():
    # Create fleet with default configuration
    fleet = create_default_fleet()

    # Execute task
    result = await fleet.run(
        user_input="Analyze energy efficiency of ML models",
        resume_from_checkpoint=None  # Optional checkpoint ID
    )

    print(f"Result: {result}")

asyncio.run(main())
```

### Custom Fleet Configuration

```python
import asyncio

from agenticfleet.agents.coder import create_coder_agent
from agenticfleet.agents.researcher import create_researcher_agent
from agenticfleet.core.checkpoints import AgenticFleetFileCheckpointStorage
from agenticfleet.fleet.fleet_builder import FleetBuilder

researcher = create_researcher_agent()
coder = create_coder_agent()
storage = AgenticFleetFileCheckpointStorage("./my_checkpoints")

workflow = (
    FleetBuilder()
    .with_agents({"researcher": researcher, "coder": coder})
    .with_manager(model="gpt-5", max_round_count=12)
    .with_checkpointing(storage=storage)
    .with_plan_review(enabled=True)
    .with_observability()
    .build()
)

async def run_custom_workflow() -> str | None:
    return (
        await workflow.run(
            "Analyze energy efficiency of ML models",
            resume_from_checkpoint=None,
        )
    )

result = asyncio.run(run_custom_workflow())
print(result)
```

## Features

### 1. Intelligent Planning

The `StandardMagenticManager` creates structured plans:

```
FACTS:
- Known information from task description
- Previously gathered data from agents
- Domain knowledge and constraints

PLAN:
1. Research phase: Gather background information
2. Analysis phase: Process and analyze findings
3. Synthesis phase: Generate final recommendations
```

### 2. Dynamic Delegation

The manager evaluates progress and selects the best agent:

```json
{
  "is_request_satisfied": false,
  "is_in_loop": false,
  "is_progress_being_made": true,
  "next_speaker": "researcher",
  "instruction_or_question": "Search for energy consumption data on ResNet-50"
}
```

### 3. Human-in-the-Loop (HITL)

Enable plan review for critical tasks:

```python
from agenticfleet.fleet.magentic_fleet import create_default_fleet
from agenticfleet.core.hitl_handler import CLIApprovalHandler

fleet = create_default_fleet()
fleet.approval_handler = CLIApprovalHandler()

# Plan will be shown to user for approval before execution
result = await fleet.run("Analyze sensitive data")
```

### 4. Checkpointing

Workflow state is automatically persisted:

```python
# First run - gets interrupted
result = await fleet.run("Complex multi-step task")

# Resume from checkpoint
checkpoints = await storage.list_checkpoints()
latest = checkpoints[-1]
result = await fleet.run(
    "Continue task",
    resume_from_checkpoint=latest.checkpoint_id
)
```

### 5. Observability

Real-time monitoring through callbacks:

```python
# Callbacks are automatically configured
# Logs show:
# - Manager plans and progress ledgers
# - Agent selections and instructions
# - Tool calls and results
# - Final answers

# Example log output:
[Fleet] Manager created plan for task: Analyze ML models
[Fleet] Progress: Selected researcher for information gathering
[Fleet] Agent 'researcher' response: Found energy consumption data...
[Fleet] Progress: Selected coder for computation
[Fleet] Agent 'coder' executed code: Calculated efficiency metrics...
[Fleet] Final result: ResNet-50 uses 38 kWh for training...
```

## Testing

Comprehensive test coverage in `tests/test_magentic_fleet.py`:

```bash
# Run Magentic Fleet tests
uv run pytest tests/test_magentic_fleet.py -v

# Test categories:
# - Initialization (default/custom agents, storage, HITL)
# - Execution (basic, checkpoints, error handling)
# - Factory method (create_default_fleet)
# - Builder pattern (fluent API)
# - Callbacks (streaming, progress, plans)

# All 14 tests passing ✓
```

## Comparison: Legacy vs Magentic

| Feature | Legacy MultiAgent | Magentic Fleet |
|---------|------------------|----------------|
| **Planning** | Simple orchestrator prompt | Structured facts + plan |
| **Delegation** | Round-robin/manual | Intelligent selection |
| **Progress Tracking** | Round counter | Progress ledger JSON |
| **Stall Detection** | Response comparison | Built-in detection |
| **Replanning** | Manual | Automatic on stalls |
| **HITL** | Code execution only | Plan review + execution |
| **Observability** | Basic logging | Event callbacks |
| **State Management** | Checkpointing | Checkpointing + ledgers |

## Advantages of Magentic Fleet

1. **Smarter Orchestration**: Manager intelligently selects agents based on current needs
2. **Better Planning**: Structured approach with facts and action plans
3. **Stall Recovery**: Automatically detects when stuck and replans
4. **Plan Review**: Humans can approve/modify plans before execution
5. **Rich Context**: Full chat history available to manager for decisions
6. **Production Ready**: Built on Microsoft's battle-tested Agent Framework
7. **Extensible**: Easy to add new agents or customize manager behavior

## Migration Guide

To switch from legacy to Magentic workflow:

1. **Update CLI usage**:

   ```bash
   # Old
   uv run python main.py

   # New
   uv run fleet --workflow=magentic
   ```

2. **Update programmatic code**:

   ```python
   # Old
   from agenticfleet.workflows import workflow
   result = await workflow.run(user_input)

   # New
   from agenticfleet import create_default_fleet
   fleet = create_default_fleet()
   result = await fleet.run(user_input)
   ```

3. **Adjust expectations**:
   - Magentic may take more rounds due to intelligent planning
   - Responses include manager's synthesis, not just agent outputs
   - Progress ledgers appear in logs for visibility
   - Plan review may interrupt flow if enabled

## Future Enhancements

1. **Tool Response Narratives**: Enhance tool returns with narrative descriptions for better manager visibility
2. **Custom Managers**: Support for domain-specific manager implementations
3. **Agent Pools**: Dynamic agent registration/removal during execution
4. **Streaming UI**: Real-time progress visualization in web interface
5. **Multi-Modal**: Support for image/audio agents in coordination
6. **Distributed**: Scale agents across multiple processes/machines

## References

- [Microsoft Agent Framework Documentation](https://github.com/microsoft/agent-framework)
- [Magentic One Paper](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/)
- [AgenticFleet Architecture](../overview/implementation-summary.md)
- [Human-in-the-Loop Guide](../guides/human-in-the-loop.md)
- [Checkpointing Documentation](./checkpointing.md)
