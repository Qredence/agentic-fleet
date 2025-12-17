# AgenticFleet System Overview

A comprehensive technical guide to the AgenticFleet multi-agent orchestration system.

---

## Overview

### Purpose and Scope

AgenticFleet is a **multi-agent orchestration framework** that combines DSPy's intelligent prompt optimization with Microsoft's Agent Framework to create self-improving workflows. It transforms simple task requests into orchestrated multi-agent operations through a sophisticated 5-phase pipeline.

**Core Value Proposition:**

- **Intelligent Routing**: DSPy-powered analysis determines optimal agent assignment
- **Multi-Modal Execution**: Support for delegated, sequential, parallel, handoff, and discussion modes
- **Self-Improvement**: Learns from execution history to improve routing decisions
- **Full Observability**: OpenTelemetry tracing, structured logging, and execution history

### What is AgenticFleet?

At its core, AgenticFleet answers a fundamental question: _"Given a user's task, how do we automatically orchestrate specialized AI agents to produce optimal results?"_

Traditional approaches require manual prompt engineering and agent coordination. AgenticFleet automates this through:

1. **Task Analysis** - Understanding complexity, required capabilities, and tool needs
2. **Intelligent Routing** - Selecting agents and execution mode using learned patterns
3. **Coordinated Execution** - Running agents in parallel, sequence, or delegation
4. **Quality Assurance** - Evaluating and optionally refining outputs
5. **Continuous Learning** - Capturing decisions for future optimization

### System Components and Code Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AgenticFleet Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐ │
│  │   CLI       │    │  Web UI     │    │        Python API               │ │
│  │ (Typer)     │    │ (React)     │    │ (create_supervisor_workflow)    │ │
│  └──────┬──────┘    └──────┬──────┘    └─────────────┬───────────────────┘ │
│         │                  │                         │                      │
│         └──────────────────┼─────────────────────────┘                      │
│                            │                                                │
│                   ┌────────▼────────┐                                       │
│                   │  FastAPI Server │                                       │
│                   │  (WebSocket/SSE)│                                       │
│                   └────────┬────────┘                                       │
│                            │                                                │
│         ┌──────────────────┼──────────────────┐                             │
│         │                  │                  │                             │
│  ┌──────▼──────┐   ┌───────▼───────┐  ┌──────▼──────┐                       │
│  │ Supervisor  │   │  DSPyReasoner │  │ AgentFactory│                       │
│  │  Workflow   │   │  (Analysis,   │  │ (Creates    │                       │
│  │ (5 Phases)  │   │   Routing,    │  │  Agents)    │                       │
│  │             │   │   Quality)    │  │             │                       │
│  └──────┬──────┘   └───────┬───────┘  └──────┬──────┘                       │
│         │                  │                 │                              │
│         │          ┌───────▼───────┐         │                              │
│         │          │ ToolRegistry  │◄────────┘                              │
│         │          │ (Tavily, Code,│                                        │
│         │          │  Browser, MCP)│                                        │
│         │          └───────────────┘                                        │
│         │                                                                   │
│  ┌──────▼────────────────────────────────────────────────────────────────┐  │
│  │                      Storage & Observability                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ Execution   │  │ Conversation│  │ OpenTelemetry│ │ Cosmos DB   │  │  │
│  │  │ History     │  │ Store       │  │ Tracing      │ │ (optional)  │  │  │
│  │  │ (.jsonl)    │  │ (.json)     │  │ (Jaeger)     │ │             │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Packages:**

| Package         | Purpose                                  | Key Files                                         |
| --------------- | ---------------------------------------- | ------------------------------------------------- |
| `workflows/`    | Orchestration & 5-phase pipeline         | `supervisor.py`, `executors.py`, `strategies.py`  |
| `dspy_modules/` | DSPy signatures, reasoning, typed models | `reasoner.py`, `signatures.py`, `typed_models.py` |
| `agents/`       | Agent creation and prompts               | `coordinator.py`, `prompts.py`                    |
| `tools/`        | Tool adapters (Tavily, Code, MCP)        | `tavily_tool.py`, `hosted_code_adapter.py`        |
| `app/`          | FastAPI server, WebSocket streaming      | `main.py`, `routers/`                             |
| `utils/`        | Configuration, tracing, storage          | `cfg/`, `infra/`, `storage/`                      |

### Five-Phase Execution Pipeline

Every task flows through a structured pipeline:

```
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐
│ANALYSIS │───►│ ROUTING │───►│ EXECUTION │───►│ PROGRESS │───►│ QUALITY │
│         │    │         │    │           │    │          │    │         │
│Complexity│    │Agent(s) │    │Delegated/ │    │Complete? │    │Score    │
│Skills    │    │Mode     │    │Sequential/│    │Refine?   │    │Missing  │
│Tools     │    │Subtasks │    │Parallel   │    │Continue? │    │Improve? │
└─────────┘    └─────────┘    └───────────┘    └──────────┘    └─────────┘
```

**Phase Details:**

