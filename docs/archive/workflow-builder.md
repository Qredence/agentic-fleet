# WorkflowBuilder Implementation Guide *(Legacy)*

> **Status:** Archived. AgenticFleet now uses the Magentic fleet orchestrator in
> `src/agenticfleet/fleet/magentic_fleet.py`. This document is retained for
> historical context on the deprecated `MultiAgentWorkflow` implementation.

## Overview

> **Note:** The legacy `MultiAgentWorkflow` implementation described in this
> document has been removed in favour of the Magentic-based fleet. The guide is
> retained for historical reference only.

## Architecture

### Graph-Based Execution

The workflow is structured as a directed graph with:
- **Nodes**: Agents (orchestrator, researcher, coder, analyst)
- **Edges**: Conditional transitions between agents
- **Entry Point**: Orchestrator agent
- **Exit**: Natural termination when no edges match

### Workflow Graph

```
User Input
    ↓
Orchestrator ←→ Researcher
    ↓           (returns to orchestrator)
    ↓
    ↓←→ Coder
    ↓   (returns to orchestrator)
    ↓
    ↓←→ Analyst
        (returns to orchestrator)
```

## Implementation Details

### File Location
`src/agenticfleet/workflows/workflow_builder.py`

### Key Components

#### 1. Conditional Edge Functions
```python
def _should_delegate_to_researcher(message: Any) -> bool:
    """Check if orchestrator wants to delegate to researcher.

    Args:
        message: The last output or message passed by the workflow framework.
    """
    response_text = _extract_response_text(message)
    return "DELEGATE: researcher" in response_text
```

Similar functions exist for coder and analyst delegation.

#### 2. Workflow Construction
```python
def create_workflow() -> Any:
    """Create multi-agent workflow using WorkflowBuilder pattern."""
    workflow = (
        WorkflowBuilder(max_iterations=max_rounds)
        .add_agent(orchestrator)
        .add_agent(researcher)
        .add_agent(coder)
        .add_agent(analyst)
        # Conditional edges from orchestrator to specialists
        .add_edge(orchestrator, researcher, condition=_should_delegate_to_researcher)
        .add_edge(orchestrator, coder, condition=_should_delegate_to_coder)
        .add_edge(orchestrator, analyst, condition=_should_delegate_to_analyst)
        # Return edges from specialists to orchestrator
        .add_edge(researcher, orchestrator)
        .add_edge(coder, orchestrator)
        .add_edge(analyst, orchestrator)
        .set_start_executor(orchestrator)
        .build()
    )
    return workflow
```

#### 3. Compatibility Wrapper
```python
class MultiAgentWorkflow:
    """Maintains backward compatibility with previous API."""
    
    def __init__(self) -> None:
        self.workflow = create_workflow()
    
    async def run(self, user_input: str) -> str:
        result = await self.workflow.run(user_input)
        return _extract_response_text(result.output)
```

## Benefits

### Native Framework Features
- ✅ **Automatic Cycle Detection**: Framework warns about potential cycles
- ✅ **Graph Validation**: Ensures workflow integrity before execution
- ✅ **State Management**: WorkflowContext handles state automatically
- ✅ **Iteration Limits**: Built-in max_iterations prevents infinite loops
- ✅ **Future-Ready**: Can easily add checkpointing, streaming, parallel execution

### Removed Manual Logic
- ❌ Manual round counting
- ❌ Manual stall detection
- ❌ Context dictionary management
- ❌ String parsing for final answer detection

## Configuration

Workflow settings are loaded from `config/workflow_config.yaml`:

```yaml
workflow:
  max_rounds: 10
  max_stalls: 3
  max_resets: 2
```

The `max_rounds` setting is used as `max_iterations` in WorkflowBuilder.

## Testing

All existing tests pass without modification:
```bash
$ uv run pytest -v
============================== 28 passed ==============================
```

Configuration tests verify:
- ✅ Workflow can be imported
- ✅ MultiAgentWorkflow class exists
- ✅ run() method is available

## Migration Notes

### Backward Compatibility
The `MultiAgentWorkflow` class maintains the same API:
```python
from agenticfleet.workflows import MultiAgentWorkflow, workflow

# Both work the same as before
workflow_instance = MultiAgentWorkflow()
result = await workflow_instance.run("Your query here")

# Or use the singleton
result = await workflow.run("Your query here")
```

### Delegation Protocol
The orchestrator agent still uses string-based delegation:
- `DELEGATE: researcher - <task>` → Routes to researcher
- `DELEGATE: coder - <task>` → Routes to coder
- `DELEGATE: analyst - <task>` → Routes to analyst
- `FINAL_ANSWER:` → Workflow terminates naturally

### Old Implementation
The previous custom implementation is preserved at:
`src/agenticfleet/workflows/multi_agent.py.old`

## Future Enhancements

The WorkflowBuilder pattern enables:

### 1. Checkpointing (OPT-02)
```python
workflow = (
    WorkflowBuilder(...)
    .with_checkpointing(storage)
    .build()
)
```

### 2. Concurrent Execution (OPT-07)
```python
workflow = (
    WorkflowBuilder(...)
    .add_fan_out_edges("orchestrator", ["researcher", "coder", "analyst"])
    .add_fan_in_edges(["researcher", "coder", "analyst"], "synthesizer")
    .build()
)
```

### 3. SharedState (OPT-08)
```python
class WorkflowState(SharedState):
    user_query: str
    research_results: list[str] = []
    code_outputs: list[str] = []

result = await workflow.run(message, shared_state=WorkflowState(...))
```

### 4. Streaming Events
```python
async for event in workflow.run_stream(message):
    if isinstance(event, WorkflowOutputEvent):
        print(f"Agent output: {event.output}")
```

## Performance

No performance regression observed. The framework handles execution efficiently with:
- Native Python async/await
- Optimized graph traversal
- Minimal overhead from validation

## Debugging

### Graph Visualization
The workflow graph can be visualized (future enhancement):
```python
from agent_framework import WorkflowViz
viz = WorkflowViz(workflow)
viz.save("workflow_graph.png")
```

### Execution Tracing
Framework provides built-in event tracking:
```python
result = await workflow.run(message, include_status_events=True)
for event in result.events:
    print(f"{event.timestamp}: {event.type}")
```

## Summary

The WorkflowBuilder implementation provides:
- Native framework patterns
- Better maintainability
- Enhanced capabilities
- Full backward compatibility
- Foundation for future features

All while passing existing tests and maintaining the same API surface.
