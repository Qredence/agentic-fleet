# 🚀 AgenticFleet Quick Reference

## One-Command Setup

```bash
# From AgenticFleet directory
cp .env.example .env           # Add your OPENAI_API_KEY
uv sync                        # Install all dependencies
source .venv/bin/activate      # Activate environment
python test_config.py          # Verify setup (should pass 6/6)
python main.py                 # Launch application
```

## 📂 Key Files

| File | Purpose |
|------|---------|
| `main.py` | Application entry point - run this |
| `test_config.py` | Configuration validation tests |
| `config/settings.py` | Configuration loader |
| `config/workflow_config.yaml` | Workflow execution parameters |
| `workflows/magentic_workflow.py` | Multi-agent coordination |

## 🎛️ Live CLI Experience

Run `uv run fleet` to launch the rich console (the legacy `uv run agentic-fleet` alias still works). The interface now:

- Streams Magentic plans, agent “thoughts”, and progress ledgers in real time.
- Shows shimmering loading states while the fleet reasons.
- Displays final answers in structured panels with zero scrolling guesswork.
- Prompt history/search (↑/↓, Ctrl+R) powered by prompt-toolkit for fast iteration.

## 🤖 Agents

| Agent | Temperature | Tools | Purpose |
|-------|-------------|-------|---------|
| **Orchestrator** | 0.1 | None | Task planning & delegation |
| **Researcher** | 0.3 | `web_search_tool` | Information gathering |
| **Coder** | 0.2 | None (draft guidance only) | Code suggestions & review |
| **Analyst** | 0.2 | `data_analysis_tool`, `visualization_suggestion_tool` | Data analysis & insights |

## 🛠️ Tools

### Web Search (`researcher_agent`)

```python
from agents.researcher_agent.tools.web_search_tools import web_search_tool

response = web_search_tool("Python machine learning")
# Returns: WebSearchResponse with SearchResult[]
```

### Coder Agent (draft only)

```python
from agenticfleet.agents import create_coder_agent

coder = create_coder_agent()
suggestion = await coder.run("Draft a Python function that greets a user")
# Returns: guidance plus code snippet (execution happens manually)
```

### Data Analysis (`analyst_agent`)

```python
from agents.analyst_agent.tools.data_analysis_tools import (
    data_analysis_tool,
    visualization_suggestion_tool
)

analysis = data_analysis_tool(data="Sales: Q1=$100k, Q2=$150k")
# Returns: DataAnalysisResponse with insights[]

viz = visualization_suggestion_tool(data_type="time_series")
# Returns: VisualizationSuggestion with chart_type, rationale
```

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
OPENAI_API_KEY=sk-your-key-here    # Required
OPENAI_MODEL=gpt-4o                # Optional (default in configs)
```

### Workflow Limits (`config/workflow_config.yaml`)

```yaml
workflow:
  max_rounds: 10          # Max conversation rounds
  max_stalls: 3           # Max stalls before reset
  max_resets: 2           # Max workflow resets
  timeout_seconds: 300    # Task timeout