1. **Analysis** (`AnalysisExecutor`): Extracts task complexity (simple/moderate/complex), required skills, and tool recommendations
2. **Routing** (`RoutingExecutor`): Selects agents, execution mode, creates subtasks, generates tool plan
3. **Execution** (`ExecutionExecutor`): Runs agents via strategies (delegated/sequential/parallel)
4. **Progress** (`ProgressExecutor`): Evaluates completion status, decides if refinement needed
5. **Quality** (`QualityExecutor`): Scores output 0-10, identifies gaps, suggests improvements

### Key Technologies and Dependencies

| Technology          | Role                                        | Version   |
| ------------------- | ------------------------------------------- | --------- |
| **DSPy**            | Prompt optimization, signatures, assertions | 2.6+      |
| **Agent Framework** | Workflow builder, executors, ChatAgent      | Microsoft |
| **FastAPI**         | HTTP/WebSocket API server                   | 0.115+    |
| **OpenAI**          | LLM backbone (GPT-4.1, GPT-4.1-mini)        | API       |
| **Tavily**          | Web search tool                             | API       |
| **OpenTelemetry**   | Distributed tracing                         | 1.x       |
| **Pydantic**        | Configuration and type validation           | 2.x       |
| **React/Vite**      | Web frontend                                | 18.x/5.x  |

### Entry Points and Usage Patterns

#### 1. Command-Line Interface (CLI)

```bash
# Run a task
agentic-fleet run -m "Research quantum computing advances" --verbose

# Start development server
agentic-fleet dev

# List available agents
agentic-fleet list-agents

# Run DSPy optimization
agentic-fleet optimize

# Evaluate against golden dataset
agentic-fleet eval
```

**Implementation**: `src/agentic_fleet/cli/console.py` (Typer-based)

#### 2. Python API

```python
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def main():
    # Create workflow with default settings
    workflow = await create_supervisor_workflow()

    # Run task (returns final result)
    result = await workflow.run("Analyze the impact of AI on healthcare")

    # Or stream events for real-time updates
    async for event in workflow.run_stream("Your task here"):
        if hasattr(event, 'agent_id'):
            print(f"[{event.agent_id}] {event.message.text}")

asyncio.run(main())
```

**Implementation**: `src/agentic_fleet/workflows/supervisor.py`

#### 3. Web Interface

```bash
# Start both backend (8000) and frontend (5173)
agentic-fleet dev

# Or separately
make backend     # FastAPI on :8000
make frontend    # React on :5173
```

**Backend API**: `/api/ws/chat` (WebSocket), `/api/chat` (REST)
**Frontend**: React + React Query + Zustand

### Configuration-Driven Architecture

AgenticFleet is configuration-driven, with all settings in `workflow_config.yaml`:

#### 1. workflow_config.yaml

```yaml
# DSPy settings
dspy:
  model: gpt-4.1-mini # Model for routing decisions
  require_compiled: false # Fail-fast if no compiled cache
  enable_routing_cache: true # Cache routing decisions
  routing_cache_ttl: 300 # Cache TTL in seconds

# Workflow settings
workflow:
  max_rounds: 15 # Max execution rounds
  enable_streaming: true # Real-time event streaming
  quality_threshold: 7.0 # Minimum quality score

# Agent definitions
agents:
  researcher:
    model: gpt-4.1
    temperature: 0.7
    tools: [TavilySearchTool]

  analyst:
    model: gpt-4.1
    temperature: 0.5
    tools: [HostedCodeInterpreterTool]
```

**Location**: `src/agentic_fleet/config/workflow_config.yaml`

#### 2. Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (recommended)
TAVILY_API_KEY=tvly-...

# Tracing (optional)
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317

# Security
ENABLE_SENSITIVE_DATA=false  # Redact prompts in traces
```

### Self-Improvement and Optimization

AgenticFleet learns from execution history:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Self-Improvement Loop                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Execute Tasks ──► 2. Record History ──► 3. GEPA Optimization   │
│         │                     │                      │              │
│         │              execution_history.jsonl       │              │
│         │                                            │              │
│         └──────────────────────────────────────◄─────┘              │
│                    Improved Routing Decisions                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**BridgeMiddleware** captures all routing decisions and outcomes. GEPA optimization uses successful patterns to improve DSPy module prompts.

### Directory Structure

```
src/agentic_fleet/
├── agents/                 # Agent definitions
│   ├── coordinator.py      # AgentFactory (creates agents from YAML)
│   └── prompts.py          # System prompts for each agent
│
├── workflows/              # Orchestration (5-phase pipeline)
│   ├── supervisor.py       # Main entry point, fast-path detection
│   ├── executors.py        # Phase executors (Analysis, Routing, etc.)
│   ├── strategies.py       # Execution modes (delegated/sequential/parallel)
│   ├── builder.py          # WorkflowBuilder configuration
│   └── context.py          # SupervisorContext definition
│
├── dspy_modules/           # DSPy integration
│   ├── reasoner.py         # DSPyReasoner (orchestrates all modules)
│   ├── signatures.py       # Core signatures (TaskAnalysis, TaskRouting)
│   ├── typed_models.py     # Pydantic output models
│   └── assertions.py       # DSPy assertions for validation
│
├── tools/                  # Tool adapters
│   ├── tavily_tool.py      # Web search
│   ├── hosted_code_adapter.py  # Code interpreter
│   └── browser_tool.py     # Browser automation
│
├── app/                    # FastAPI backend
│   ├── main.py             # Application entry
│   └── routers/            # API routes (chat, nlu, dspy)
│
├── config/                 # Configuration
│   └── workflow_config.yaml # Source of truth
│
├── utils/                  # Utilities (subpackages)
│   ├── cfg/                # Configuration loading
│   ├── infra/              # Tracing, resilience, logging
│   └── storage/            # History, Cosmos DB, persistence
│
└── cli/                    # Command-line interface
    ├── console.py          # Main Typer app
    └── commands/           # Individual commands
