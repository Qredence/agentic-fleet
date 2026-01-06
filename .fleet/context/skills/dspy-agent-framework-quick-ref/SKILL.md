---
name: dspy-agent-framework-quick-ref
description: Quick reference card for DSPy + Agent Framework integration patterns: typed signatures, assertions, routing cache, and agent handoffs.
---

# DSPy + Agent Framework Quick Reference

## Typed Signatures

```python
class TaskRouting(dspy.Signature):
    task: str = dspy.InputField(desc="Task to route")
    team: str = dspy.InputField(desc="Available agents")
    decision: RoutingDecisionOutput = dspy.OutputField()

class RoutingDecisionOutput(BaseModel):
    assigned_to: list[str] = Field(min_length=1)
    execution_mode: Literal["delegated", "sequential", "parallel"]
    subtasks: list[str] = Field(default_factory=list)
    tool_plan: list[str] = Field(default_factory=list)
    reasoning: str
```

## DSPy Assertions

```python
dspy.Assert(condition, "error message")  # Hard constraint
dspy.Suggest(condition, "guidance")       # Soft constraint

def validate_agent_exists(agents, available):
    Assert(len(agents) > 0, "Must assign at least one agent")
    for a in agents:
        Assert(a.lower() in [x.lower() for x in available],
               f"Agent {a} not in pool")
```

## Routing Cache

```python
class RoutingCache:
    def __init__(self, ttl_seconds=300, max_size=1024):
        self.ttl = ttl_seconds
        self.max_size = max_size

    def get(self, key): ...  # Returns None if expired/missing
    def set(self, key, value): ...  # Auto-evicts oldest
    def clear(self): ...
```

## DSPy-Enhanced Agent

```python
class DSPyEnhancedAgent(ChatAgent):
    def __init__(self, reasoning_strategy="chain_of_thought"):
        self.reasoning_strategy = reasoning_strategy
        if reasoning_strategy == "react":
            self.react_module = dspy.ReAct("q -> a", tools=self.tools)
        elif reasoning_strategy == "chain_of_thought":
            self.cot_module = dspy.ChainOfThought("q -> a")
```

## Workflow with Checkpoints

```python
from agent_framework._workflows import (
    WorkflowStartedEvent, WorkflowStatusEvent,
    WorkflowOutputEvent, ExecutorCompletedEvent,
    RequestInfoEvent, FileCheckpointStorage
)

class SupervisorWorkflow:
    def __init__(self, checkpoint_dir=".var/checkpoints"):
        self.checkpoint_storage = FileCheckpointStorage(checkpoint_dir)

    async def resume(self, checkpoint_id: str):
        state = self.checkpoint_storage.load(checkpoint_id)
        self.context.restore_from_state(state)
```

## Agent Handoffs

```python
class HandoffManager:
    def prepare_handoff(self, from_agent, to_agent, context):
        return {
            "task": context["original_task"],
            "findings": context.get("findings", []),
            "decisions": context.get("decisions", []),
            "from_agent_summary": self._summarize(from_agent)
        }

    def execute_sequential_with_handoffs(self, agents, tasks):
        context = {"original_task": tasks[0], "findings": [], "decisions": []}
        results = []
        for i, (agent, task) in enumerate(zip(agents, tasks)):
            handoff = self.prepare_handoff(
                agents[i-1] if i > 0 else None, agent, context
            )
            result = self._run_with_context(agent, task, handoff)
            context["findings"].extend(result.get("findings", []))
            results.append(result)
        return results
```

## GEPA Optimization

```bash
agentic-fleet optimize  # Outputs: .var/cache/dspy/compiled_reasoner.json
```

Config:

```yaml
dspy:
  use_typed_signatures: true
  enable_routing_cache: true
  routing_cache_ttl_seconds: 300
  optimization:
    use_gepa: true
    gepa_auto: light
```

## Key Imports

```python
# DSPy
import dspy
from dspy import TypedPredictor, ChainOfThought, ReAct, ProgramOfThought

# Agent Framework
from agent_framework._agents import ChatAgent
from agent_framework._workflows import Workflow, AgentThread
from agent_framework._types import AgentRunResponse, ChatMessage

# Pydantic
from pydantic import BaseModel, Field
from typing import Literal
```
