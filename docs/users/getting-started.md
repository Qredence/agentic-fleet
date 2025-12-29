# Getting Started with AgenticFleet

This guide will get you from zero to running your first multi-agent task in about 5 minutes.

## Prerequisites

Before you begin, make sure you have:

| Requirement    | Version                | How to Check                                         |
| -------------- | ---------------------- | ---------------------------------------------------- |
| Python         | 3.12+                  | `python --version`                                   |
| Git            | Any recent version     | `git --version`                                      |
| OpenAI API Key | Required               | [Get one here](https://platform.openai.com/api-keys) |
| Tavily API Key | Optional (recommended) | [Free tier available](https://tavily.com)            |

> **Why Tavily?** It enables web search capabilities for the Researcher agent. Without it, research tasks won't have access to current information.

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet
```

### Step 2: Install Dependencies

We use `uv` for fast, reliable Python dependency management:

```bash
# Recommended: Use Make (handles everything)
make install
make frontend-install

# Or directly with uv
uv sync
```

<details>
<summary>📦 Don't have uv installed?</summary>

```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then restart your terminal and run
uv sync
```

</details>

<details>
<summary>📦 Prefer pip?</summary>

```bash
pip install -e .
```

Note: We recommend `uv` for faster installation and better dependency resolution.

</details>

### Step 3: Configure Your Environment

Create a `.env` file in the project root:

```bash
# Required - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-key-here

# Recommended - Get free key from https://tavily.com
TAVILY_API_KEY=tvly-your-tavily-key-here
```

> **Security Note**: Never commit your `.env` file. It's already in `.gitignore`.

### Step 4: Verify Installation

```bash
# Run the test suite to verify everything works
make test

# Or run a quick sanity check
uv run agentic-fleet list-agents
```

You should see output like:

```
Available Agents:
  • Researcher - Information gathering and web research
  • Analyst - Data analysis and computation
  • Writer - Content creation and report writing
  • Reviewer - Quality assurance and validation
  • Coder - Code generation and debugging
  • Planner - Task decomposition and orchestration
```

---

## Your First Task: Hello World

Let's run your first AgenticFleet task:

```bash
agentic-fleet run -m "Write a haiku about artificial intelligence"
```

### What You'll See

```
╔══════════════════════════════════════════════════════════════╗
║                      AgenticFleet v0.6.95                     ║
╚══════════════════════════════════════════════════════════════╝

📊 Analyzing task...
🔀 Routing to: Writer (delegated mode)
✍️  Writer is working...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Silicon dreams wake,
Patterns dance in neural paths,
Mind of our making.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Quality Score: 8.5/10
⏱️  Completed in 12.3 seconds
```

### What Just Happened?

Let's break down what AgenticFleet did:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ANALYSIS                                                      │
│    "Write a haiku" → Simple creative writing task               │
│    Complexity: Low | Skills needed: Writing                     │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ROUTING                                                       │
│    Best agent: Writer (specializes in content creation)         │
│    Mode: Delegated (single agent can handle this)               │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. EXECUTION                                                     │
│    Writer receives task → Generates haiku                       │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. QUALITY                                                       │
│    Evaluated: Structure ✓ | Theme ✓ | Creativity ✓              │
│    Score: 8.5/10                                                │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: AgenticFleet automatically figured out:

- This is a simple writing task
- The Writer agent is the best choice
- No other agents or tools needed
- One agent can handle it (delegated mode)

---

## Try More Examples

### Example 1: Research Task (Uses Web Search)

```bash
agentic-fleet run -m "What are the latest breakthroughs in fusion energy?"
```

**What happens**:

- Routes to **Researcher** agent (has web search)
- Uses Tavily to find current information
- Returns synthesized findings with sources

```
🔀 Routing to: Researcher (delegated mode)
🔍 Researcher is searching the web...
🌐 Found 5 relevant sources
```

### Example 2: Data Analysis (Uses Code Execution)

```bash
agentic-fleet run -m "Calculate the compound interest on $10,000 at 5% annual rate for 10 years"
```

**What happens**:

- Routes to **Analyst** agent (has code interpreter)
- Writes and executes Python code
- Returns calculated result

```
🔀 Routing to: Analyst (delegated mode)
💻 Analyst is running code...

Result: $16,288.95
Formula used: A = P(1 + r)^t
```

### Example 3: Multi-Step Task (Sequential Mode)

```bash
agentic-fleet run -m "Research the top 3 AI companies, analyze their market caps, and write a summary"
```

**What happens**:

- Routes to **Researcher → Analyst → Writer** (sequential)
- Each agent builds on the previous output

```
🔀 Routing: Sequential (Researcher → Analyst → Writer)

📚 Step 1/3: Researcher gathering information...
📊 Step 2/3: Analyst processing data...
✍️  Step 3/3: Writer creating summary...
```

### Example 4: Parallel Processing

```bash
agentic-fleet run -m "Research current gold prices AND calculate the growth rate over the past year"
```

**What happens**:

- Routes to **Researcher + Analyst** (parallel)
- Both work simultaneously
- Results combined at the end

```
🔀 Routing: Parallel (Researcher || Analyst)

🔄 Running 2 agents in parallel...
   └─ Researcher: Searching for gold prices...
   └─ Analyst: Calculating growth rate...

✅ Both complete - combining results...
```

---

## Using the Web Interface

For a richer experience, use the web interface:

```bash
# Start both backend and frontend
make dev
```

Then open http://localhost:5173 in your browser.

### Web Interface Features

| Feature                    | Description                          |
| -------------------------- | ------------------------------------ |
| **Chat Interface**         | Natural conversation with the system |
| **Real-time Streaming**    | Watch agents work in real-time       |
| **Workflow Visualization** | See which agents are active          |
| **Conversation History**   | Past conversations persist           |
| **Agent Activity**         | Monitor what each agent is doing     |

### Backend/Frontend Only

```bash
make backend        # Backend only (port 8000)
make frontend-dev   # Frontend only (port 5173)
```

---

## Using the Python API

For programmatic access, use the Python API:

```python
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def main():
    # Create the workflow
    workflow = await create_supervisor_workflow()

    # Run a task
    result = await workflow.run(
        "Analyze the impact of AI on software development"
    )

    # Access the results
    print(f"Answer: {result['result']}")
    print(f"Quality: {result['quality']['score']}/10")
    print(f"Agent used: {result['routing']['assigned_to']}")
    print(f"Mode: {result['routing']['mode']}")

asyncio.run(main())
```

### Streaming Results

For real-time updates:

```python
async def stream_example():
    workflow = await create_supervisor_workflow()

    async for event in workflow.run_stream("Your task here"):
        if hasattr(event, 'agent_id'):
            print(f"[{event.agent_id}] {event.message.text}")
        elif hasattr(event, 'data'):
            print(f"Final result: {event.data}")

asyncio.run(stream_example())
```

---

## Understanding the Output

Every AgenticFleet response includes:

### 1. The Result

The main output from the task.

### 2. Quality Score (0-10)

How well the output meets the task requirements:

- **9-10**: Excellent, comprehensive answer
- **7-8**: Good, covers main points
- **5-6**: Acceptable, may have gaps
- **Below 5**: May need refinement

### 3. Routing Information

- **Agent(s)**: Who worked on this
- **Mode**: How they collaborated
- **Tools used**: Web search, code execution, etc.

### 4. Timing

How long each phase took.

---

## Verbose Mode: See Everything

Add `--verbose` to see detailed decision-making:

```bash
agentic-fleet run -m "Research quantum computing advances" --verbose
```

This shows:

- DSPy analysis reasoning
- Routing decisions with explanations
- Tool calls and responses
- Quality evaluation details

---

## Common First-Run Issues

### Issue: "OPENAI_API_KEY not found"

```bash
# Make sure .env exists and has the key
cat .env | grep OPENAI

# If missing, add it
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

### Issue: "ModuleNotFoundError"

```bash
# Reinstall in editable mode
uv pip install -e .

# Or use uv sync
uv sync
```

### Issue: "uv: command not found"

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal, then
uv sync
```

### Issue: Research tasks return no results

Make sure you have `TAVILY_API_KEY` set:

```bash
echo "TAVILY_API_KEY=tvly-your-key" >> .env
```

Get a free key at [tavily.com](https://tavily.com).

---

## Post-Installation Tips

### Clear the Cache (After Updates)

```bash
# Clear DSPy compiled cache
make clear-cache

# Or manually
uv run python -m agentic_fleet.scripts.manage_cache --clear
```

### Check System Health

```bash
# Run the test suite
make test

# Check configuration
make test-config
```

### View Execution History

```bash
# Analyze past executions
make analyze-history
```

---

## Next Steps

You're now ready to use AgenticFleet! Here's your learning path:

### Beginner

1. ✅ You are here: **Getting Started**
2. → [Overview](overview.md) - Understand how it works
3. → [User Guide](user-guide.md) - Core concepts and features

### Intermediate

4. → [Configuration](configuration.md) - Customize behavior
5. → [Troubleshooting](troubleshooting.md) - Solve common issues

### Advanced

6. → [Architecture](../developers/architecture.md) - Technical deep-dive
7. → [DSPy Optimizer Guide](../guides/dspy-optimizer.md) - Improve routing

---

## Quick Reference

| Task              | Command                                                  |
| ----------------- | -------------------------------------------------------- |
| Run a task        | `agentic-fleet run -m "Your task"`                       |
| Start dev servers | `make dev`                                               |
| List agents       | `agentic-fleet list-agents`                              |
| Verbose output    | `agentic-fleet run -m "Task" --verbose`                  |
| Clear cache       | `make clear-cache`                                       |
| Run tests         | `make test`                                              |
| See history       | `uv run python -m agentic_fleet.scripts.analyze_history` |

---

## Getting Help

If you encounter issues:

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Run `make test` to verify setup
3. Check `.var/logs/workflow.log` for errors
4. Open a GitHub issue with error details

Welcome to AgenticFleet! 🚀