```

### Quick Start Example

```python
"""Complete example: Run a multi-step task with streaming."""
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def run_task():
    # Create workflow (loads config from workflow_config.yaml)
    workflow = await create_supervisor_workflow()

    # Define a complex task
    task = """
    Research the top 3 AI startups in healthcare,
    analyze their funding and market position,
    and write a brief investment summary.
    """

    # Stream execution events
    async for event in workflow.run_stream(task):
        event_type = type(event).__name__

        if hasattr(event, 'agent_id'):
            # Agent message event
            print(f"[{event.agent_id}] {event.message.text}")
        elif hasattr(event, 'data'):
            # Final output event
            print(f"\n=== Final Result ===")
            print(event.data.get('result', 'No result'))
            print(f"Quality: {event.data.get('quality', {}).get('score', 'N/A')}/10")

if __name__ == "__main__":
    asyncio.run(run_task())
```

---

## Five-Phase Execution Pipeline

The heart of AgenticFleet is its 5-phase execution pipeline, built on agent-framework primitives.

### Phase 1: Task Analysis

**Purpose**: Understand what the task requires before making routing decisions.

**Executor**: `AnalysisExecutor` (`workflows/executors.py`)

**DSPy Signature**: `TaskAnalysis`

```python
class TaskAnalysis(dspy.Signature):
    """Analyze task complexity and requirements."""

    task: str = dspy.InputField(desc="The user's task")
    team: str = dspy.InputField(desc="Available agents with their specializations")

    complexity: str = dspy.OutputField(desc="simple, moderate, or complex")
    required_skills: list[str] = dspy.OutputField(desc="Skills needed")
    recommended_tools: list[str] = dspy.OutputField(desc="Tools that would help")
    analysis_summary: str = dspy.OutputField(desc="Brief analysis")
```

**What Gets Analyzed**:

| Factor                | Values                              | Impact                           |
| --------------------- | ----------------------------------- | -------------------------------- |
| **Complexity**        | simple, moderate, complex           | Affects execution mode selection |
| **Required Skills**   | research, coding, writing, analysis | Determines agent candidates      |
| **Recommended Tools** | TavilySearchTool, CodeInterpreter   | Pre-filters tool-capable agents  |

**Example Output**:

```json
{
  "complexity": "moderate",
  "required_skills": ["research", "analysis", "writing"],
  "recommended_tools": ["TavilySearchTool"],
  "analysis_summary": "Multi-step task requiring web research and synthesis"
}
```

### Phase 2: Routing

**Purpose**: Select the optimal agents and execution mode for the task.

**Executor**: `RoutingExecutor` (`workflows/executors.py`)

**DSPy Signature**: `EnhancedTaskRouting` (with typed outputs)

```python
class TaskRoutingOutput(BaseModel):
    """Structured routing decision."""
    assigned_to: list[str] = Field(description="Agent names to assign")
    mode: Literal["delegated", "sequential", "parallel"] = Field(...)
    subtasks: list[str] = Field(description="Subtasks for each agent")
    reasoning: str = Field(description="Why this routing was chosen")
    tool_plan: list[str] = Field(description="Ordered tools to use")
    latency_budget: Literal["low", "medium", "high"] = Field(...)
```

**Routing Decision Matrix**:

| Task Type          | Agents                        | Mode       | Rationale                     |
| ------------------ | ----------------------------- | ---------- | ----------------------------- |
| Simple creative    | Writer                        | delegated  | Single agent sufficient       |
| Research + report  | Researcher → Writer           | sequential | Build on research output      |
| Multi-faceted      | Researcher ∥ Analyst          | parallel   | Independent subtasks          |
| Complex multi-step | Planner → [Agents] → Reviewer | sequential | Planning + execution + review |

**Routing Cache**: Decisions are cached (TTL 5 minutes) to reduce latency for similar tasks.

### Phase 3: Execution Modes

**Purpose**: Execute the routed task using the selected strategy.

**Executor**: `ExecutionExecutor` (`workflows/executors.py`)

**Strategies**: `workflows/strategies.py`

#### Delegated Mode

Single agent handles the entire task end-to-end.

```
Task ─────► Agent ─────► Result
```

**When Used**: Simple tasks, single-skill requirements
**Example**: "Write a haiku about coding"

```python
async def execute_delegated(agent, task, context):
    """Single agent execution."""
    chat_agent = create_agent(agent, context.tools)
    result = await chat_agent.run(task)
    return result
