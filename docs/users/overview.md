# Understanding AgenticFleet

Welcome to AgenticFleet! This guide will help you understand what AgenticFleet is, why it exists, and how it works under the hood.

## The Problem: Why Single LLM Calls Aren't Enough

Imagine you ask an AI assistant: _"Research the latest AI regulations in Europe, analyze their impact on tech startups, and write a comprehensive report with recommendations."_

A single LLM call struggles with this because:

- **Knowledge cutoff**: The model may not have current information
- **No tool access**: It can't search the web or run calculations
- **Context limits**: Complex tasks overflow context windows
- **No verification**: No way to check accuracy or completeness
- **One-shot answers**: No iteration or refinement

You could try to work around this by:

1. Breaking the task into multiple prompts manually
2. Copy-pasting outputs between prompts
3. Manually deciding what to do next

But this is tedious, error-prone, and doesn't scale.

**What if the AI could do this automatically?**

---

## The Solution: AgenticFleet

AgenticFleet is a **multi-agent orchestration system** that automatically:

1. **Analyzes** your task to understand what's needed
2. **Routes** it to specialized AI agents with the right tools
3. **Executes** the work (in parallel, sequence, or delegation)
4. **Evaluates** progress and quality
5. **Returns** a polished, verified result

Think of it like a **smart team lead** who:

- Receives your request
- Figures out who should work on it
- Coordinates the team
- Reviews the output before delivering it

### What Makes AgenticFleet Different?

AgenticFleet combines two powerful technologies:

| Technology                    | What It Does                                                    |
| ----------------------------- | --------------------------------------------------------------- |
| **DSPy**                      | Intelligent routing and decision-making that improves over time |
| **Microsoft Agent Framework** | Reliable agent execution with tools and orchestration           |

This combination gives you:

- ✅ **Smart routing** – Tasks go to the right agents automatically
- ✅ **Tool integration** – Web search, code execution, and more
- ✅ **Quality assurance** – Built-in scoring and refinement
- ✅ **Self-improvement** – Learns from execution history
- ✅ **Full observability** – Traces, logs, and history for debugging

---

## How AgenticFleet Works

### The 5-Phase Pipeline

Every task flows through a **5-phase pipeline**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR TASK ENTERS HERE                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: ANALYSIS                                                      │
│  ─────────────────                                                      │
│  • What is this task asking for?                                        │
│  • How complex is it? (simple/moderate/complex)                         │
│  • What capabilities are needed? (research, coding, writing...)         │
│  • What tools might help? (web search, code execution...)               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: ROUTING                                                       │
│  ────────────────                                                       │
│  • Which agents should handle this?                                     │
│  • What execution mode? (delegated/sequential/parallel)                 │
│  • How should subtasks be structured?                                   │
│  • What's the expected approach?                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: EXECUTION                                                     │
│  ──────────────────                                                     │
│  • Agents receive their assignments                                     │
│  • Tools are invoked as needed (search, compute, etc.)                  │
│  • Results are collected and combined                                   │
│  • Progress events stream in real-time                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: PROGRESS                                                      │
│  ────────────────                                                       │
│  • Is the task complete?                                                │
│  • Does it need another iteration?                                      │
│  • Are there missing pieces?                                            │
│  • Should we continue or finalize?                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: QUALITY                                                       │
│  ───────────────                                                        │
│  • Score the output (0-10 scale)                                        │
│  • Identify missing elements                                            │
│  • Suggest improvements                                                 │
│  • Optionally trigger refinement                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FINAL RESULT DELIVERED                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Simple Tasks Get a Fast Path

Not every task needs the full pipeline. AgenticFleet detects simple queries like:

- "Hello!"
- "What is 2 + 2?"
- "Define machine learning"

These bypass the pipeline for **instant responses** (under 1 second).

---

## Core Concepts

### Agents: Your Specialized Team

AgenticFleet includes **9 specialized agents**, each with specific expertise:

