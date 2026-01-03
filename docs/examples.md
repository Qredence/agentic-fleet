# Examples

## Basic Usage

### Creating a Router Agent

```python
from agentic_fleet.agents.router import RouterAgent
from agent_framework import ChatMessage

async def main():
    router = RouterAgent()

    # Simple message
    response = await router.run("Research AI trends")

    print(response.Text)
    print(response.AdditionalProperties)
    # Output: {
    #   "route_pattern": "complex",
    #   "target_team": "research"
    # }

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Creating a Custom Agent

```python
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature
from agent_framework import ChatMessage

class CustomPlanner(BaseFleetAgent):
    def __init__(self):
        super().__init__(
            name="CustomPlanner",
            role="architect",
            signature=PlannerSignature,
        )

async def main():
    planner = CustomPlanner()

    response = await planner.run(
        messages="Create a Python web scraper",
        team_id="coding",
    )

    print(response.Text)
```

### Using Team Context

```python
from agentic_fleet.middleware.context import ContextModulator
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import WorkerSignature
from agent_framework import ChatMessage

async def main():
    worker = BaseFleetAgent("Worker", "executor", WorkerSignature)

    # Research team context
    async with ContextModulator.scope("research"):
        response = await worker.run(
            messages="Search for latest AI papers",
            team_id="research",
        )

    print(response.Text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Workflow Examples

### Building a Simple Workflow

```python
from agent_framework import WorkflowBuilder, AgentExecutor
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import WorkerSignature

async def simple_workflow():
    # Create agents
    router = RouterAgent()
    worker = BaseFleetAgent("Worker", "executor", WorkerSignature)

    # Wrap in executors
    router_executor = AgentExecutor(router, id="Router")
    worker_executor = AgentExecutor(worker, id="Worker", output_response=True)

    # Build workflow
    workflow = (WorkflowBuilder()
        .set_start_executor(router_executor)
        .add_edge(router_executor, worker_executor)
        .build())

    # Run
    events = await workflow.run("What is 2+2?")
    print(events.get_outputs())

if __name__ == "__main__":
    import asyncio
    asyncio.run(simple_workflow())
```

### Conditional Workflow

```python
from agent_framework import WorkflowBuilder, AgentExecutor
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature, WorkerSignature

def build_conditional_workflow():
    # Create agents
    router = RouterAgent()
    planner = BaseFleetAgent("Planner", "architect", PlannerSignature)
    worker = BaseFleetAgent("Worker", "executor", WorkerSignature)

    # Wrap in executors
    router_executor = AgentExecutor(router, id="Router")
    planner_executor = AgentExecutor(planner, id="Planner")
    worker_executor = AgentExecutor(worker, id="Worker")

    # Build with conditional routing
    builder = WorkflowBuilder(name="conditional")
    builder.set_start_executor(router_executor)

    # Complex → Planner; Simple/Direct → Worker
    builder.add_switch_case_edge_group(
        "Router",
        [
            (lambda p: p in {"complex"}, "Planner"),
            (lambda p: p in {"simple", "direct"}, "Worker"),
        ],
    )

    builder.add_edge(planner_executor, worker_executor)

    return builder.build()
```

---

## DSPy Examples

### Creating a Signature

```python
import dspy

class CustomSignature(dspy.Signature):
    """Custom task signature."""
    input_text: str = dspy.InputField(desc="input text to process")
    output_text: str = dspy.OutputField(desc="processed output")

# Use with ChainOfThought
module = dspy.ChainOfThought(CustomSignature)

# Execute
result = module(input_text="Hello, world!")
print(result.output_text)
```

### Training with Examples

```python
import dspy

# Create training examples
training_data = [
    dspy.Example(
        task="Analyze data",
        context={"team_id": "default"},
        plan="1. Load data\n2. Analyze\n3. Report",
        result="Analysis complete"
    ).with_inputs("task", "context"),

    dspy.Example(
        task="Research topic",
        context={"team_id": "research"},
        plan="1. Search\n2. Read\n3. Summarize",
        result="Research complete"
    ).with_inputs("task", "context"),
]

# Compile with optimizer
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(
    metric=lambda ex, pred: pred.plan == ex.plan,
    max_bootstrapped_demos=4,
)

compiled = optimizer.compile(
    student=dspy.ChainOfThought(PlannerSignature),
    trainset=training_data,
)

# Save
compiled.save("./custom_planner.json")
```

### Loading Compiled Program

```python
import dspy

# Load compiled program
program = dspy.ChainOfThought(PlannerSignature)
program.load("./custom_planner.json")

# Execute
result = program(
    task="Create a report",
    context={"team_id": "default"},
)

print(result.plan)
print(result.reasoning)
```

---

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from pydantic import BaseModel
from agentic_fleet.workflows.modules import build_modules_workflow

app = FastAPI()

class RunRequest(BaseModel):
    message: str
    team_id: str = "default"

class RunResponse(BaseModel):
    output: str
    trace: list[dict]

@app.post("/run")
async def run_workflow(request: RunRequest):
    workflow = build_modules_workflow()
    events = await workflow.run(request.message)

    return RunResponse(
        output=events.get_outputs()[-1] if events.get_outputs() else "",
        trace=[{"status": "completed"}],
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Using with LiteLLM

```python
import dspy
from litellm import LM

# Configure with LiteLLM
llm = dspy.LM(
    model="deepseek-v3.2",
    api_base="http://localhost:4000",
    api_key="sk-...",
)

dspy.configure(lm=llm)

# Now DSPy uses LiteLLM proxy
program = dspy.ChainOfThought(PlannerSignature)
result = program(task="Test task", context={"team_id": "default"})
```

---

## Test Examples

### Testing an Agent

```python
import pytest
from agentic_fleet.agents.router import RouterAgent

@pytest.mark.asyncio
async def test_router_direct():
    router = RouterAgent()

    response = await router.run("What is 2+2?")

    assert response.AdditionalProperties["route_pattern"] in {"direct", "simple"}
    assert "default" in response.AdditionalProperties["target_team"]

@pytest.mark.asyncio
async def test_router_complex():
    router = RouterAgent()

    response = await router.run("Research the latest developments in quantum computing")

    assert response.AdditionalProperties["route_pattern"] == "complex"
    assert response.AdditionalProperties["target_team"] == "research"
```

### Testing a Workflow

```python
import pytest
from agent_framework import WorkflowBuilder, AgentExecutor
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import WorkerSignature

@pytest.mark.asyncio
async def test_simple_workflow():
    router = RouterAgent()
    worker = BaseFleetAgent("Worker", "executor", WorkerSignature)

    router_executor = AgentExecutor(router, id="Router")
    worker_executor = AgentExecutor(worker, id="Worker")

    workflow = (WorkflowBuilder()
        .set_start_executor(router_executor)
        .add_edge(router_executor, worker_executor)
        .build())

    events = await workflow.run("Simple question")

    assert events.get_outputs()
    assert len(events.get_outputs()) > 0
```

### Mocking DSPy

```python
from unittest.mock import MagicMock
import dspy

# Mock LM for testing
class MockLM:
    def __init__(self, response):
        self.response = response

    def __call__(self, *args, **kwargs):
        return MagicMock(**self.response)

def test_with_mocked_dspy():
    # Configure with mock
    mock_lm = MockLM({"decision": MagicMock(pattern="simple", target_team="default")})
    dspy.settings.configure(lm=mock_lm)

    router = RouterAgent()

    # Now uses mock
    import asyncio
    response = asyncio.run(router.run("Test"))

    assert response.AdditionalProperties["route_pattern"] == "simple"
```

---

## Configuration Examples

### Custom Team Configuration

```python
from agentic_fleet.config import TEAM_REGISTRY, TeamConfig

# Add custom team
TEAM_REGISTRY["analytics"] = TeamConfig(
    tools=["sql_query", "data_visualization", "statistics"],
    credentials={},
    description="Data analytics and visualization"
)

# Now available
from agentic_fleet.middleware.context import ContextModulator

async def use_analytics():
    async with ContextModulator.scope("analytics"):
        # Team context is now "analytics"
        pass
```

### Custom DSPy Configuration

```python
import dspy

# Configure for different model
dspy.configure(
    lm=dspy.LM(
        "openai/gpt-4o",
        temperature=0.1,
        max_tokens=4096,
    ),
    rm_cache=True,  # Enable response caching
    compile_tasks=False,
)
```

---

## Best Practices

### 1. Always Use Context

```python
# ✅ Good
async with ContextModulator.scope(team_id):
    response = await agent.run(message)

# ❌ Bad - Context not active
response = await agent.run(message)
```

### 2. Handle Errors Gracefully

```python
async def safe_run(agent, message, team_id):
    try:
        async with ContextModulator.scope(team_id):
            return await agent.run(message)
    except Exception as e:
        return AgentRunResponse(
            Text=f"Error: {str(e)}",
            AdditionalProperties={"error": True},
        )
```

### 3. Use Type Annotations

```python
from typing import AsyncGenerator

async def context_generator(team_id: str) -> AsyncGenerator[dict, None]:
    """Generator for context-aware operations."""
    async with ContextModulator.scope(team_id):
        ctx = ContextModulator.get_current()
        yield ctx
```

### 4. Log Appropriately

```python
import logging

logger = logging.getLogger(__name__)

async def tracked_run(agent, message):
    logger.info(f"Starting agent: {agent.name}")
    response = await agent.run(message)
    logger.info(f"Completed agent: {agent.name}")
    return response
```

---

## Summary

| Pattern | Example | Use Case |
|---------|---------|----------|
| Router Agent | `RouterAgent()` | Route tasks to teams |
| Custom Agent | `BaseFleetAgent(name, role, signature)` | Create custom agents |
| Team Context | `ContextModulator.scope("research")` | Set team context |
| Workflow | `WorkflowBuilder().add_edge().build()` | Orchestrate agents |
| DSPy Signature | `class X(dspy.Signature)` | Define LLM interface |
| ChainOfThought | `dspy.ChainOfThought(Signature)` | Add reasoning |
| Training | `BootstrapFewShot.compile()` | Optimize prompts |
| FastAPI | `@app.post("/run")` | Expose as API |
