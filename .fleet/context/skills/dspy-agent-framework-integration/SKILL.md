---
name: dspy-agent-framework-integration
description: Comprehensive guide to integrating DSPy with Microsoft Agent Framework in AgenticFleet, covering typed signatures, assertions, routing cache, GEPA optimization, and agent handoffs.
---

# DSPy + Microsoft Agent Framework Integration

A comprehensive guide to the integration patterns between DSPy and Microsoft Agent Framework in AgenticFleet. This skill documents how to leverage DSPy's structured reasoning capabilities with the Agent Framework's orchestration primitives.

## Overview

AgenticFleet combines **DSPy** for intelligent prompt optimization and structured outputs with **Microsoft Agent Framework** for reliable multi-agent orchestration. This integration enables:

- **Typed Signatures**: Pydantic-validated DSPy outputs for type-safe orchestration
- **DSPy-Enhanced Agents**: ChatAgent wrappers with Chain of Thought, ReAct, and Program of Thought reasoning
- **Routing Cache**: TTL-based caching of routing decisions to reduce latency
- **GEPA Optimization**: Offline genetic prompt algorithm optimization
- **Checkpoint Storage**: Workflow resumption via agent-framework storage
- **Agent Handoffs**: Direct agent-to-agent transfers with context preservation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgenticFleet Integration                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ DSPyReasoner│────►│ AgentFactory│────►│  ChatAgent  │       │
│  │ (Signatures)│     │ (YAML Config)     │ (Enhanced)  │       │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘       │
│         │                   │                   │               │
│  ┌──────▼───────────────────▼───────────────────▼──────┐       │
│  │              Microsoft Agent Framework               │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │       │
│  │  │ Workflow │  │AgentThread│  │CheckpointStorage │   │       │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Typed Signatures with Pydantic

### Signature Definition Pattern

All DSPy signatures in AgenticFleet use Pydantic models for structured outputs:

```python
# src/agentic_fleet/dspy_modules/signatures.py
import dspy
from pydantic import BaseModel, Field
from typing import Literal

class TaskAnalysis(dspy.Signature):
    """Analyze a task with structured output."""
    task: str = dspy.InputField(desc="The user's task description")
    analysis: TaskAnalysisOutput = dspy.OutputField(
        desc="Structured analysis of the task"
    )

class TaskAnalysisOutput(BaseModel):
    """Pydantic model for typed signature output."""
    complexity: Literal["low", "medium", "high"] = Field(
        description="Estimated task complexity"
    )
    required_capabilities: list[str] = Field(
        description="List of required capabilities"
    )
    estimated_steps: int = Field(ge=1, le=50)
    preferred_tools: list[str] = Field(default_factory=list)
    needs_web_search: bool = Field(description="Whether web search needed")
    reasoning: str = Field(description="Reasoning behind analysis")
```

### Using TypedPredictor

```python
# src/agentic_fleet/dspy_modules/reasoner.py
from dspy import TypedPredictor

class DSPyReasoner(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyzer = TypedPredictor(TaskAnalysis)

    def analyze(self, task: str) -> TaskAnalysisOutput:
        result = self.analyzer(task=task)
        return result.analysis
```

### Field Validators

Normalize inputs with Pydantic validators:

```python
class RoutingDecisionOutput(BaseModel):
    assigned_to: list[str] = Field(min_length=1)
    execution_mode: Literal["delegated", "sequential", "parallel"]

    @field_validator("assigned_to", mode="before")
    @classmethod
    def normalize_agents(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [a.strip() for a in v.split(",") if a.strip()]
        return v

    @field_validator("execution_mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        mapping = {
            "delegate": "delegated",
            "single": "delegated",
            "sequence": "sequential",
            "concurrent": "parallel",
        }
        return mapping.get(v.strip().lower(), v)
```

## DSPy Assertions for Validation

### Hard and Soft Constraints

DSPy 3.x provides two assertion types for routing validation:

```python
# src/agentic_fleet/dspy_modules/assertions.py
import dspy

# Hard constraint: causes backtracking on failure
dspy.Assert(condition, "error message")

# Soft constraint: guides optimization without failure
dspy.Suggest(condition, "guidance message")
```

### Agent Assignment Validation

```python
def validate_agent_exists(
    assigned_agents: list[str],
    available_agents: list[str]
) -> bool:
    """Check all assigned agents exist in available pool."""
    # Hard constraint: must assign at least one agent
    Assert(len(assigned_agents) > 0, "Must assign at least one agent")

    # Soft suggestion: prefer matching case
    for agent in assigned_agents:
        Assert(
            agent.lower() in [a.lower() for a in available_agents],
            f"Agent '{agent}' not in available pool"
        )

    return True
```