```

#### Sequential Mode

Agents work in order, each building on the previous output.

```
Task ─► Agent 1 ─► Output 1 ─► Agent 2 ─► Output 2 ─► Final
```

**When Used**: Multi-step pipelines, dependent tasks
**Example**: "Research AI trends, then write a summary"

```python
async def execute_sequential(agents, task, context):
    """Pipeline execution."""
    current_output = task
    for agent in agents:
        chat_agent = create_agent(agent, context.tools)
        current_output = await chat_agent.run(current_output)
    return current_output
```

#### Parallel Mode

Multiple agents work simultaneously, results are synthesized.

```
         ┌─► Agent 1 ─► Result 1 ─┐
Task ────┼─► Agent 2 ─► Result 2 ─┼─► Synthesize ─► Final
         └─► Agent 3 ─► Result 3 ─┘
```

**When Used**: Independent subtasks, time-sensitive
**Example**: "Research competitors AND analyze market trends"

```python
async def execute_parallel(agents, subtasks, context):
    """Concurrent execution."""
    tasks = [
        create_agent(agent, context.tools).run(subtask)
        for agent, subtask in zip(agents, subtasks)
    ]
    results = await asyncio.gather(*tasks)
    return synthesize_results(results)
```

### Phase 4: Progress Evaluation

**Purpose**: Determine if the task is complete or needs refinement.

**Executor**: `ProgressExecutor` (`workflows/executors.py`)

**DSPy Signature**: `ProgressEvaluation`

```python
class ProgressEvaluation(dspy.Signature):
    """Evaluate execution progress."""

    task: str = dspy.InputField()
    current_result: str = dspy.InputField()
    execution_history: str = dspy.InputField()

    status: Literal["complete", "needs_refinement", "continue"] = dspy.OutputField()
    reasoning: str = dspy.OutputField()
    next_steps: list[str] = dspy.OutputField()
```

**Decision Flow**:

```
                    ┌─────────────────┐
                    │ Evaluate Result │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │ Complete  │     │ Refinement│     │ Continue  │
    │           │     │   Needed  │     │ (more     │
    │ → Phase 5 │     │ → Re-route│     │  rounds)  │
    └───────────┘     └───────────┘     └───────────┘
```

### Phase 5: Quality Assessment

**Purpose**: Score the output and identify areas for improvement.

**Executor**: `QualityExecutor` (`workflows/executors.py`)

**DSPy Signature**: `QualityAssessment`

```python
class QualityAssessment(dspy.Signature):
    """Assess output quality."""

    task: str = dspy.InputField()
    output: str = dspy.InputField()

    score: float = dspy.OutputField(desc="Quality score 0-10")
    strengths: list[str] = dspy.OutputField()
    weaknesses: list[str] = dspy.OutputField()
    missing_elements: list[str] = dspy.OutputField()
    improvement_suggestions: list[str] = dspy.OutputField()
```

**Quality Score Interpretation**:

| Score | Meaning    | Action                   |
| ----- | ---------- | ------------------------ |
| 9-10  | Excellent  | Return as-is             |
| 7-8   | Good       | Return with minor notes  |
| 5-6   | Acceptable | May trigger refinement   |
| <5    | Poor       | Triggers refinement loop |

### Fast Path and Mode Selection

**Fast-Path Detection** (`supervisor.py:is_simple_task`):

Simple tasks bypass the full pipeline for <1 second responses:

```python
def is_simple_task(task: str) -> bool:
    """Detect tasks that don't need full orchestration."""
    simple_patterns = [
        r"^(hi|hello|hey|greetings)",  # Greetings
        r"^\d+\s*[\+\-\*\/]\s*\d+",      # Math
        r"^(what is|define|explain)\s+\w+$",  # Simple definitions
        r"^(yes|no|ok|thanks)",          # Acknowledgments
    ]
    return any(re.match(p, task.lower()) for p in simple_patterns)
```

**Mode Selection Logic**:

```python
def select_execution_mode(analysis, routing):
    """Select mode based on task characteristics."""

    # Single agent → delegated
    if len(routing.assigned_to) == 1:
        return "delegated"

    # Independent subtasks → parallel
    if routing.subtasks_independent:
        return "parallel"

    # Default → sequential
    return "sequential"
