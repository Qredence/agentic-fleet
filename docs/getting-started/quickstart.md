# Quick Start Guide

Get up and running with AgenticFleet in 5 minutes! This guide walks you through your first multi-agent workflow.

---

## Prerequisites

Before starting, ensure you have:

- ✅ Python 3.12+ installed
- ✅ uv package manager installed
- ✅ OpenAI API key
- ✅ AgenticFleet installed (see [Installation Guide](installation.md))

---

## Step 1: Configure Your Environment

Create and configure your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

Add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

💡 **Tip:** You can get an API key from [OpenAI Platform](https://platform.openai.com/api-keys).

---

## Step 2: Launch AgenticFleet

Start the interactive CLI:

```bash
make run
# Or: uv run fleet
```

You should see the welcome screen:

```
╔══════════════════════════════════════════════════════════════════╗
║                         AgenticFleet v0.5.3                      ║
║                   Multi-Agent Orchestration                      ║
╚══════════════════════════════════════════════════════════════════╝

Available commands: help, quit, clear, checkpoints, resume, stream, history
Magentic Fleet initialized with 3 agents: researcher, coder, analyst

fleet> _
```

---

## Step 3: Run Your First Workflow

Try a simple research task:

```
fleet> Explain quantum computing in 3 sentences. Be concise.
```

### What Happens Next?

Watch as AgenticFleet orchestrates the workflow:

1. **Planning Phase**
   ```
   Plan · Iteration 1
   Facts: User wants quantum computing explained concisely
   Plan: Delegate to researcher for summary, synthesize response
   ```

2. **Agent Execution**
   ```
   Agent · researcher
   Quantum computing uses quantum bits (qubits) that can exist in...
   ```

3. **Result Synthesis**
   ```
   Result
   ✓ Task completed successfully

   [Final answer displayed here]
   ```

---

## Step 4: Try Different Agent Types

### Code Generation

Ask the coder agent to write code:

```
fleet> Write a Python function to calculate Fibonacci numbers
```

The coder agent will:
- Generate the code
- Explain the approach
- Provide usage examples

### Data Analysis

Request data analysis:

```
fleet> What statistical method should I use for analyzing customer churn?
```

The analyst agent will:
- Recommend appropriate methods
- Explain the rationale
- Suggest visualization approaches

### Research Tasks

Complex research queries:

```
fleet> Research the latest developments in transformer architectures for NLP
```

The researcher agent will:
- Search for information (mock data in default setup)
- Summarize findings
- Provide structured insights

---

## Step 5: Explore CLI Features

### View Available Commands

```
fleet> help
```

Available commands:
- `help` – Show all commands
- `quit` / `exit` – Exit AgenticFleet
- `clear` – Clear the screen
- `checkpoints` – List saved checkpoints
- `resume <id>` – Resume from a checkpoint
- `stream` – Toggle streaming mode
- `history` – View command history

### Use Command History

Navigate previous commands:
- **↑ / ↓** – Scroll through history
- **Ctrl+R** – Search history
- **Ctrl+C** – Cancel current input

### Save & Resume Workflows

Checkpoints are automatically saved after each round. To resume:

```
fleet> checkpoints
```

Output:
```
Available checkpoints:
  1. abc123 - 2 minutes ago (Round 3)
  2. def456 - 5 minutes ago (Round 2)
```

Resume a workflow:

```
fleet> resume abc123
```

---

## Common Usage Patterns

### Simple Q&A

Perfect for quick answers:

```
fleet> What is the capital of France?
```

**Expected behavior:** Quick response, minimal agent interaction.

### Multi-Step Tasks

Complex tasks with multiple agents:

```
fleet> Research Python web frameworks, write example code, and analyze performance considerations
```

**Expected behavior:**
1. Researcher finds information about frameworks
2. Coder writes example code
3. Analyst provides performance insights
4. Manager synthesizes final answer

### Iterative Refinement

Build on previous responses:

```
fleet> Explain machine learning
fleet> Now explain how neural networks fit into that
fleet> Can you provide a simple code example?
```

**Expected behavior:** Context is maintained across queries.

---

## Understanding the Output

### Plan Section

Shows the manager's planning process:

```
Plan · Iteration 1
Facts:
  - User wants explanation of X
  - No prior context available

Plan:
  1. Delegate to researcher for information
  2. Synthesize findings into clear explanation
```

### Progress Section

Tracks workflow state:

```
Progress
Status: In progress
Next speaker: researcher
Current round: 2/30
```

### Agent Messages

Shows agent responses:

```
Agent · researcher
Quantum computing leverages quantum mechanical phenomena...
[Agent output streamed here]
```

### Final Result

```
Result
✓ Task completed successfully

[Synthesized final answer]
```

---

## Configuration Quick Tips

### Adjust Agent Behavior

Edit agent configs in `src/agenticfleet/agents/<agent>/config.yaml`:

```yaml
agent:
  name: researcher
  model: gpt-4o  # Change model
  temperature: 0.7  # Adjust creativity (0.0-2.0)
  system_prompt: "You are a research assistant..."  # Customize prompt
```

### Modify Workflow Settings

Edit `src/agenticfleet/config/workflow.yaml`:

```yaml
fleet:
  orchestrator:
    max_round_count: 30  # Maximum workflow rounds
    max_stall_count: 3   # Rounds before replanning
```

### Enable Features

In your `.env` file:

```bash
# Enable OpenTelemetry tracing
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317

# Enable memory persistence
MEM0_HISTORY_DB_PATH=./var/mem0.db
```

---

## Troubleshooting Quick Fixes

### No Response from Agents

**Problem:** Workflow hangs or produces no output.

**Solution:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Verify configuration
make test-config

# Check logs
tail -f logs/agenticfleet.log
```

### Rate Limit Errors

**Problem:** `RateLimitError` from OpenAI.

**Solution:**
- Reduce `max_round_count` in workflow.yaml
- Add delays between requests
- Use a different API key or upgrade your plan

### Import Errors

**Problem:** `ModuleNotFoundError` when starting.

**Solution:**
```bash
# Reinstall dependencies
uv sync --all-extras

# Verify installation
uv run python -c "import agenticfleet"
```

---

## Next Steps

Now that you're familiar with the basics:

1. **[Working with Agents](../guides/agents.md)** – Deep dive into agent customization
2. **[Configuration Guide](configuration.md)** – Full configuration options
3. **[HITL Approvals](../guides/human-in-the-loop.md)** – Add approval gates
4. **[Checkpointing Guide](../guides/checkpointing.md)** – Master workflow persistence
5. **[REST API](../api/rest-api.md)** – Integrate with external applications

---

## Example Workflows

### Research Paper Summary

```
fleet> Read and summarize the key findings from recent papers on large language model efficiency
```

### Code Review

```
fleet> Review this Python code for security issues: [paste code]
```

### Data Pipeline Design

```
fleet> Design a data pipeline for real-time user analytics with Python and Redis
```

### Technical Documentation

```
fleet> Write API documentation for a RESTful user authentication service
```

---

## Getting Help

- **In-CLI:** Type `help` for command reference
- **Documentation:** Browse the [full docs](../README.md)
- **Community:** [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions)
- **Issues:** [Report bugs](https://github.com/Qredence/agentic-fleet/issues)
- **Email:** <contact@qredence.ai>

---

**Congratulations!** 🎉 You've completed the quick start guide. You're now ready to build sophisticated multi-agent workflows with AgenticFleet.
