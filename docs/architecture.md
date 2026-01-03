# Agentic Fleet v2.0 - Architecture Guide

## Overview

Agentic Fleet v2.0 is a modular agent orchestration system that combines **Microsoft Agent Framework** for workflow orchestration with **DSPy** for type-safe cognitive layer (LLM prompting and optimization). The system enables team-based agent routing with conditional workflow execution and self-improvement capabilities.

### Core Principles

1. **Separation of Concerns**: Agent Framework handles orchestration; DSPy handles cognition
2. **Type Safety**: Pydantic models for all data structures; DSPy signatures for LLM interactions
3. **Team-Based Context**: Each team (research, coding, default) has isolated configuration
4. **Self-Improvement**: GEPA (Gradient-Efficient Prompt Alignment) enables continuous optimization

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│   │  CLI Client │    │  FastAPI    │    │   Webhook   │                    │
│   │             │    │ /run /train │    │             │                    │
│   └─────────────┘    └─────────────┘    └─────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agentic Fleet Core                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    ContextModulator                                  │   │
│   │              (contextvars-based team scoping)                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                       TEAM_REGISTRY                                  │   │
│   │    research  │  coding  │  default  │  (extensible)                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    DSPy Configuration                                │   │
│   │     (ChainOfThought, Signatures, Optimizers)                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Agent Framework Layer                                   │
│                                                                             │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│   │  Router  │────>│  Planner │────>│  Worker  │────>│  Judge   │          │
│   │  Agent   │     │  Agent   │     │  Agent   │     │  Agent   │          │
│   └──────────┘     └──────────┘     └──────────┘     └──────────┘          │
│        │                                    │              │                │
│        │                                    │              ▼                │
│        │                                    │        ┌──────────┐           │
│        │                                    │        │ Terminal │           │
│        │                                    │        │ Executor │           │
│        │                                    │        └──────────┘           │
│        ▼                                                                   │
│   ┌──────────┐                                                         │
│   │ Terminal │                                                         │
│   │ Executor │                                                         │
│   └──────────┘                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GEPA Self-Improvement Layer                              │
│                                                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐           │
│   │TraceCollector│────>│FleetOptimizer│────>│  planner_opt.json│           │
│   │(extract traces)│    │(BootstrapFewShot)│ (compiled state)  │           │
│   └──────────────┘     └──────────────┘     └──────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Configuration Layer (`config.py`)

The configuration layer provides centralized team management:

```python
# src/agentic_fleet/config.py
from typing import TypedDict

class TeamConfig(TypedDict):
    tools: list[str]
    credentials: dict
    description: str

class TeamContext(TeamContext):
    team_id: str

TEAM_REGISTRY: dict[str, TeamConfig] = {
    "research": TeamConfig(
        tools=["browser", "search", "synthesize"],
        credentials={},
        description="Web research and synthesis"
    ),
    "coding": TeamConfig(
        tools=["repo_read", "repo_write", "tests"],
        credentials={},
        description="Code changes and validation"
    ),
    "default": TeamConfig(
        tools=["general"],
        credentials={},
        description="Generalist fallback"
    )
}

def list_teams() -> list[str]:
    """Return list of available team names."""
    return list(TEAM_REGISTRY.keys())
```

### DSPy Cognitive Layer (`dspy_modules/`)

#### Signatures (`signatures.py`)

DSPy signatures define the interface between agents and LLMs:

```python
# src/agentic_fleet/dspy_modules/signatures.py
from pydantic import BaseModel, Field
import dspy

class TaskContext(BaseModel):
    """Context passed into planner/worker modules."""
    team_id: str
    constraints: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    """Normalized worker output."""
    status: str  # "success", "error", "pending"
    content: str
    artifacts: list[str] = Field(default_factory=list)

class RoutingDecision(BaseModel):
    """Router output containing pattern and target team."""
    pattern: str  # "direct", "simple", "complex"
    target_team: str
    reasoning: str

# DSPy Signatures
class RouterSignature(dspy.Signature):
    """Route task to appropriate team and complexity pattern."""
    task: str = dspy.InputField(desc="the user's task description")
    decision: RoutingDecision = dspy.OutputField(desc="routing decision")

class PlannerSignature(dspy.Signature):
    """Create execution plan for complex tasks."""
    task: str = dspy.InputField(desc="the user's task")
    context: TaskContext = dspy.InputField(desc="team context with constraints and tools")
    plan: str = dspy.OutputField(desc="step-by-step execution plan")
    reasoning: str = dspy.OutputField(desc="reasoning for the plan")

class WorkerSignature(dspy.Signature):
    """Execute a single step of the plan."""
    step: str = dspy.InputField(desc="the step to execute")
    context: TaskContext = dspy.InputField(desc="team context")
    action: str = dspy.OutputField(desc="action taken")
    result: ExecutionResult = dspy.OutputField(desc="execution result")

class JudgeSignature(dspy.Signature):
    """Review and approve/reject worker output."""
    original_task: str = dspy.InputField(desc="original user task")
    result: ExecutionResult = dspy.InputField(desc="worker result to review")
    is_approved: bool = dspy.OutputField(desc="whether result meets quality bar")
    critique: str = dspy.OutputField(desc="feedback for revision if rejected")
```

#### Validation (`validation.py`)

Reusable validators ensure data integrity:

```python
# src/agentic_fleet/dspy_modules/validation.py
from pydantic import field_validator

VALID_ROUTING_PATTERNS = {"direct", "simple", "complex"}

def validate_non_empty_str(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()

def validate_team_name(value: str) -> str:
    from agentic_fleet.config import TEAM_REGISTRY
    if value not in TEAM_REGISTRY:
        raise ValueError(f"Unknown team: {value}")
    return value

def validate_routing_pattern(value: str) -> str:
    if value not in VALID_ROUTING_PATTERNS:
        raise ValueError(f"Invalid pattern: {value}. Must be one of {VALID_ROUTING_PATTERNS}")
    return value
```

### Agent Layer (`agents/`)

#### BaseFleetAgent (`base.py`)

The base agent wraps Microsoft Agent Framework with DSPy cognition:

```python
# src/agentic_fleet/agents/base.py
from agent_framework import BaseAgent, ChatMessage, AgentRunResponse
import dspy
from typing import Any
from agentic_fleet.dspy_modules.signatures import TaskContext
from agentic_fleet.middleware.context import ContextModulator

class FleetBrain(dspy.Module):
    """Wrapper that injects active team context into DSPy calls."""
    def __init__(self, signature: type[dspy.Signature], brain_state_path: str | None = None):
        super().__init__()
        self.signature = signature
        self.brain_state_path = brain_state_path
        self.program = dspy.ChainOfThought(signature)
        if brain_state_path:
            self.program.load(brain_state_path)

    def forward(self, **kwargs: Any) -> Any:
        """Inject context if not provided, then call DSPy program."""
        if "context" in self.signature.input_fields and "context" not in kwargs:
            ctx = ContextModulator.get_current()
            if ctx is not None:
                kwargs["context"] = TaskContext(**ctx)
        return self.program(**kwargs)

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
            # Build kwargs for DSPy brain from messages
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

#### RouterAgent (`router.py`)

Specialized router with routing signature:

```python
# src/agentic_fleet/agents/router.py
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import RouterSignature, RoutingDecision
import json

class RouterAgent(BaseFleetAgent):
    """Specialized agent for routing decisions."""

    def __init__(self):
        super().__init__(
            name="Router",
            role="router",
            signature=RouterSignature,
        )

    async def run(self, messages, **kwargs) -> AgentRunResponse:
        """Execute routing and attach decision to additional_properties."""
        response = await super().run(messages, **kwargs)

        # Extract routing decision from brain prediction
        prediction = self.brain.program
        if hasattr(prediction, 'decision'):
            decision = prediction.decision
            if isinstance(decision, str):
                decision = RoutingDecision.model_validate_json(decision)
            elif hasattr(decision, 'model_dump'):
                decision = RoutingDecision(**decision.model_dump())

            response.AdditionalProperties = {
                "route_pattern": decision.pattern,
                "target_team": decision.target_team,
                "original_task": messages[-1].content if isinstance(messages, list) else messages,
            }

        return response