```

---

## Agent System

### Agent Architecture

Agents in AgenticFleet are built on agent-framework's `ChatAgent` class:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ChatAgent                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │     Name        │    │  Instructions   │    │     Tools       │ │
│  │  (identifier)   │    │  (system prompt)│    │  (capabilities) │ │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘ │
│           │                      │                      │           │
│           └──────────────────────┼──────────────────────┘           │
│                                  │                                  │
│                     ┌────────────▼────────────┐                     │
│                     │  OpenAIResponsesClient  │                     │
│                     │  (model, temperature,   │                     │
│                     │   reasoning_effort)     │                     │
│                     └─────────────────────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### AgentFactory and Creation

**Location**: `src/agentic_fleet/agents/coordinator.py`

The `AgentFactory` creates agents from YAML configuration:

```python
class AgentFactory:
    """Factory for creating agents from configuration."""

    def __init__(self, config: dict, tool_registry: ToolRegistry):
        self.config = config
        self.tool_registry = tool_registry

    def create_agent(self, name: str) -> ChatAgent:
        """Create a single agent by name."""
        agent_config = self.config["agents"][name]

        # Get tools
        tools = [
            self.tool_registry.get(tool_name)
            for tool_name in agent_config.get("tools", [])
        ]

        # Create chat client
        chat_client = OpenAIResponsesClient(
            model_id=agent_config.get("model", "gpt-4.1"),
            temperature=agent_config.get("temperature", 0.7),
            reasoning_effort=agent_config.get("reasoning_effort"),
        )

        # Get instructions from prompts
        instructions = prompts.get(name, prompts.default)

        return ChatAgent(
            name=name,
            chat_client=chat_client,
            instructions=instructions,
            tools=tools,
        )

    def create_all_agents(self) -> dict[str, ChatAgent]:
        """Create all configured agents."""
        return {
            name: self.create_agent(name)
            for name in self.config["agents"]
        }
```

### Specialized Agent Roles

AgenticFleet includes 9 specialized agents by default:

| Agent          | Specialization        | Default Tools    | System Prompt Focus             |
| -------------- | --------------------- | ---------------- | ------------------------------- |
| **Researcher** | Information gathering | TavilySearchTool | Find current info, cite sources |
| **Analyst**    | Data processing       | CodeInterpreter  | Calculations, visualizations    |
| **Writer**     | Content creation      | None             | Clear prose, structure          |
| **Reviewer**   | Quality assurance     | None             | Fact-check, critique            |
| **Coder**      | Code generation       | CodeInterpreter  | Clean code, best practices      |
| **Planner**    | Task decomposition    | None             | Break down complex tasks        |
| **Executor**   | General execution     | Various          | Follow instructions precisely   |
| **Verifier**   | Output validation     | None             | Check accuracy                  |
| **Generator**  | Creative content      | None             | Brainstorm, ideate              |

**Why Specialization Matters**:

```
Generic LLM:  "Research AND analyze AND write" ─► Mediocre at all

Specialized:  Researcher ─► Best at finding info
              Analyst   ─► Best at data analysis
              Writer    ─► Best at prose

Orchestrated: Researcher → Analyst → Writer ─► Excellent at all
```

### Tool System and Registry

**Location**: `src/agentic_fleet/utils/tool_registry.py`

The `ToolRegistry` manages tool metadata and availability:

```python
class ToolRegistry:
    """Registry for tool metadata and instances."""

    def __init__(self):
        self._tools: dict[str, ToolMetadata] = {}
        self._instances: dict[str, BaseTool] = {}

    def register(self, name: str, tool_class: type, metadata: ToolMetadata):
        """Register a tool with metadata."""
        self._tools[name] = metadata
        self._instances[name] = tool_class()

    def get(self, name: str) -> BaseTool:
        """Get tool instance by name."""
        return self._instances.get(name)

    def get_metadata(self, name: str) -> ToolMetadata:
        """Get tool metadata (for DSPy routing)."""
        return self._tools.get(name)

    def get_all_metadata(self) -> dict[str, ToolMetadata]:
        """Get all tool metadata for routing context."""
        return self._tools.copy()
```

**Tool Metadata Structure**:

```python
class ToolMetadata(BaseModel):
    """Metadata for tool-aware routing."""
    name: str
    description: str
    latency: Literal["low", "medium", "high"]
    capabilities: list[str]
    requires_api_key: bool = False
```

**Built-in Tools**:

| Tool                        | Latency | Capabilities                  |
| --------------------------- | ------- | ----------------------------- |
| `TavilySearchTool`          | medium  | web_search, current_events    |
| `HostedCodeInterpreterTool` | high    | code_execution, data_analysis |
| `BrowserTool`               | high    | web_browsing, scraping        |

### MCP Tools and Integration

AgenticFleet supports Model Context Protocol (MCP) tools:

```python
# Example: Tavily MCP Tool
from agentic_fleet.tools.tavily_mcp_tool import TavilyMCPTool

# MCP tools expose their schema via the protocol
mcp_tool = TavilyMCPTool()
schema = mcp_tool.get_schema()  # Returns MCP-compliant schema
```

### Handoff System

**Location**: `src/agentic_fleet/workflows/handoff.py`

Agents can hand off tasks to other agents during execution:

```
┌──────────┐     Handoff     ┌──────────┐
│ Agent A  │ ───────────────►│ Agent B  │
│          │   (with context)│          │
└──────────┘                 └──────────┘
```

**Handoff Decision Signature**:

```python
class HandoffDecision(dspy.Signature):
    """Decide whether to handoff to another agent."""

    current_agent: str = dspy.InputField()
    task: str = dspy.InputField()
    current_output: str = dspy.InputField()
    available_agents: str = dspy.InputField()

    should_handoff: bool = dspy.OutputField()
    target_agent: str = dspy.OutputField()
    handoff_context: str = dspy.OutputField()
