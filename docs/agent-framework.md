# Microsoft Agent Framework Conventions Guide

This document covers Microsoft Agent Framework patterns and conventions used in Agentic Fleet v2.0, based on official documentation from Context7.

## Table of Contents

1. [BaseAgent](#baseagent)
2. [AgentRunResponse](#agentrunresponse)
3. [WorkflowBuilder](#workflowbuilder)
4. [Executor](#executor)
5. [AgentExecutor](#agenteecutor)
6. [Conditional Routing](#conditional-routing)
7. [Best Practices](#best-practices)

---

## BaseAgent

BaseAgent is the foundation for creating agents in the Microsoft Agent Framework.

### Basic Agent Implementation

```python
from agent_framework import BaseAgent, ChatMessage, AgentRunResponse
from typing import Any

class MyAgent(BaseAgent):
    """Custom agent implementation."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)

    async def run(
        self,
        messages: list[ChatMessage] | str,
        **kwargs,
    ) -> AgentRunResponse:
        """Execute the agent with the given messages."""
        # Process messages
        if isinstance(messages, str):
            user_input = messages
        else:
            user_input = messages[-1].content if messages else ""

        # Perform agent logic
        response_text = await self._process(user_input)

        # Return response
        return AgentRunResponse(
            messages=[ChatMessage(role="assistant", content=response_text)],
            Text=response_text,
        )

    async def _process(self, input_text: str) -> str:
        """Agent-specific processing logic."""
        return f"Processed: {input_text}"
```

### Agentic Fleet's BaseFleetAgent

```python
from agent_framework import BaseAgent, ChatMessage, AgentRunResponse
from typing import Any
import dspy

class BaseFleetAgent(BaseAgent):
    """Base agent that binds DSPy brains to Agent Framework."""

    def __init__(
        self,
        name: str,
        role: str,
        signature: type[dspy.Signature],
        brain_state_path: str | None = None,
    ):
        super().__init__(name=name)
        self.role = role
        self.signature = signature
        # FleetBrain wraps DSPy ChainOfThought
        self.brain = FleetBrain(signature, brain_state_path)

    async def run(
        self,
        messages: list[ChatMessage] | str,
        team_id: str | None = None,
        metadata: dict | None = None,
        **kwargs,
    ) -> AgentRunResponse:
        """Execute agent with team-scoped context."""
        # Resolve team from param, metadata, or context
        resolved_team_id = team_id or (metadata or {}).get("team_id") or "default"

        async with ContextModulator.scope(resolved_team_id):
            # Build kwargs for DSPy brain
            brain_kwargs = self._build_brain_kwargs(messages, kwargs)
            prediction = self.brain(**brain_kwargs)

            # Extract payload from prediction
            payload = self._extract_payload(prediction)

            return AgentRunResponse(
                messages=[ChatMessage(role="assistant", content=payload["response"])],
                AdditionalProperties=payload.get("metadata", {}),
            )

    def _build_brain_kwargs(self, messages, kwargs) -> dict:
        """Convert messages to signature input fields."""
        if isinstance(messages, str):
            task = messages
        else:
            task = messages[-1].content if messages else ""
        return {"task": task, **kwargs}

    def _extract_payload(self, prediction) -> dict:
        """Extract response and metadata from DSPy prediction."""
        return {"response": str(prediction)}
```

---

## AgentRunResponse

AgentRunResponse is the standard response type for agent execution.

### Response Structure

```python
from agent_framework import AgentRunResponse, ChatMessage, AdditionalPropertiesDictionary

response = AgentRunResponse(
    # Aggregated text content
    Text="The final response text",

    # List of chat messages
    Messages=[
        ChatMessage(role="assistant", content="Response text"),
    ],

    # Response identifier
    ResponseId="resp_123",

    # Metadata
    AuthorName="AgentName",
    CreatedAt=datetime.now(),

    # Raw LLM response
    RawRepresentation={...},

    # Usage statistics
    Usage=UsageDetails(...),

    # Custom properties (routing metadata, etc.)
    AdditionalProperties=AdditionalPropertiesDictionary({
        "route_pattern": "complex",
        "target_team": "research",
    }),
)
```

### Extracting Information

```python
# Access response content
print(response.Text)  # "The final response text"

# Access messages
for msg in response.Messages:
    print(f"{msg.role}: {msg.content}")

# Access metadata
if response.AdditionalProperties:
    pattern = response.AdditionalProperties.get("route_pattern")
    team = response.AdditionalProperties.get("target_team")
```

### Streaming Responses

```python
from agent_framework import AIAgent

async def streaming_example(agent: AIAgent):
    """Handle streaming responses."""
    async for update in agent.run_streaming("Hello"):
        # update is AgentRunResponseUpdate
        print(update.Text)  # Incremental text
        if update.Contents:
            for content in update.Contents:
                print(content)
```

---

## WorkflowBuilder

WorkflowBuilder creates execution graphs for orchestrating multiple agents.

### Basic Workflow

```python
from agent_framework import WorkflowBuilder, Executor

# Define custom executor
class UpperCase(Executor):
    def __init__(self, id: str):
        super().__init__(id=id)

    async def handle(self, text: str, ctx) -> None:
        result = text.upper()
        await ctx.send_message(result)

async def main():
    upper = UpperCase(id="upper_case")

    # Build workflow: upper -> reverse
    workflow = (WorkflowBuilder()
        .add_edge(upper, reverse_executor)
        .set_start_executor(upper)
        .build())

    # Execute
    events = await workflow.run("hello")
    print(events.get_outputs())  # ['OLLEH']
```

### Agentic Fleet's Workflow Builder

```python
from agent_framework import WorkflowBuilder, AgentExecutor
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature

def build_modules_workflow(planner_state_path: str | None = None):
    """Build the Router → Planner → Worker → Judge → Terminal workflow."""

    # Create agents
    router_agent = RouterAgent()
    planner_agent = BaseFleetAgent(
        "Planner", "architect", PlannerSignature,
        brain_state_path=planner_state_path,
    )
    worker_agent = BaseFleetAgent("Worker", "executor", WorkerSignature)
    judge_agent = BaseFleetAgent("Judge", "critic", JudgeSignature)

    # Wrap in executors
    router_executor = AgentExecutor(router_agent, id="Router")
    planner_executor = AgentExecutor(planner_agent, id="Planner")
    worker_executor = AgentExecutor(worker_agent, id="Worker", output_response=True)
    judge_executor = AgentExecutor(judge_agent, id="Judge", output_response=True)
    terminal = TerminalExecutor(id="Terminal")

    # Build workflow
    builder = WorkflowBuilder(name="modules-workflow")
    builder.set_start_executor(router_executor)

    # Router → Planner (complex) or Worker (simple/direct)
    builder.add_switch_case_edge_group(
        "Router",
        [
            (lambda p: _is_complex(p), "Planner"),
            (lambda p: _is_simple(p) or _is_direct(p), "Worker"),
        ],
    )

    # Planner → Worker
    builder.add_edge(planner_executor, worker_executor)

    # Worker → Judge
    builder.add_edge(worker_executor, judge_executor)

    # Judge → Terminal (approved) or Worker (retry)
    builder.add_switch_case_edge_group(
        "Judge",
        [
            (lambda approved: approved, "Terminal"),
            (lambda approved: not approved, "Worker"),
        ],
    )

    return builder.build()

def _is_complex(pattern: str) -> bool:
    return pattern in {"complex", "complex_council"}

def _is_simple(pattern: str) -> bool:
    return pattern in {"simple", "simple_tool"}

def _is_direct(pattern: str) -> bool:
    return pattern in {"direct", "direct_answer"}
```

---

## Executor

Executor handles deterministic, non-AI processing in workflows.

### Class-Based Executor

```python
from agent_framework import Executor, WorkflowContext
from typing import Never

class DataProcessor(Executor):
    """Process data in a workflow."""

    def __init__(self, id: str, transform: str = "upper"):
        super().__init__(id=id)
        self.transform = transform

    async def handle(self, data: str, ctx: WorkflowContext[str]) -> None:
        """Process data and send to next node."""
        if self.transform == "upper":
            result = data.upper()
        elif self.transform == "lower":
            result = data.lower()
        else:
            result = data

        await ctx.send_message(result)
```

### Function-Based Executor

```python
from agent_framework import executor, WorkflowContext
from typing import Never

@executor(id="reverse_text")
async def reverse_text(text: str, ctx: WorkflowContext[Never, str]) -> None:
    """Reverse the input string."""
    result = text[::-1]
    await ctx.yield_output(result)
```

### Typed Executors

```python
from agent_framework import Executor

# Typed input/output
class StringProcessor(Executor[str, str]):
    """Processor that transforms strings."""

    def __init__(self, id: str):
        super().__init__(id=id)

    async def handle_async(self, message: str, context) -> str:
        """Process string and return result."""
        return message.upper()

# Build with typed executor
processor = StringProcessor(id="processor")
workflow = (WorkflowBuilder()
    .add_edge(processor, next_executor)
    .set_start_executor(processor)
    .build())
```

---

## AgentExecutor

AgentExecutor wraps agents for use in workflows.

### Basic AgentExecutor

```python
from agent_framework import AgentExecutor

# Create agent
router_agent = RouterAgent()

# Wrap in executor
router_executor = AgentExecutor(
    router_agent,
    id="Router",
    output_response=True,  # Include agent response in output
)

# Add to workflow
workflow = (WorkflowBuilder()
    .add_edge(router_executor, planner_executor)
    .set_start_executor(router_executor)
    .build())
```

### AgentExecutor Options

```python
router_executor = AgentExecutor(
    router_agent,
    id="Router",
    output_response=True,      # Include response in workflow output
    input_to_output=True,      # Forward input to output
    maxIterations=5,           # Max execution attempts
)
```

---

## Conditional Routing

Workflows can route based on agent outputs.

### Switch-Case Edges

```python
from agent_framework import WorkflowBuilder, AgentExecutor, Case, Default

# Define condition functions
def is_complex(pattern: str) -> bool:
    return pattern in {"complex", "complex_council"}

def is_simple(pattern: str) -> bool:
    return pattern in {"simple", "simple_tool"}

# Build conditional routing
builder = WorkflowBuilder()
builder.set_start_executor(router_executor)

# Router output determines next step
builder.add_switch_case_edge_group(
    "Router",  # Source executor ID
    [
        (is_complex, "Planner"),     # If complex → Planner
        (is_simple, "Worker"),       # If simple → Worker
        (Default, "Terminal"),       # Otherwise → Terminal
    ],
)
```

### Complex Conditions

```python
from agent_framework import Case, Default

# Multiple conditions with priority
builder.add_switch_case_edge_group(
    "Judge",
    [
        # Judge approved → Terminal
        (lambda approved: approved, "Terminal"),
        # Judge rejected with 3+ retries → Terminal (fail)
        (lambda approved, ctx: ctx.iteration > 3, "Terminal"),
        # Judge rejected, retry → Worker
        (lambda approved: not approved, "Worker"),
    ],
)
```

### Chaining with add_edge

```python
# Simple sequential routing
builder.add_edge(router_executor, planner_executor)
builder.add_edge(planner_executor, worker_executor)
builder.add_edge(worker_executor, judge_executor)
```

---

## Best Practices

### 1. Agent Design

```python
# ✅ Good: Focused agent with single responsibility
class RouterAgent(BaseAgent):
    """Specialized agent for routing decisions only."""

    async def run(self, messages, **kwargs) -> AgentRunResponse:
        # Simple, focused logic
        decision = self._route(messages)
        return self._format_response(decision)

# ❌ Bad: Agent doing too much
class GodAgent(BaseAgent):
    """Agent that routes, plans, executes, and judges."""

    async def run(self, messages, **kwargs) -> AgentRunResponse:
        # Too many responsibilities
```

### 2. Error Handling

```python
class RobustAgent(BaseAgent):
    async def run(self, messages, **kwargs) -> AgentRunResponse:
        try:
            # Primary logic
            result = await self._process(messages)
            return result
        except TemporaryError:
            # Retry logic
            return await self._retry(messages)
        except PermanentError:
            # Fail gracefully
            return AgentRunResponse(
                Text="Unable to process request",
                AdditionalProperties={"error": "permanent"},
            )
```

### 3. Context Management

```python
from agentic_fleet.middleware.context import ContextModulator

class ContextAwareAgent(BaseAgent):
    async def run(self, messages, **kwargs) -> AgentRunResponse:
        team_id = kwargs.get("team_id", "default")

        async with ContextModulator.scope(team_id):
            # Context is now active
            ctx = ContextModulator.get_current()
            # Use ctx for team-specific config
            result = await self._process_with_context(messages, ctx)
            return result
```

### 4. Workflow Organization

```python
# ✅ Good: Clear workflow structure
workflow = (WorkflowBuilder()
    .set_start_executor(router_executor)
    .add_switch_case_edge_group("Router", [
        (is_complex, "Planner"),
        (Default, "Worker"),
    ])
    .add_edge(planner_executor, worker_executor)
    .add_edge(worker_executor, judge_executor)
    .add_switch_case_edge_group("Judge", [
        (lambda a: a, "Terminal"),
        (Default, "Worker"),
    ])
    .build())

# ❌ Bad: Disorganized workflow
workflow = (WorkflowBuilder()
    .add_edge(x, y)
    .add_edge(a, b)
    .set_start_executor(z)
    # Hard to follow
    .build())
```

### 5. Response Metadata

```python
class RouterAgent(BaseAgent):
    async def run(self, messages, **kwargs) -> AgentRunResponse:
        decision = await self._route(messages)

        return AgentRunResponse(
            messages=[ChatMessage(role="assistant", content=str(decision))],
            Text=str(decision),
            AdditionalProperties={
                "route_pattern": decision.pattern,
                "target_team": decision.target_team,
                "confidence": decision.confidence,
            },
        )
```

### 6. Testing Patterns

```python
import pytest
from agent_framework import WorkflowBuilder

@pytest.mark.asyncio
async def test_workflow_routing():
    """Test that complex tasks go to planner."""
    workflow = build_modules_workflow()

    events = await workflow.run({
        "task": "Research AI trends",
        "complexity": "complex",
    })

    outputs = events.get_outputs()
    assert "Planner" in str(outputs)
```

---

## Summary

| Pattern | Agent Framework Convention | Agentic Fleet Usage |
|---------|---------------------------|---------------------|
| BaseAgent | `class X(BaseAgent)` | `BaseFleetAgent` |
| run() | `async def run(messages, **kwargs)` | Agent execution |
| AgentRunResponse | Return type with `Text`, `Messages`, `AdditionalProperties` | Response format |
| WorkflowBuilder | `WorkflowBuilder().add_edge().build()` | `build_modules_workflow()` |
| Executor | Class/function for processing | `TerminalExecutor` |
| AgentExecutor | Wrap agents for workflows | Router, Planner, Worker, Judge |
| Conditional | `add_switch_case_edge_group()` | Routing logic |