```

### Workflow Layer (`workflows/modules.py`)

The workflow builder creates conditional execution graphs:

```python
# src/agentic_fleet/workflows/modules.py
from agent_framework import WorkflowBuilder, AgentExecutor, Executor, TerminalExecutor
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature, WorkerSignature, JudgeSignature
from typing import Callable

def _is_complex(pattern: str) -> bool:
    return pattern in {"complex", "complex_council"}

def _is_simple(pattern: str) -> bool:
    return pattern in {"simple", "simple_tool"}

def _is_direct(pattern: str) -> bool:
    return pattern in {"direct", "direct_answer"}

def build_modules_workflow(planner_state_path: str | None = None) -> WorkflowBuilder:
    """Build the Router → Planner → Worker → Judge → Terminal workflow."""
    builder = WorkflowBuilder(name="modules-workflow")

    # Create agents
    router_agent = RouterAgent()
    planner_agent = BaseFleetAgent(
        "Planner", "architect", PlannerSignature,
        brain_state_path=planner_state_path,
    )
    worker_agent = BaseFleetAgent(
        "Worker", "executor", WorkerSignature,
    )
    judge_agent = BaseFleetAgent(
        "Judge", "critic", JudgeSignature,
    )

    # Wrap in executors
    router_executor = AgentExecutor(router_agent, id="Router")
    planner_executor = AgentExecutor(planner_agent, id="Planner")
    worker_executor = AgentExecutor(worker_agent, id="Worker", output_response=True)
    judge_executor = AgentExecutor(judge_agent, id="Judge", output_response=True)
    terminal = TerminalExecutor(id="Terminal")

    # Build conditional graph
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

    return builder
```

### Middleware Layer (`middleware/context.py`)

Context modulation enables team-scoped configuration:

```python
# src/agentic_fleet/middleware/context.py
from contextvars import ContextVar
from agentic_fleet.config import TeamConfig, TEAM_REGISTRY, TeamContext
from typing import AsyncGenerator
import asyncio

class TeamContextVars:
    _active_context: ContextVar[TeamContext | None] = ContextVar("active_context", default=None)

    @staticmethod
    async def scope(team_id: str) -> AsyncGenerator[TeamContext, None]:
        """Temporarily activate the team context for this async scope."""
        resolved_team = team_id if team_id in TEAM_REGISTRY else "default"
        config = TEAM_REGISTRY[resolved_team]

        context_data = TeamContext(
            team_id=resolved_team,
            **config,
        )
        token = TeamContextVars._active_context.set(context_data)
        try:
            yield context_data
        finally:
            TeamContextVars._active_context.reset(token)

    @staticmethod
    def get_current() -> TeamContext | None:
        """Get the currently active team context."""
        return TeamContextVars._active_context.get()

# Alias for backward compatibility
ContextModulator = TeamContextVars
```

### GEPA Self-Improvement (`gepa/`)

#### TraceCollector (`collector.py`)

Extracts training examples from workflow execution:

```python
# src/agentic_fleet/gepa/collector.py
from agent_framework.events import AgentRunEvent
import dspy
from agentic_fleet.dspy_modules.signatures import TaskContext
from typing import Any