```

---

## DSPy Integration and Intelligence

### DSPy Architecture and Modules

**Location**: `src/agentic_fleet/dspy_modules/`

DSPy provides the intelligence layer for all decision-making:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DSPyReasoner                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Signatures                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │  │TaskAnalysis  │  │TaskRouting   │  │Quality       │       │   │
│  │  │              │  │              │  │Assessment    │       │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐                         │   │
│  │  │Progress      │  │Enhanced      │                         │   │
│  │  │Evaluation    │  │TaskRouting   │                         │   │
│  │  └──────────────┘  └──────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Typed Models (Pydantic)                    │   │
│  │  TaskAnalysisOutput, TaskRoutingOutput, QualityOutput       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Assertions                                 │   │
│  │  validate_agent_exists, validate_tool_assignment,           │   │
│  │  validate_mode_agent_match                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Routing Cache                              │   │
│  │  TTL: 5 minutes | Key: hash(task + team)                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**DSPyReasoner Class**:

```python
class DSPyReasoner:
    """Orchestrates all DSPy modules for workflow intelligence."""

    def __init__(
        self,
        use_enhanced_signatures: bool = True,
        use_typed_signatures: bool = True,
        enable_routing_cache: bool = True,
        cache_ttl_seconds: int = 300,
    ):
        self.analysis_module = dspy.Predict(TaskAnalysis)
        self.routing_module = dspy.Predict(EnhancedTaskRouting)
        self.progress_module = dspy.Predict(ProgressEvaluation)
        self.quality_module = dspy.Predict(QualityAssessment)

        self._routing_cache = TTLCache(ttl=cache_ttl_seconds)

    def analyze_task(self, task: str, team: str) -> TaskAnalysisOutput:
        """Analyze task complexity and requirements."""
        result = self.analysis_module(task=task, team=team)
        return TaskAnalysisOutput.model_validate(result)

    def route_task(self, task: str, team: str, analysis: dict) -> TaskRoutingOutput:
        """Route task to agents (with caching)."""
        cache_key = self._get_cache_key(task, team)

        if cached := self._routing_cache.get(cache_key):
            return cached

        result = self.routing_module(
            task=task,
            team=team,
            analysis=analysis,
        )
        output = TaskRoutingOutput.model_validate(result)

        # Validate with assertions
        dspy.Assert(
            validate_agent_exists(output.assigned_to, team.split(",")),
            "Assigned agents must exist in team"
        )

        self._routing_cache.set(cache_key, output)
        return output
```

### Offline Compilation and Caching

**DSPy modules are compiled offline**, never at runtime in production:

```bash
# Compile DSPy modules (offline)
agentic-fleet optimize

# Or via script
uv run python src/agentic_fleet/scripts/optimize_reasoner.py
```

**Compilation Process**:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Training Data   │────►│ BootstrapFewShot│────►│ Compiled Module │
│ (examples.json) │     │   Optimizer     │     │  (.pkl cache)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Cache Location**: `.var/logs/compiled_supervisor.pkl`

**Configuration**:

```yaml
# workflow_config.yaml
dspy:
  require_compiled: true # Fail if no cache (production)
  cache_path: .var/logs/compiled_supervisor.pkl
```

### GEPA Optimization and Training

**GEPA** (Guided Evolutionary Prompt Algorithm) optimizes DSPy modules:

```python
# GEPA Configuration
gepa_config = {
    "max_metric_calls": 20,
    "max_bootstrapped_demos": 4,
    "population_size": 5,
    "generations": 3,
}

# Run optimization
from agentic_fleet.utils.gepa_optimizer import GEPAOptimizer

optimizer = GEPAOptimizer(config=gepa_config)
optimized_module = optimizer.optimize(
    module=reasoner.routing_module,
    trainset=load_training_examples(),
    metric=routing_accuracy_metric,
)
```

**GEPA Logs**: `.var/logs/gepa/`

### Self-Improvement Engine

**Location**: `src/agentic_fleet/utils/self_improvement.py`

The self-improvement engine learns from execution history:

```python
class SelfImprovementEngine:
    """Learns from execution history to improve routing."""

    def __init__(self, history_manager: HistoryManager):
        self.history = history_manager

    def extract_successful_patterns(self) -> list[TrainingExample]:
        """Extract high-quality routing decisions for training."""
        examples = []

        for entry in self.history.get_entries():
            if entry.quality_score >= 8.0:  # High quality
                examples.append(TrainingExample(
                    task=entry.task,
                    routing=entry.routing_decision,
                    outcome="success",
                ))

        return examples

    def update_training_data(self):
        """Update training examples from recent history."""
        new_examples = self.extract_successful_patterns()
        self.history.append_training_examples(new_examples)