### Execution Mode Validation

```python
def validate_execution_mode(
    assigned_agents: list[str],
    execution_mode: str
) -> bool:
    """Ensure execution mode matches agent count."""
    if len(assigned_agents) > 1 and execution_mode == "delegated":
        Suggest(
            len(assigned_agents) == 1,
            "Consider using 'parallel' for multiple agents"
        )
    return True
```

### Usage in Signatures

```python
class TaskRouting(dspy.Signature):
    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Available agents")
    context: str = dspy.InputField(desc="Execution context")
    decision: RoutingDecisionOutput = dspy.OutputField()

    def __call__(self, task, team, context):
        # Extract agent names from team description
        available_agents = extract_agent_names(team)

        # Validate before finalizing
        result = super().__call__(task=task, team=team, context=context)

        # Validate routing decision
        validate_agent_exists(result.decision.assigned_to, available_agents)
        validate_execution_mode(
            result.decision.assigned_to,
            result.decision.execution_mode
        )

        return result
```

## DSPy-Enhanced Agents

### Wrapping ChatAgent

```python
# src/agentic_fleet/agents/base.py
from agent_framework._agents import ChatAgent
import dspy

class DSPyEnhancedAgent(ChatAgent):
    def __init__(
        self,
        name: str,
        chat_client,
        instructions: str = "",
        enable_dspy: bool = True,
        reasoning_strategy: str = "chain_of_thought",
        **kwargs
    ):
        super().__init__(
            name=name,
            instructions=instructions,
            chat_client=chat_client,
            **kwargs
        )

        self.enable_dspy = enable_dspy
        self.reasoning_strategy = reasoning_strategy

        # Initialize reasoning modules
        if enable_dspy:
            self._init_reasoning_modules()

    def _init_reasoning_modules(self):
        """Initialize DSPy reasoning strategies."""
        if self.reasoning_strategy == "react":
            self.react_module = dspy.ReAct(
                "question -> answer",
                tools=self.tools
            )
        elif self.reasoning_strategy == "program_of_thought":
            self.pot_module = dspy.ProgramOfThought("question -> answer")
        elif self.reasoning_strategy == "chain_of_thought":
            self.cot_module = dspy.ChainOfThought("question -> answer")
```

### Task Enhancement

```python
class DSPyEnhancedAgent(ChatAgent):
    def _enhance_task_with_dspy(self, task: str, context: str = "") -> str:
        """Enhance task using DSPy reasoning."""
        if not self.enable_dspy:
            return task

        # Use Chain of Thought for complex tasks
        enhancer = dspy.ChainOfThought("task, context -> enhanced_task")
        result = enhancer(
            task=task,
            context=context or "No prior context"
        )

        return result.enhanced_task

    async def run(self, message, **kwargs):
        # Enhance task before execution
        enhanced_message = self._enhance_task_with_dspy(
            message,
            kwargs.get("context", "")
        )

        # Run with enhanced task
        return await super().run(enhanced_message, **kwargs)
```

## Routing Cache

### TTL-Based Cache Implementation

```python
# src/agentic_fleet/dspy_modules/reasoner_cache.py
import time
from typing import Any
from collections import OrderedDict

class RoutingCache:
    """TTL-based cache for routing decisions."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1024):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """Cache value with current timestamp."""
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
```

### Integration with DSPyReasoner

```python
# src/agentic_fleet/dspy_modules/reasoner.py
class DSPyReasoner(dspy.Module):
    def __init__(self, enable_routing_cache: bool = True, **kwargs):
        super().__init__()
        self.enable_routing_cache = enable_routing_cache
        self._routing_cache = RoutingCache(
            ttl_seconds=kwargs.get("cache_ttl_seconds", 300),
            max_size=kwargs.get("cache_max_entries", 1024)
        )

    def _generate_cache_key(
        self,
        task: str,
        team: str,
        context: str
    ) -> str:
        """Generate cache key from routing inputs."""
        import hashlib
        content = f"{task}:{team}:{context}"
        return hashlib.md5(content.encode()).hexdigest()

    def route(self, task: str, team: str, context: str) -> RoutingDecisionOutput:
        # Check cache first
        if self.enable_routing_cache:
            cache_key = self._generate_cache_key(task, team, context)
            cached = self._routing_cache.get(cache_key)
            if cached:
                return cached

        # Execute routing
        result = self.router(task=task, team=team, context=context)
        decision = result.decision

        # Cache result
        if self.enable_routing_cache:
            self._routing_cache.set(cache_key, decision)

        return decision
```