| Agent          | Expertise             | Tools               | Best For                             |
| -------------- | --------------------- | ------------------- | ------------------------------------ |
| **Researcher** | Information gathering | Web search (Tavily) | Finding current info, fact-checking  |
| **Analyst**    | Data processing       | Code interpreter    | Calculations, data analysis, charts  |
| **Writer**     | Content creation      | None                | Reports, summaries, documentation    |
| **Reviewer**   | Quality assurance     | None                | Fact-checking, validation, critique  |
| **Coder**      | Code generation       | Code interpreter    | Writing code, debugging, refactoring |
| **Planner**    | Task decomposition    | None                | Breaking down complex tasks          |
| **Executor**   | Task execution        | Various             | Running specific actions             |
| **Verifier**   | Output validation     | None                | Checking correctness                 |
| **Generator**  | Creative content      | None                | Brainstorming, ideation              |

**Why specialized agents?**

Just like a real team, specialists are better than generalists for specific tasks:

- A **Researcher** with web search tools finds current information faster
- An **Analyst** with code execution can actually run calculations
- A **Writer** focused on prose produces better content

### Tools: Agent Superpowers

Agents can use **tools** to extend their capabilities:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TOOL REGISTRY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TavilySearchTool          HostedCodeInterpreterTool           │
│  ─────────────────         ─────────────────────────           │
│  • Real-time web search    • Python code execution             │
│  • With citations          • Data processing                   │
│  • Current events          • Visualizations                    │
│  • Fact verification       • Calculations                      │
│                                                                 │
│  Used by: Researcher       Used by: Analyst, Coder             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Tool-aware routing**: DSPy automatically considers which tools are needed when assigning tasks. If your task requires web search, it routes to an agent with `TavilySearchTool`.

### Execution Modes: How Work Gets Done

AgenticFleet supports **6 execution modes**:

#### 1. Auto Mode (Default)

Let DSPy decide the best approach based on task analysis.

#### 2. Delegated Mode

**One agent handles everything.**

```
Task ──► Single Agent ──► Result
```

Best for: Simple, focused tasks that fit one agent's expertise.

**Example**: "Write a haiku about coding" → Writer agent handles it alone.

#### 3. Sequential Mode

**Agents work in order, passing results forward.**

```
Task ──► Agent 1 ──► Agent 2 ──► Agent 3 ──► Result
```

Best for: Multi-step tasks where each step builds on the previous.

**Example**: "Research AI trends, analyze the data, write a report"

- Researcher gathers information
- Analyst processes the data
- Writer creates the report

#### 4. Parallel Mode

**Agents work simultaneously, results are combined.**

```
         ┌──► Agent 1 ──┐
Task ────┼──► Agent 2 ──┼──► Combine ──► Result
         └──► Agent 3 ──┘
```

Best for: Independent subtasks that can run concurrently.

**Example**: "Analyze our sales data AND research competitor pricing"

- Analyst processes sales data (simultaneously)
- Researcher finds competitor info (simultaneously)
- Results combined at the end

#### 5. Handoff Mode

**Agents pass control directly to each other.**

```
Task ──► Triage ──► Specialist A ──► Specialist B ──► Result
```

Best for: Linear tasks where speed is priority.

#### 6. Discussion Mode

**Agents collaborate in a group chat.**

Best for: Complex problems requiring multiple perspectives.

### DSPy Intelligence: The Brain Behind Routing

**DSPy** (Declarative Self-improving Python) is what makes AgenticFleet smart. It:

1. **Analyzes tasks** using structured reasoning
2. **Makes routing decisions** based on learned patterns
3. **Evaluates quality** of outputs
4. **Improves over time** from execution history