```

### Training Data and Examples Format

**Location**: `src/agentic_fleet/data/`

**supervisor_examples.json**:

```json
[
  {
    "task": "Research the latest developments in quantum computing",
    "team": "Researcher,Analyst,Writer",
    "expected_routing": {
      "assigned_to": ["Researcher"],
      "mode": "delegated",
      "reasoning": "Simple research task requiring web search"
    },
    "quality": 9.0
  },
  {
    "task": "Analyze sales data and write a quarterly report",
    "team": "Researcher,Analyst,Writer",
    "expected_routing": {
      "assigned_to": ["Analyst", "Writer"],
      "mode": "sequential",
      "reasoning": "Data analysis followed by report writing"
    },
    "quality": 8.5
  }
]
```

### BridgeMiddleware and Feedback Loop

**Location**: `src/agentic_fleet/core/middleware.py`

BridgeMiddleware captures runtime decisions for offline learning:

```python
class BridgeMiddleware:
    """Captures execution data for self-improvement."""

    def __init__(self, history_manager: HistoryManager):
        self.history = history_manager

    async def __call__(self, context: SupervisorContext) -> SupervisorContext:
        """Wrap execution to capture decisions."""

        # Capture pre-execution state
        execution_record = ExecutionRecord(
            task=context.task,
            timestamp=datetime.utcnow(),
        )

        # Let execution proceed
        yield context

        # Capture post-execution state
        execution_record.routing_decision = context.routing
        execution_record.quality_score = context.quality.score
        execution_record.duration = context.duration

        # Persist for learning
        self.history.append(execution_record)
```

---

## User Interfaces

### Command-Line Interface (CLI)

**Location**: `src/agentic_fleet/cli/`

Built with Typer for a modern CLI experience:

```
agentic-fleet
├── run           # Run a task
├── dev           # Start development server
├── list-agents   # Show available agents
├── optimize      # Run GEPA optimization
├── eval          # Batch evaluation
├── history       # Export execution history
└── inspect       # Inspect workflow state
```

**Example Commands**:

```bash
# Run with verbose output
agentic-fleet run -m "Your task" --verbose

# Specify execution mode
agentic-fleet run -m "Your task" --mode sequential

# Start dev server on custom port
agentic-fleet dev --port 8080

# Export history as JSON
agentic-fleet history --format json --output history.json
```

### Python API

**Location**: `src/agentic_fleet/workflows/supervisor.py`

```python
from agentic_fleet.workflows import create_supervisor_workflow

# Create workflow
workflow = await create_supervisor_workflow(
    config_path="config/workflow_config.yaml",
    compile_dspy=False,  # Use cached modules
)

# Synchronous run
result = await workflow.run("Your task")

# Streaming run
async for event in workflow.run_stream("Your task"):
    handle_event(event)

# Access internals
context = workflow.context
reasoner = context.reasoner
agents = context.agents
```

### Web Frontend Architecture

**Location**: `src/frontend/`

```
src/frontend/
├── src/
│   ├── api/                # API layer
│   │   ├── hooks.ts        # React Query hooks
│   │   ├── websocket.ts    # WebSocket client
│   │   └── types.ts        # Type definitions
│   │
│   ├── stores/             # State management (Zustand)
│   │   └── chatStore.ts    # Chat state
│   │
│   ├── components/         # UI components
│   │   ├── layout/         # App layout
│   │   └── ui/             # shadcn/ui atoms
│   │
│   └── features/           # Feature modules
│       └── chat/           # Chat feature
│
├── vite.config.ts          # Vite configuration
└── package.json            # Dependencies
```

**Technology Stack**:

| Layer          | Technology                    |
| -------------- | ----------------------------- |
| Framework      | React 18                      |
| Build Tool     | Vite 5                        |
| State (Server) | React Query                   |
| State (Client) | Zustand                       |
| UI Components  | shadcn/ui                     |
| Styling        | Tailwind CSS                  |
| WebSocket      | Native + reconnecting wrapper |

### Chat UI and Message Components

**Chat Flow**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Chat Interface                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Message History                                             │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ User: Research AI trends                                │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ [Researcher] Searching for AI trends...                 │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ [Writer] Creating summary...                            │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ Assistant: [Final response with quality score]          │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Input: [Type your message...                    ] [Send]    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### State Management and API Client

**Zustand Store** (`stores/chatStore.ts`):

```typescript
interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentAgent: string | null;

  sendMessage: (content: string) => Promise<void>;
  cancelStream: () => void;
  clearMessages: () => void;
}

const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentAgent: null,

  sendMessage: async (content) => {
    set({ isStreaming: true });

    const ws = new ReconnectingWebSocket("/api/ws/chat");
    ws.send(JSON.stringify({ message: content }));

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleStreamEvent(data, set);
    };
  },
}));
```

**API Hooks** (`api/hooks.ts`):

```typescript
// Chat hook with WebSocket streaming
export function useChat() {
  const { messages, sendMessage, isStreaming } = useChatStore();

  return {
    messages,
    sendMessage,
    isStreaming,
  };
}