class TraceCollector:
    """Extracts DSPy training examples from workflow history."""

    def __init__(self, team_id: str = "default"):
        self.team_id = team_id
        self.traces: list[dict[str, Any]] = []

    def extract_examples(self, events: list[AgentRunEvent]) -> list[dspy.Example]:
        """Extract training examples from completed workflow traces."""
        examples = []

        for event in events:
            if event.kind == "AgentRunCompleted":
                # Extract router, planner, worker, judge decisions
                if self._judge_approved(event):
                    example = self._build_example(event)
                    if example:
                        examples.append(example)

        return examples

    def _judge_approved(self, event: AgentRunEvent) -> bool:
        """Check if judge approved the output."""
        # Parse agent output to determine approval
        return True  # Simplified

    def _build_example(self, event: AgentRunEvent) -> dspy.Example | None:
        """Build dspy.Example from approved trace."""
        try:
            return dspy.Example(
                task=event.input,
                context=TaskContext(team_id=self.team_id),
                plan=event.planning_result,
                result=event.output,
            ).with_inputs("task", "context")
        except Exception:
            return None
```

#### FleetOptimizer (`optimizer.py`)

Compiles DSPy programs using BootstrapFewShot:

```python
# src/agentic_fleet/gepa/optimizer.py
import dspy
from dspy.teleprompt import BootstrapFewShot
from agentic_fleet.dspy_modules.signatures import PlannerSignature
from pathlib import Path

class FleetOptimizer:
    """Compiles DSPy programs using GEPA methodology."""

    def __init__(self, output_dir: str = "dspy_modules/state"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compile(
        self,
        program: dspy.Module,
        training_data: list[dspy.Example],
        output_path: str | None = None,
    ) -> dspy.Module:
        """Compile the program using BootstrapFewShot."""
        optimizer = BootstrapFewShot(
            metric=self._default_metric,
            max_bootstrapped_demos=4,
            max_labeled_demos=16,
        )

        compiled = optimizer.compile(program, trainset=training_data)

        # Save compiled state
        save_path = output_path or str(self.output_dir / "planner_opt.json")
        compiled.save(save_path)

        return compiled

    def _default_metric(self, example: dspy.Example, prediction: Any, **kwargs) -> bool:
        """Default metric for optimization."""
        # Check if plan was approved by judge
        return kwargs.get("is_approved", False)
```

## Configuration Files

### Environment Variables

```bash
# LLM Configuration
LITELLM_PROXY_URL=http://localhost:4000
LITELLM_SERVICE_KEY=sk-...
DSPY_MODEL=deepseek-v3.2
DSPY_TEMPERATURE=0
DSPY_MAX_TOKENS=4096

# Database (optional)
DATABASE_URL=postgresql://...
```

### LiteLLM Config (`litellm_config.yaml`)

```yaml
model_list:
  - model_name: gpt-5-mini
    litellm_params:
      model: openai/gpt-5-mini
      api_key: env.openai_api_key
    tier: 1

  - model_name: deepseek-v3.2
    litellm_params:
      model: deepseek/deepseek-v3.2
      api_key: env.deepseek_api_key
    tier: 1

  - model_name: gemini-3-flash
    litellm_params:
      model: google/gemini-1.5-flash
      api_key: env.gemini_api_key
    tier: 2
```

## Dependencies

```toml
# pyproject.toml (key dependencies)
agent-framework = ">=1.0.0b251223"
dspy-ai = ">=3.0.0"
litellm = {version = ">=1.40.0", extras = ["proxy"]}
fastapi = ">=0.110.0"
pydantic = ">=2.7.0"
langfuse = ">=2.30.0"
```

## Execution Flow

1. **Client Request**: `POST /run` with message and optional team_id
2. **Router Analysis**: RouterAgent analyzes task complexity
3. **Conditional Routing**:
   - `direct`: Router → Worker → Terminal
   - `simple`: Router → Worker → Terminal
   - `complex`: Router → Planner → Worker → Judge → Terminal
4. **Execution**: Each agent uses DSPy signature for LLM cognition
5. **Judge Review**: Worker output reviewed; rejected outputs retry
6. **Trace Collection**: Approved traces captured for training
7. **Optimization**: Periodic `/train` calls compile improved prompts