```
┌─────────────────────────────────────────────────────────────────┐
│                      DSPy REASONER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Signatures (What to decide)                                    │
│  ──────────────────────────                                     │
│  • TaskAnalysis: Understand complexity and requirements         │
│  • TaskRouting: Choose agents and execution mode                │
│  • ProgressEvaluation: Is the task complete?                    │
│  • QualityAssessment: Score and critique output                 │
│                                                                 │
│  Optimization (How it improves)                                 │
│  ────────────────────────────                                   │
│  • Learns from training examples                                │
│  • Caches successful routing patterns                           │
│  • Uses typed Pydantic models for reliability                   │
│  • Validates decisions with assertions                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Real-World Use Cases

### Use Case 1: Research Assistant

**Task**: "What are the latest developments in quantum computing this month?"

**What happens**:

1. **Analysis**: Detects need for current information → requires web search
2. **Routing**: Assigns to Researcher (has TavilySearchTool) in delegated mode
3. **Execution**: Researcher searches web, gathers sources, synthesizes findings
4. **Quality**: Scores output, checks for completeness and citations

**Result**: A well-sourced summary with citations to recent articles.

### Use Case 2: Data Analysis Pipeline

**Task**: "Calculate the average customer lifetime value from this data and visualize the trend."

**What happens**:

1. **Analysis**: Detects need for computation and visualization → requires code
2. **Routing**: Assigns to Analyst (has HostedCodeInterpreterTool)
3. **Execution**: Analyst writes Python code, runs calculations, generates chart
4. **Quality**: Verifies calculations, checks visualization quality

**Result**: Numerical analysis with a generated chart.

### Use Case 3: Multi-Step Report

**Task**: "Research EU AI regulations, analyze their impact on startups, and write a strategic brief."

**What happens**:

1. **Analysis**: Complex multi-step task requiring research + analysis + writing
2. **Routing**: Sequential mode: Researcher → Analyst → Writer
3. **Execution**:
   - Researcher finds current regulation info
   - Analyst processes implications
   - Writer synthesizes into brief
4. **Quality**: Comprehensive review for completeness

**Result**: A polished strategic brief with research backing.

### Use Case 4: Parallel Information Gathering

**Task**: "Get current Bitcoin price AND analyze historical volatility."

**What happens**:

1. **Analysis**: Two independent subtasks
2. **Routing**: Parallel mode: Researcher + Analyst
3. **Execution**: Both work simultaneously
4. **Quality**: Combined results reviewed

**Result**: Faster completion than sequential execution.

---

## What You Get Out of the Box

### Command-Line Interface

```bash
agentic-fleet run -m "Your task here"     # Run a task
make dev                                   # Start dev servers
agentic-fleet list-agents                  # See available agents
```

### Web Interface

```bash
make dev
# Opens at http://localhost:5173
```

Features:

- Real-time streaming responses
- Workflow visualization
- Conversation history
- Agent activity display

### Configuration

All settings in one place: `src/agentic_fleet/config/workflow_config.yaml`

```yaml
dspy:
  model: gpt-5.2 # Primary DSPy model
  routing_model: gpt-5-mini # Fast model for routing decisions
  enable_routing_cache: true # Cache routing for speed

workflow:
  supervisor:
    max_rounds: 15 # Prevent infinite loops
    enable_streaming: true # Real-time updates

agents:
  researcher:
    model: gpt-4.1-mini # Per-agent model override
    tools: [TavilySearchTool]
```

### Observability

Everything is logged and traceable:

```
.var/
├── logs/
│   ├── execution_history.jsonl  # All executions
│   ├── workflow.log             # Runtime logs
│   └── gepa/                    # Optimization logs
└── cache/
    └── dspy/                    # Compiled modules
```

---

## Key Takeaways

1. **AgenticFleet automates multi-agent coordination** – No more manual prompt chaining
2. **5-phase pipeline ensures quality** – Analysis → Routing → Execution → Progress → Quality
3. **Specialized agents with tools** – Right expert for each job
4. **Multiple execution modes** – Delegated, sequential, parallel, and more
5. **DSPy makes it smart** – Learns and improves from history
6. **Full observability** – Logs, traces, and history for debugging

---

## Next Steps

Now that you understand how AgenticFleet works:

1. **[Getting Started](getting-started.md)** – Install and run your first task
2. **[User Guide](user-guide.md)** – Deep dive into features
3. **[Configuration](configuration.md)** – Customize behavior
4. **[Troubleshooting](troubleshooting.md)** – Common issues and solutions

---

## Frequently Asked Questions

### How is this different from just using ChatGPT?

ChatGPT is a single model responding to prompts. AgenticFleet:

- Uses multiple specialized agents
- Has tools (web search, code execution)
- Automatically routes tasks to the right expert
- Evaluates and refines output quality
- Learns from execution history

### Do I need multiple API keys?

Only **OpenAI API key** is required. Tavily API key is optional but recommended for web search capabilities.

### How fast is it?

- **Simple tasks**: Under 1 second (fast path)
- **Standard tasks**: 30-60 seconds
- **Complex multi-step tasks**: 2-5 minutes

### Can I add custom agents?

Yes! Add agent configuration to `workflow_config.yaml` and prompts to `agents/prompts.py`. See the [User Guide](user-guide.md#adding-custom-tools) for details.

### Does it work offline?

No, it requires API access to language models (OpenAI). However, DSPy modules are compiled once and cached locally for faster subsequent runs.