```

### Agent Config (`agents/*/agent_config.yaml`)

```yaml
agent:
  name: "agent_name"
  model: "gpt-4o"
  temperature: 0.2        # Agent-specific
  max_tokens: 4000

system_prompt: |
  Your agent's instructions here

# Agent-specific settings below
## 🎯 Example Tasks

### Research + Code

```text
🎯 Your task: Research Python async programming and write example code with error handling
```

### Data Analysis

```text
🎯 Your task: Analyze sales trends Q1-Q4: $100k, $150k, $200k, $180k and suggest best visualization
```

### Mixed Task

```text
🎯 Your task: Research REST API best practices, write a Python Flask example, and explain security considerations
```

### Code Explanation

```text
🎯 Your task: Write a Python function to merge sorted lists and explain time complexity
```

## 🧪 Testing

### Run All Tests

```bash
python test_config.py
```

### Expected Output

```text
✓ PASS - Environment file
✓ PASS - OpenAI API Key
✓ PASS - Workflow config: max_rounds
✓ PASS - Workflow config: max_stalls
✓ PASS - Workflow config: max_resets
✓ PASS - orchestrator_agent config
✓ PASS - researcher_agent config
✓ PASS - coder_agent config
✓ PASS - analyst_agent config
✓ PASS - Import web_search_tool
✓ PASS - Import code_interpreter_tool
✓ PASS - Import data_analysis_tool
✓ PASS - Import visualization_suggestion_tool
✓ PASS - Factory create_orchestrator_agent
✓ PASS - Factory create_researcher_agent
✓ PASS - Factory create_coder_agent
✓ PASS - Factory create_analyst_agent
✓ PASS - Workflow import

Overall: 6/6 tests passed
```

## 🐛 Common Issues

### "OPENAI_API_KEY not found"

```bash
# Solution: Add key to .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### "Module not found" errors

```bash
# Solution: Reinstall dependencies
uv sync --force
# or
pip install -e . --force-reinstall
```

### YAML syntax errors

```bash
# Solution: Validate YAML files
python -c "import yaml; yaml.safe_load(open('config/workflow_config.yaml'))"
```

### Import errors from agents

```bash
# Solution: Check you're in project root and venv is active
pwd  # Should end in /AgenticFleet
which python  # Should point to .venv/bin/python
```

## 📊 Project Structure

```text
AgenticFleet/
├── main.py                     ← Run this
├── test_config.py              ← Test this first
├── .env                        ← Add your API key here
│
├── config/
│   ├── settings.py
│   └── workflow_config.yaml
│
├── agents/
│   ├── orchestrator_agent/
│   │   ├── agent.py
│   │   └── agent_config.yaml
│   ├── researcher_agent/
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/web_search_tools.py
│   ├── coder_agent/
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/code_interpreter.py
│   └── analyst_agent/
│       ├── agent.py
│       ├── agent_config.yaml
│       └── tools/data_analysis_tools.py
│
└── workflows/
    └── magentic_workflow.py
```

## 🔍 Debugging

### Enable verbose output

```python
# In main.py, add before workflow creation:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check agent creation

```python
# Test individual agent
from agents.orchestrator_agent.agent import create_orchestrator_agent
orchestrator = create_orchestrator_agent()
print(f"Agent created: {orchestrator}")
```

### Validate configuration

```python
# Test config loading
from config.settings import settings
print(f"Workflow config: {settings.workflow_config}")
print(f"Agent config: {settings.load_agent_config('agents/orchestrator_agent')}")
```

## 💡 Tips

### Customize Agent Behavior

Edit `agents/*/agent_config.yaml` to change:

- Temperature (creativity vs consistency)
- System prompt (agent personality and rules)
- Max tokens (response length)

### Adjust Execution Limits

Edit `config/workflow_config.yaml` to change:

- `max_rounds`: More rounds = more complex tasks
- `max_stalls`: Patience for stuck workflows
- `timeout_seconds`: Overall task timeout

### Monitor Workflow Events

The `on_event` handler in `workflows/magentic_workflow.py` logs all workflow events. Uncomment print statements for detailed tracking.

## 📚 Resources

- **Documentation Index**: `docs/README.md`
- **Implementation Details**: `../overview/implementation-summary.md`
- **Developer Standards**: `../operations/repository-guidelines.md`
- **Troubleshooting**: `../runbooks/troubleshooting.md`
- **Microsoft Agent Framework**: [docs.microsoft.com/agent-framework](https://docs.microsoft.com/agent-framework)

## 🆘 Get Help

1. **Configuration Issues**: Run `python test_config.py`
2. **Runtime Errors**: Check `.env` file and API key
3. **Tool Errors**: Verify imports work: `python -c "from agents.researcher_agent.tools.web_search_tools import web_search_tool"`
4. **Workflow Errors**: Check YAML syntax in config files

---

**Ready to start?** Run: `python main.py`
