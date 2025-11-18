# DSPy-Enhanced Agent Framework - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [Configuration](#configuration)
6. [Usage Patterns](#usage-patterns)
7. [Tool Integration](#tool-integration)
8. [Execution Modes](#execution-modes)
9. [Quality Assessment](#quality-assessment)
10. [Monitoring & History](#monitoring--history)
11. [Troubleshooting](#troubleshooting)

## Introduction

The DSPy-Enhanced Agent Framework combines Microsoft's agent-framework with DSPy's intelligent prompt optimization to create self-improving multi-agent workflows. The framework automatically analyzes tasks, routes them to appropriate agents, and learns from execution patterns to improve future routing decisions.

### Key Features

- **Intelligent Task Routing**: DSPy-powered automatic task decomposition and agent selection
- **Adaptive Workflows**: Self-improving workflows that learn from examples
- **Multi-Agent Orchestration**: Coordinate specialized agents efficiently
- **Real-time Monitoring**: Stream events for complete visibility
- **Comprehensive Logging**: Detailed 4-phase execution tracking with persistent history
- **Tool-Aware DSPy**: DSPy modules understand and leverage tool capabilities for better routing
- **Extensible Tools**: Code execution, web search, and custom tools

## Installation

### Prerequisites

- Python 3.10 or higher
- OpenAI API key
- Tavily API key (optional, for web search capabilities)

### Step-by-Step Installation

1. **Clone the repository**:

```bash
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet
```

2. **Create virtual environment**:

```bash
uv python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
uv sync
```

4. **Set up environment variables**:

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-key-here
TAVILY_API_KEY=tvly-your-key-here  # Optional but recommended
```

Get a free Tavily API key at [tavily.com](https://tavily.com) for high-quality web search with citations.

## Quick Start

### Using the CLI

The command-line interface for interacting with the framework:

```bash
# Basic usage
uv run agentic-fleet run -m "Your question here"

# With verbose logging (see all DSPy decisions)
uv run agentic-fleet run -m "Your question here" --verbose

# Save output to file
uv run agentic-fleet run -m "Your question here" --verbose 2>&1 | tee logs/output.log
```

## Workflow via CLI

### Running the Supervisor Workflow

Once the package is installed you can invoke the workflow directly with the
packaged CLI (no `uv run` wrapper required in production shells):

```bash
agentic-fleet run -m "Map Q4 risks for the AI compliance program"
```

Commonly used flags:

- `--verbose` – stream DSPy analysis, routing, tool calls, and judge feedback
- `--no-compile` – skip DSPy compilation for the current session (faster cold start)
- `--history <path>` – override where execution history is written

The same executable exposes supporting commands such as
`agentic-fleet list-agents` (inspect roster) and
`agentic-fleet evaluate --max-tasks 25` (batch evaluation), so teams can keep a
single mental model for both ad-hoc runs and continuous benchmarking.

### Features & Representative Use Cases

| Feature                        | What it delivers                                                                                                                  | Sample CLI prompts                                                                    |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Adaptive multi-agent routing   | DSPy supervisor selects the right mix of Researcher/Analyst/Writer/Reviewer plus execution mode (delegated, sequential, parallel) | `agentic-fleet run -m "Research EU AI Act updates and summarize the compliance gap"`  |
| Tool-aware orchestration       | Routing decisions consider tool requirements such as Tavily search or Hosted Code Interpreter                                     | `agentic-fleet run -m "Fetch current GPU spot prices and chart 12‑month trend"`       |
| Judge & refinement loop        | Automatic scoring (0–10), gap detection, and optional refinement when the score falls below thresholds                            | `agentic-fleet run -m "Draft an incident postmortem for outage #1452" --verbose`      |
| Streaming visibility           | Real-time event stream powers CLIs, TUIs, and the frontend dashboard                                                              | `agentic-fleet run -m "Live update: summarize today’s AI policy headlines" --verbose` |
| Persistent history & analytics | JSONL history + analyzer scripts make it easy to audit routing, timings, and quality                                              | `agentic-fleet run -m "Prepare talking points for next week’s roadmap review"`        |

These patterns cover the primary personas we see in production: research pods,
analyst desks, documentation teams, and evaluation/QA leads.

### Processing Flow

Each CLI invocation triggers the same four-phase pipeline described in
[Execution Phases](#execution-phases):

1. **Analysis** – DSPy inspects the prompt, required skills, and available tools.
2. **Routing** – The supervisor fixes the agent roster, selects delegated vs.
   sequential vs. parallel mode, and synthesizes subtasks/handoffs.
3. **Execution** – Microsoft agent-framework executors run the selected
   ChatAgents, stream tool calls, and capture artifacts.
4. **Quality & Judge** – DSPy scores the output, records missing elements, and
   optionally triggers refinement rounds until thresholds are met.

The CLI surfaces these phases through the `--verbose` stream and also records
timings/decisions in `logs/execution_history.jsonl` for later inspection via
`uv run python scripts/analyze_history.py`.

### Programmatic Usage

Integrate into your Python applications:

```python
from src.workflows import create_supervisor_workflow
import asyncio

async def main():
    # Create and initialize workflow
    workflow = await create_supervisor_workflow(compile_dspy=True)

    # Execute a task
    result = await workflow.run("Analyze the impact of AI on software development")

    # Access results
    print(f"Result: {result['result']}")
    print(f"Quality Score: {result['quality']['score']}/10")
    print(f"Routing: {result['routing']['mode']} to {result['routing']['assigned_to']}")

asyncio.run(main())
```

## Core Concepts

### Agents

The framework includes four specialized agents:

1. **Researcher**
   - Information gathering and web research
   - Has access to TavilySearchTool (if API key configured)
   - Best for: finding current information, gathering facts, web research

2. **Analyst**
   - Data analysis and computation
   - Has access to HostedCodeInterpreterTool (Python sandbox)
   - Best for: calculations, data processing, visualizations, code execution

3. **Writer**
   - Content creation and report writing
   - No special tools
   - Best for: creating documents, summarizing, formatting content

4. **Reviewer**
   - Quality assurance and validation
   - No special tools
   - Best for: checking accuracy, validating outputs, quality control

### DSPy Integration

DSPy (Declarative Self-improving Python) optimizes prompts automatically. The framework uses DSPy for:

1. **Task Analysis**: Understanding complexity, required capabilities, and steps
2. **Task Routing**: Selecting the best agents and execution mode
3. **Progress Evaluation**: Monitoring execution progress
4. **Quality Assessment**: Evaluating output quality and suggesting improvements

DSPy modules are compiled using BootstrapFewShot optimization with training examples, allowing the system to learn optimal routing patterns from historical data.

### Execution Phases

Every workflow execution follows 4 phases:

```
┌─────────────────────────────────────────────────────┐
│ Phase 1: DSPy Task Analysis                        │
│ - Analyze complexity, capabilities, tool needs      │
│ - Optionally use tools for context gathering        │
└─────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ Phase 2: DSPy Task Routing                         │
│ - Select agents based on analysis                  │
│ - Choose execution mode (parallel/sequential/      │
│   delegated)                                       │
│ - Prepare subtasks                                 │
└─────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ Phase 3: Agent Execution                           │
│ - Agents process tasks using their tools           │
│ - Results collected according to execution mode    │
└─────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ Phase 4: DSPy Quality Assessment                   │
│ - Evaluate output quality (0-10 scale)             │
│ - Identify missing elements                        │
│ - Suggest improvements                             │
│ - Optionally refine if score < threshold           │
└─────────────────────────────────────────────────────┘
```

## Configuration

### Configuration Files

The framework uses YAML-based configuration in `config/workflow_config.yaml`:

```yaml
# DSPy Configuration
dspy:
  model: gpt-5-mini # Model for DSPy supervisor
  temperature: 0.7
  max_tokens: 2000
  optimization:
    enabled: true # Enable DSPy compilation
    examples_path: data/supervisor_examples.json
    metric_threshold: 0.8
    max_bootstrapped_demos: 4 # Few-shot examples per prompt

# Workflow Configuration
workflow:
  supervisor:
    max_rounds: 15 # Max agent conversation turns
    max_stalls: 3 # Max stuck iterations
    max_resets: 2 # Max workflow resets
    enable_streaming: true # Stream events for live UI

  execution:
    parallel_threshold: 3 # Min agents for parallel execution
    timeout_seconds: 300
    retry_attempts: 2

# Agent Configuration
agents:
  researcher:
    model: gpt-4.1
    tools:
      - TavilySearchTool
    temperature: 0.5

  analyst:
    model: gpt-4.1
    tools:
      - HostedCodeInterpreterTool
    temperature: 0.3

  writer:
    model: gpt-4.1
    tools: []
    temperature: 0.7

  reviewer:
    model: gpt-4.1
    tools: []
    temperature: 0.2

# Tool Configuration
tools:
  enable_tool_aware_routing: true
  pre_analysis_tool_usage: true
  tool_registry_cache: true
  tool_usage_tracking: true

# Logging
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/workflow.log
  save_history: true
  history_file: logs/execution_history.jsonl
  verbose: true
```

### Configuration Options Explained

**DSPy Configuration**:

- `model`: Language model for DSPy routing decisions
- `temperature`: Randomness (0.0 = deterministic, 2.0 = creative)
- `optimization.enabled`: Enable/disable DSPy compilation
- `max_bootstrapped_demos`: Number of examples DSPy uses per prompt

**Workflow Configuration**:

- `max_rounds`: Prevents infinite agent loops
- `max_stalls`: Detects when agents aren't making progress
- `enable_streaming`: Enable streaming events (optional)

**Agent Configuration**:

- Per-agent `model`: Override default model for specific agents
- Per-agent `temperature`: Control creativity vs. consistency
- `tools`: List of tools available to each agent

**Tool Configuration**:

- `enable_tool_aware_routing`: DSPy considers tool availability when routing
- `pre_analysis_tool_usage`: Allow DSPy to use tools during task analysis
- `tool_usage_tracking`: Track which tools are used

### Environment Variables

Required:

- `OPENAI_API_KEY`: OpenAI API key for language models

Optional:

- `TAVILY_API_KEY`: Tavily API key for web search (highly recommended)
- `OPENAI_BASE_URL`: Custom OpenAI endpoint (for Azure, etc.)

## Usage Patterns

### Simple Task Execution

For straightforward tasks, the framework handles routing automatically:

```python
workflow = await create_supervisor_workflow()

# Simple writing task - automatically routed to Writer
result = await workflow.run("Write a product description for a smart watch")

# Research task - automatically routed to Researcher
result = await workflow.run("Find the latest developments in quantum computing")

# Analysis task - automatically routed to Analyst
result = await workflow.run("Calculate the average of [5, 10, 15, 20, 25]")
```

### Streaming Execution

For interactive applications and UIs:

```python
workflow = await create_supervisor_workflow()

async for event in workflow.run_stream("Your task here"):
    if hasattr(event, 'agent_id'):
        # Agent message event
        print(f"{event.agent_id}: {event.message.text}")
    elif hasattr(event, 'data'):
        # Final result event
        result = event.data
```

### Complex Multi-Step Tasks

The framework automatically decomposes complex tasks:

```python
# Automatically uses sequential mode: Researcher → Analyst → Writer
result = await workflow.run(
    "Research current AI trends, analyze adoption rates, and create a report"
)

# Automatically uses parallel mode: multiple agents work simultaneously
result = await workflow.run(
    "Analyze customer data AND research competitor pricing"
)
```

### Manual Configuration

You can override default configuration per execution:

```python
# Create workflow with custom config
config = WorkflowConfig(
    dspy_model="gpt-4.1",
    refinement_threshold=9.0,  # Stricter quality threshold
    enable_refinement=True,
    max_rounds=20,
)

workflow = SupervisorWorkflow(config=config)
await workflow.initialize()

result = await workflow.run("Your task")
```

## Tool Integration

### Available Tools

**TavilySearchTool** (Web Search):

- Real-time web search with citations
- Requires `TAVILY_API_KEY`
- Available to Researcher agent
- Best for: current events, factual information, research

**HostedCodeInterpreterTool** (Code Execution):

- Python code execution in secure sandbox
- Available to Analyst agent
- Best for: calculations, data processing, visualizations

### Tool-Aware Routing

DSPy automatically considers tool availability when routing tasks. The framework includes a centralized **ToolRegistry** that tracks all tools, their capabilities, and which agents can use them.

**How It Works**:

1. During initialization, tools are registered from each agent's configuration
2. Tool metadata (name, description, capabilities, use cases, aliases) is extracted
3. DSPy signatures receive formatted tool descriptions as input
4. The supervisor's instructions include a live tool catalog for context
5. Routing decisions explicitly list `tool_requirements`

**Example Tool-Aware Routing**:

```python
# Task requiring web search → automatically routed to Researcher (has TavilySearchTool)
await workflow.run("What are the latest AI breakthroughs this week?")
# DSPy sees: web_search capability needed, Researcher has TavilySearchTool

# Task requiring computation → automatically routed to Analyst (has CodeInterpreter)
await workflow.run("Calculate compound interest for $10,000 at 5% over 10 years")
# DSPy sees: code_execution capability needed, Analyst has HostedCodeInterpreterTool

# Task requiring both → sequential routing: Researcher then Analyst
await workflow.run("Find current Bitcoin price and calculate profit from $1000 investment")
# DSPy sees: web_search + code_execution needed, routes sequentially
```

**Tool Capability Inference**:
The registry automatically infers capabilities from tool names and descriptions:

- Tools with "search" in name/description → `web_search` capability
- Tools with "code" or "interpreter" → `code_execution` capability
- Tavily tools → `web_search`, `real_time`, `citations` capabilities

**Accessing Tool Information**:

```python
# View registered tools
print(workflow.tool_registry.get_tool_descriptions())

# Get tools by capability
search_tools = workflow.tool_registry.get_tools_by_capability("web_search")

# Get agent's tools
researcher_tools = workflow.tool_registry.get_agent_tools("Researcher")

# Check tool availability
if workflow.tool_registry.can_execute_tool("tavily_search"):
    result = await workflow.tool_registry.execute_tool(
        "tavily_search", query="Latest AI news"
    )
```

### Adding Custom Tools

To add a new tool:

1. **Implement the ToolProtocol**:

```python
# src/tools/my_tool.py
from agent_framework import ToolProtocol

class MyCustomTool(ToolProtocol):
    """Custom tool description."""

    @property
    def name(self) -> str:
        return "MyCustomTool"

    @property
    def description(self) -> str:
        return "Description of what the tool does"

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "my_tool",
                "description": "Tool description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }

    async def run(self, query: str) -> str:
        # Implement tool logic
        return f"Result for: {query}"
```

2. **Register with an agent**:

```python
# In supervisor_workflow.py _create_agents()
agents["MyAgent"] = self._create_agent(
    name="MyAgent",
    description="Custom agent with special tool",
    instructions="Use the custom tool to process requests",
    tools=MyCustomTool(),
)
```

3. **Add training examples**:

Add examples to `data/supervisor_examples.json` that show when to use the new tool.

## Execution Modes

### Delegated Mode

Single agent handles the entire task end-to-end.

**When to use**:

- Task fits one agent's expertise
- No need for collaboration
- Fastest execution

**Example**:

```python
# "Write a blog post" → Writer (delegated)
result = await workflow.run("Write a blog post about productivity tips")
```

### Sequential Mode

Task flows through agents in order, output of one becomes input of next.

**When to use**:

- Task requires multiple steps
- Each step builds on previous
- Order matters

**Example**:

```python
# "Research → Analyze → Write" pipeline
result = await workflow.run(
    "Research AI impact on healthcare, analyze the data, create a report"
)
# Execution: Researcher (gather data) → Analyst (process) → Writer (report)
```

### Parallel Mode

Multiple agents work simultaneously on subtasks, results synthesized.

**When to use**:

- Independent subtasks
- Faster execution needed
- No dependencies between tasks

**Example**:

```python
# Research AND analysis happen simultaneously
result = await workflow.run(
    "Research competitor pricing AND analyze our sales data"
)
# Execution: Researcher (pricing) || Analyst (sales data) → synthesis
```

## Quality Assessment

### Quality Scoring

Every execution receives a quality score (0-10) based on:

- Completeness (does it answer the question?)
- Accuracy (is it correct?)
- Relevance (does it address the task?)
- Clarity (is it well-presented?)

### Automatic Refinement

If quality score < threshold (default 8.0), the system automatically refines:

```python
config = WorkflowConfig(
    refinement_threshold=8.0,   # Refine if score < 8
    enable_refinement=True,      # Enable auto-refinement
)

workflow = SupervisorWorkflow(config=config)
await workflow.initialize()

result = await workflow.run("Your task")
# If initial quality < 8.0, Writer agent will refine the output
```

### Accessing Quality Metrics

```python
result = await workflow.run("Your task")

quality = result['quality']
print(f"Score: {quality['score']}/10")
print(f"Missing: {quality['missing']}")
print(f"Improvements: {quality['improvements']}")
```

## Monitoring & History

### Execution History

All executions are automatically saved to `logs/execution_history.jsonl` (preferred) or `logs/execution_history.json` (legacy).

**JSONL Format** (default):

- Append-only for performance (10-100x faster than JSON)
- One execution per line
- Efficient for large histories

**JSON Format** (legacy):

- Full array of executions
- More readable but slower for large files
- Still supported for backwards compatibility

### Analyzing History

Use the built-in analyzer:

```bash
# Show overall summary and last 10 executions
uv run python scripts/analyze_history.py

# Show all statistics
uv run python scripts/analyze_history.py --all

# Show specific information
uv run python scripts/analyze_history.py --routing    # Routing mode distribution
uv run python scripts/analyze_history.py --agents     # Agent usage stats
uv run python scripts/analyze_history.py --timing     # Time breakdown by phase
```

### Programmatic History Access

```python
from src.utils.history_manager import HistoryManager

manager = HistoryManager(history_format="jsonl")

# Load recent executions
recent = manager.load_history(limit=10)

# Get statistics
stats = manager.get_history_stats()
print(f"Total executions: {stats['total_executions']}")
print(f"Average quality: {stats['average_quality_score']}/10")

# Rotate history (keep last N entries)
manager.clear_history(keep_recent=100)
```

### Verbose Logging

Enable verbose logging to see DSPy decisions:

```bash
uv run agentic-fleet run -m "Your task" --verbose
```

Verbose output includes:

- DSPy prompts and reasoning
- Tool availability and usage
- Routing decisions with explanations
- Quality assessment details

## Console Output Formatting

By default the CLI prints a concise **Final Answer** block that contains the
user-facing response, the overall quality score, and the agents that
contributed. When you add `--verbose`, the stream is reorganized into clearly
separated sections so operators can reason about the run without losing the
clean answer:

1. **Final Answer** – Markdown-formatted response and key metrics (always shown).
2. **Reasoning & Plan** – DSPy analysis, proposed steps, and routing rationale.
3. **Execution Log** – Timestamped agent/tool events, iterations, and handoffs.
4. **Assertions & Checks** – Judge/referee evaluations, missing items, and
   refinement outcomes.

The structured layout keeps executive-ready answers readable in the default
mode while still exposing deep traces for operators and developers via
`--verbose`. Teams that ingest the CLI output into observability tooling often
pipe the verbose stream through `tee` or redirect just the Final Answer block
to downstream systems, knowing that the reasoning/steps/assertions are already
formatted for inspection.

## Troubleshooting

### Common Issues

**1. "OPENAI_API_KEY not found"**

```bash
# Solution: Set in .env file
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

**2. "TAVILY_API_KEY not set - Researcher will operate without web search"**

```bash
# Solution: Get free API key from tavily.com
echo "TAVILY_API_KEY=tvly-your-key" >> .env
```

**3. "ModuleNotFoundError: No module named 'src'"**

```bash
# Solution: Install in editable mode
pip install -e .
```

**4. "Cache is stale / compilation fails"**

```bash
# Solution: Clear cache
python -c "from src.utils.compiler import clear_cache; clear_cache()"
```

**5. Tests failing with import errors**

```bash
# Solution: Set PYTHONPATH
PYTHONPATH=. pytest -q tests/
```

### Performance Tuning

**Faster Startup**:

```bash
# Skip DSPy compilation
uv run agentic-fleet run -m "Task" --no-compile
```

**Better Routing Accuracy**:

- Add more training examples to `data/supervisor_examples.json`
- Increase `max_bootstrapped_demos` in config
- Use `gpt-4.1` instead of `gpt-5-mini` for DSPy

**Lower Costs**:

- Use `gpt-5-mini` for most agents
- Reduce `temperature` for less randomness (fewer tokens)
- Disable `pre_analysis_tool_usage` if not needed

### Debug Mode

Enable maximum verbosity:

```python
import logging
from src.utils.logger import setup_logger

setup_logger("dspy_agent_framework", "DEBUG")

workflow = await create_supervisor_workflow(compile_dspy=True)
result = await workflow.run("Your task")
```

Check logs at:

- Console output (real-time)
- `logs/workflow.log` (persistent file log)
- `logs/execution_history.jsonl` (structured execution data)

## Advanced Features

### History Management

Programmatic history control:

```python
from src.utils.history_manager import HistoryManager

manager = HistoryManager(
    history_format="jsonl",
    max_entries=1000  # Auto-rotate after 1000 entries
)

# Save execution
manager.save_execution(execution_data)

# Load specific range
recent = manager.load_history(limit=50)

# Clear old history
manager.clear_history(keep_recent=100)

# Get statistics
stats = manager.get_history_stats()
```

### Cache Management

Control DSPy compilation cache:

```python
from src.utils.compiler import clear_cache, get_cache_info

# View cache info
info = get_cache_info()
print(f"Cache created: {info['created_at']}")
print(f"Cache size: {info['cache_size_bytes']} bytes")

# Clear cache (force recompilation)
clear_cache()
```

### Custom Exceptions

Handle workflow errors gracefully:

```python
from src.workflows.exceptions import (
    WorkflowError,
    AgentExecutionError,
    RoutingError,
    ConfigurationError,
    HistoryError,
)

try:
    result = await workflow.run("Your task")
except AgentExecutionError as e:
    print(f"Agent {e.agent_name} failed on task: {e.task}")
    print(f"Original error: {e.original_error}")
except RoutingError as e:
    print(f"Routing failed: {e}")
    print(f"Routing decision: {e.routing_decision}")
except HistoryError as e:
    print(f"History save failed: {e}")
```

### Configuration Validation

Use Pydantic schemas for validation:

```python
from src.utils.config_schema import validate_config, WorkflowConfigSchema

# Validate configuration
try:
    schema = validate_config(config_dict)
    print("Configuration is valid")
except ConfigurationError as e:
    print(f"Invalid configuration: {e}")
```

## Best Practices

1. **Always set TAVILY_API_KEY** for research tasks
2. **Use JSONL format** for execution history (much faster)
3. **Enable DSPy compilation** for better routing (first run is slower, subsequent runs are cached)
4. **Monitor quality scores** and refine if consistently low
5. **Add training examples** for domain-specific routing patterns
6. **Use appropriate temperatures**: low (0.2-0.3) for factual tasks, high (0.7-0.9) for creative tasks
7. **Enable verbose logging** when debugging routing decisions

## Next Steps

- Read [Architecture](../developers/architecture.md) for technical architecture
- Read [Contributing](../developers/contributing.md) for development guidelines
- Explore `examples/` directory for sample code
- Check `config/workflow_config.yaml` for all configuration options

## GEPA Optimization

Reflective prompt evolution is available via the built-in GEPA command:

```bash
uv run python console.py gepa-optimize \
  --auto medium \
  --max-full-evals 60 \
  --use-history
```

- Enable GEPA globally by setting `dspy.optimization.use_gepa: true` in `config/workflow_config.yaml`.
- Customize search intensity with `--auto` (`light`, `medium`, `heavy`) or the matching config key.
- Add `--use-history` to merge high-quality records from `logs/execution_history.*` into the training split. Tune `--history-min-quality` and `--history-limit` as needed.
- Results are cached at `logs/compiled_supervisor.pkl`. Delete the cache or pass `--no-cache` to force a fresh optimization run.

Under the hood, the command configures `dspy.GEPA` with the routing feedback metric defined in `src/utils/gepa_optimizer.py`, ensuring actionable text feedback for each trajectory.