// Sessions hook with React Query
export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => api.get("/api/sessions"),
  });
}
```

---

## Observability and Monitoring

### Streaming Events and Message Types

**Location**: `src/agentic_fleet/workflows/streaming_events.py`

AgenticFleet emits structured events during execution:

| Event Type                  | Purpose           | Fields                      |
| --------------------------- | ----------------- | --------------------------- |
| `WorkflowStatusEvent`       | Phase transitions | phase, status, message      |
| `ExecutorCompletedEvent`    | Phase completion  | executor, result, duration  |
| `MagenticAgentMessageEvent` | Agent messages    | agent_id, message, role     |
| `ReasoningStreamEvent`      | DSPy reasoning    | step, reasoning, confidence |
| `WorkflowOutputEvent`       | Final output      | result, quality, routing    |

**Event Flow**:

```
Workflow Start
    │
    ├── WorkflowStatusEvent(phase="analysis")
    │       └── MagenticAgentMessageEvent(agent="fleet", "Analyzing task...")
    │
    ├── ExecutorCompletedEvent(executor="analysis")
    │
    ├── WorkflowStatusEvent(phase="routing")
    │       └── ReasoningStreamEvent(step="routing", reasoning="...")
    │
    ├── ExecutorCompletedEvent(executor="routing")
    │
    ├── WorkflowStatusEvent(phase="execution")
    │       ├── MagenticAgentMessageEvent(agent="Researcher", "Searching...")
    │       └── MagenticAgentMessageEvent(agent="Writer", "Writing...")
    │
    ├── ExecutorCompletedEvent(executor="execution")
    │
    ├── WorkflowStatusEvent(phase="quality")
    │
    └── WorkflowOutputEvent(result=..., quality=..., routing=...)
```

### OpenTelemetry Integration

**Location**: `src/agentic_fleet/utils/infra/tracing.py`

AgenticFleet supports OpenTelemetry for distributed tracing:

```python
# Enable tracing
export ENABLE_OTEL=true
export OTLP_ENDPOINT=http://localhost:4317

# Start Jaeger UI
make tracing-start  # Opens http://localhost:16686
```

**Trace Structure**:

```
workflow.run (root span)
├── analysis.execute
│   └── dspy.predict (TaskAnalysis)
├── routing.execute
│   └── dspy.predict (TaskRouting)
├── execution.execute
│   ├── agent.researcher.run
│   │   └── tool.tavily.search
│   └── agent.writer.run
├── progress.execute
│   └── dspy.predict (ProgressEvaluation)
└── quality.execute
    └── dspy.predict (QualityAssessment)
```

**Configuration**:

```yaml
# workflow_config.yaml
tracing:
  enabled: true
  service_name: agentic-fleet
  capture_sensitive: false # Redact prompts (default)
```

### Middleware System

**Location**: `src/agentic_fleet/core/middleware.py`

Middleware provides cross-cutting concerns:

```python
class ChatMiddleware:
    """Middleware for chat workflow operations."""

    async def before_execution(self, context: SupervisorContext):
        """Called before workflow execution."""
        # Start timing
        context.start_time = time.time()
        # Initialize tracing span
        context.span = tracer.start_span("workflow.run")

    async def after_execution(self, context: SupervisorContext):
        """Called after workflow execution."""
        # Record duration
        context.duration = time.time() - context.start_time
        # End tracing span
        context.span.end()
        # Log execution summary
        logger.info(f"Workflow completed in {context.duration:.2f}s")


class BridgeMiddleware:
    """Middleware for capturing execution history."""

    async def after_execution(self, context: SupervisorContext):
        """Capture execution for self-improvement."""
        record = ExecutionRecord(
            task=context.task,
            routing=context.routing,
            quality=context.quality,
            duration=context.duration,
        )
        self.history_manager.append(record)
```

**Middleware Stack**:

```
Request
    │
    ▼
┌─────────────────┐
│ ChatMiddleware  │ ──► Logging, Tracing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BridgeMiddleware│ ──► History Capture
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SupervisorWorkflow│ ──► Core Execution
└────────┬────────┘
         │
         ▼
Response
```

---

## Appendix

### Environment Variables Reference

| Variable                | Required | Default | Description               |
| ----------------------- | -------- | ------- | ------------------------- |
| `OPENAI_API_KEY`        | Yes      | -       | OpenAI API key            |
| `TAVILY_API_KEY`        | No       | -       | Tavily search API key     |
| `ENABLE_OTEL`           | No       | false   | Enable OpenTelemetry      |
| `OTLP_ENDPOINT`         | No       | -       | OTLP collector endpoint   |
| `ENABLE_SENSITIVE_DATA` | No       | false   | Capture prompts in traces |
| `LOG_JSON`              | No       | 1       | JSON structured logging   |
| `DSPY_COMPILE`          | No       | true    | Enable DSPy compilation   |

### File Locations Reference

| File                                              | Purpose                |
| ------------------------------------------------- | ---------------------- |
| `src/agentic_fleet/config/workflow_config.yaml`   | All runtime settings   |
| `.var/logs/execution_history.jsonl`               | Execution history      |
| `.var/logs/compiled_supervisor.pkl`               | DSPy compiled cache    |
| `.var/logs/gepa/`                                 | GEPA optimization logs |
| `src/agentic_fleet/data/supervisor_examples.json` | Training examples      |

### Common Commands Reference

| Task             | Command                                                      |
| ---------------- | ------------------------------------------------------------ |
| Install          | `make install`                                               |
| Run tests        | `make test`                                                  |
| Start dev        | `make dev`                                                   |
| Clear DSPy cache | `make clear-cache`                                           |
| Start tracing    | `make tracing-start`                                         |
| Run optimization | `agentic-fleet optimize`                                     |
| Analyze history  | `uv run python src/agentic_fleet/scripts/analyze_history.py` |