## GEPA Optimization

### Configuration

```yaml
# src/agentic_fleet/config/workflow_config.yaml
dspy:
  optimization:
    enabled: true
    examples_path: src/agentic_fleet/data/supervisor_examples.json
    use_gepa: true
    gepa_auto: light # light|medium|heavy
    gepa_reflection_model: gpt-5-mini
    gepa_history_min_quality: 8.0
    gepa_history_limit: 200
    gepa_val_split: 0.2
    gepa_seed: 13
    gepa_log_dir: .var/logs/dspy/gepa
```

### Optimization Command

```bash
# Run GEPA optimization
agentic-fleet optimize

# Output: .var/cache/dspy/compiled_reasoner.json
```

### Loading Compiled Modules

```python
# src/agentic_fleet/dspy_modules/reasoner.py
def _load_compiled_module(self) -> None:
    """Load optimized prompt weights from disk."""
    compiled_path = get_configured_compiled_reasoner_path()
    meta_path = Path(f"{compiled_path}.meta")

    if compiled_path.exists():
        # Verify source hash matches
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            expected_hash = meta.get("reasoner_source_hash")
            if expected_hash != get_reasoner_source_hash():
                logger.info("Compiled reasoner ignored (source hash mismatch)")
                return

        logger.info(f"Loading compiled reasoner from {compiled_path}")
        self.load(str(compiled_path))
```

## Agent Framework Integration

### Creating ChatAgent from YAML

```python
# src/agentic_fleet/agents/coordinator.py
from agent_framework._agents import ChatAgent

class AgentFactory:
    def create_agent(self, name: str, config: dict) -> ChatAgent:
        """Create ChatAgent from YAML configuration."""
        model_id = config.get("model")
        instructions = self._resolve_instructions(config.get("instructions", ""))
        tools = self._resolve_tools(config.get("tools", []))

        return ChatAgent(
            name=name,
            description=config.get("description", ""),
            instructions=instructions,
            chat_client=self._create_chat_client(model_id),
            tools=tools
        )

    def _resolve_instructions(self, instructions_ref: str) -> str:
        """Resolve dynamic prompts or static references."""
        if instructions_ref.startswith("prompts."):
            # Dynamic DSPy prompt generation
            return self._generate_dynamic_prompt(instructions_ref)
        # Static prompt lookup
        return get_static_prompt(instructions_ref)
```

### Dynamic Prompt Generation

```python
# src/agentic_fleet/agents/coordinator.py
from dspy import ChainOfThought
from agentic_fleet.dspy_modules.signatures import PlannerInstructionSignature

class AgentFactory:
    def __init__(self):
        self.instruction_generator = ChainOfThought(PlannerInstructionSignature)

    def _generate_dynamic_prompt(self, ref: str) -> str:
        """Generate prompt using DSPy."""
        if ref == "prompts.planner":
            result = self.instruction_generator(
                available_agents=self._get_agent_descriptions(),
                task_goals="Plan and coordinate multi-agent workflows"
            )
            return result.instructions
        return ""
```

### Workflow with Checkpointing

```python
# src/agentic_fleet/workflows/supervisor.py
from agent_framework._workflows import (
    WorkflowStartedEvent,
    WorkflowStatusEvent,
    WorkflowOutputEvent,
    ExecutorCompletedEvent,
    RequestInfoEvent,  # HITL support
    FileCheckpointStorage
)

class SupervisorWorkflow:
    def __init__(self, context, checkpoint_dir: str = ".var/checkpoints"):
        self.context = context
        self.checkpoint_storage = FileCheckpointStorage(checkpoint_dir)

    async def run_stream(self, task: str, checkpoint_id: str | None = None):
        """Run workflow with optional checkpoint resume."""
        if checkpoint_id:
            # Resume from checkpoint
            await self._resume_from_checkpoint(checkpoint_id)
        else:
            # Start fresh
            async for event in self._execute_pipeline(task):
                yield event

    async def _resume_from_checkpoint(self, checkpoint_id: str):
        """Resume workflow execution from checkpoint."""
        state = self.checkpoint_storage.load(checkpoint_id)

        # Restore workflow state
        self.context.restore_from_state(state)

        # Continue execution
        async for event in self._continue_pipeline():
            yield event
```

### Agent Handoffs

```python
# src/agentic_fleet/workflows/strategies.py
from agent_framework._agents import ChatAgent

class HandoffManager:
    """Manage agent-to-agent transfers with context preservation."""

    def __init__(self):
        self._handoff_history: list[dict] = []

    def prepare_handoff(
        self,
        from_agent: ChatAgent,
        to_agent: ChatAgent,
        context: dict
    ) -> dict:
        """Prepare handoff input with accumulated context."""
        handoff_input = {
            "task": context.get("original_task"),
            "findings": context.get("findings", []),
            "decisions": context.get("decisions", []),
            "remaining_work": context.get("remaining_work", []),
            "from_agent_summary": self._summarize_agent_work(from_agent)
        }

        self._handoff_history.append({
            "from": from_agent.name,
            "to": to_agent.name,
            "input": handoff_input
        })

        return handoff_input

    def execute_sequential_with_handoffs(
        self,
        agents: list[ChatAgent],
        tasks: list[str]
    ) -> list[dict]:
        """Execute tasks with agent handoffs."""
        context = {"original_task": tasks[0], "findings": [], "decisions": []}
        results = []

        for i, (agent, task) in enumerate(zip(agents, tasks)):
            context["remaining_work"] = tasks[i + 1:]

            handoff_input = self.prepare_handoff(
                from_agent=agents[i - 1] if i > 0 else None,
                to_agent=agent,
                context=context
            )

            result = self._run_agent_with_context(agent, task, handoff_input)

            context["findings"].extend(result.get("findings", []))
            context["decisions"].extend(result.get("decisions", []))
            results.append(result)

        return results
```

## Configuration Reference

### workflow_config.yaml

```yaml
# DSPy Configuration
dspy:
  model: gpt-5-mini
  routing_model: gpt-5-mini
  use_typed_signatures: true
  enable_routing_cache: true
  routing_cache_ttl_seconds: 300
  require_compiled: false # true in production

  # Dynamic Prompts
  dynamic_prompts:
    enabled: true
    signatures_path: src/agentic_fleet/dspy_modules/signatures.py

  # GEPA Optimization
  optimization:
    enabled: true
    use_gepa: true
    gepa_auto: light

# Workflow Configuration
workflow:
  supervisor:
    max_rounds: 15
    enable_streaming: true

  checkpointing:
    checkpoint_dir: .var/checkpoints

# Agent Configuration
agents:
  researcher:
    model: gpt-4.1-mini
    tools: [TavilySearchTool]
    reasoning:
      effort: medium
      verbosity: normal
```

## Common Patterns

### 1. Simple Task (Fast-Path)

```python
# src/agentic_fleet/workflows/helpers.py
def is_simple_task(task: str) -> bool:
    """Check if task qualifies for fast-path processing."""
    simple_patterns = [
        r"^(hi|hello|hey|how are you|what's up)",
        r"^\d+\s*[\+\-\*/]\s*\d+$",  # Simple math
        r"^(what is|who is|where is|when did)\s+\w+",  # Simple facts
    ]
    return any(re.match(p, task.lower()) for p in simple_patterns)
```

### 2. Multi-Agent Parallel Execution

```python
# src/agentic_fleet/workflows/strategies.py
async def execute_parallel(
    agents: list[ChatAgent],
    task: str
) -> list[dict]:
    """Execute task across multiple agents concurrently."""
    async def run_agent(agent):
        return {
            "agent": agent.name,
            "result": await agent.run(task)
        }

    results = await asyncio.gather(*[run_agent(a) for a in agents])
    return results
```

### 3. Quality-Based Refinement Loop

```python
# src/agentic_fleet/workflows/executors.py
async def run_quality_phase(
    task: str,
    result: str,
    threshold: float = 7.0
) -> tuple[str, bool]:
    """Evaluate quality and refine if needed."""
    assessment = await self.reasoner.assess_quality(task, result)

    if assessment.score < threshold:
        # Refine the result
        refined = await self._refine_result(task, result, assessment.feedback)
        return refined, True

    return result, False
```

## Debugging Tips

1. **Routing issues**: Check `.var/logs/execution_history.jsonl` for routing decisions
2. **Slow workflows**: Reduce `gepa_max_metric_calls` in config
3. **DSPy fallback**: If no compiled cache, system uses zero-shot
4. **Type errors**: Run `make type-check` before commits

## Related Documentation

- [DSPy Documentation](https://dspy.ai)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- AgenticFleet: `docs/guides/dspy-agent-framework-integration.md`
