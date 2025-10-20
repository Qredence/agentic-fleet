# Frequently Asked Questions (FAQ)

Common questions about AgenticFleet answered.

---

## General Questions

### What is AgenticFleet?

AgenticFleet is a multi-agent orchestration system built on the Microsoft Agent Framework. It coordinates specialist agents (researcher, coder, analyst) through an intelligent manager to solve complex tasks.

### Who is AgenticFleet for?

- **Developers** building AI-powered applications
- **Researchers** needing automated research and analysis
- **Teams** wanting to leverage multi-agent systems
- **Anyone** interested in agentic AI workflows

### Is AgenticFleet free to use?

Yes, AgenticFleet is open-source under the MIT License. However, you'll need an OpenAI API key, which has associated costs based on usage.

### What's the difference between AgenticFleet and ChatGPT?

ChatGPT is a single AI assistant. AgenticFleet orchestrates multiple specialized agents that collaborate on complex tasks, with features like:
- Task decomposition and planning
- Agent specialization
- Workflow checkpointing
- Human-in-the-loop approvals
- Persistent memory

---

## Installation & Setup

### What are the system requirements?

- Python 3.12 or higher
- 4GB RAM minimum (8GB recommended)
- OpenAI API key
- Linux, macOS, or Windows (WSL2)

See [Installation Guide](../getting-started/installation.md) for details.

### Why use uv instead of pip?

uv is significantly faster than pip and provides better dependency resolution. It's the recommended package manager for AgenticFleet, offering:
- 10-100x faster installation
- Better lock file management
- Deterministic builds
- Cross-platform consistency

### Can I use conda or virtualenv?

While possible, we strongly recommend uv for the best experience. If you must use another tool:

```bash
# With pip
python -m venv .venv
source .venv/bin/activate
pip install -e .

# With conda
conda create -n agenticfleet python=3.12
conda activate agenticfleet
pip install -e .
```

### Where do I get an OpenAI API key?

1. Visit [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Go to API keys section
4. Click "Create new secret key"
5. Copy and store securely

Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

---

## Usage Questions

### How do I run AgenticFleet?

```bash
# Method 1: Using make
make run

# Method 2: Using uv
uv run fleet

# Method 3: Direct Python
uv run python -m agenticfleet
```

See [Quick Start](../getting-started/quickstart.md) for details.

### What tasks can AgenticFleet handle?

AgenticFleet excels at:
- **Research tasks**: Gathering and summarizing information
- **Code generation**: Writing and explaining code
- **Data analysis**: Statistical insights and recommendations
- **Complex workflows**: Multi-step tasks requiring planning
- **Q&A**: Answering questions with agent collaboration

### How do I save my work?

Checkpoints are automatically saved after each round. To resume:

```
fleet> checkpoints          # List saved checkpoints
fleet> resume abc123        # Resume from checkpoint ID
```

See [Checkpointing Guide](../guides/checkpointing.md).

### Can I use AgenticFleet programmatically?

Yes! Use the Python API:

```python
from agenticfleet.fleet import create_default_fleet

# Create fleet
fleet = create_default_fleet()

# Run workflow
result = await fleet.run("Your task here")
```

See [Python API Reference](../api/python-api.md).

### How do I stop a running workflow?

- **Interactive CLI**: Press `Ctrl+C` to cancel
- **Graceful exit**: Type `quit` or `exit`
- **API**: Use cancellation tokens

---

## Configuration

### Where are configuration files located?

- **Environment**: `.env` in project root
- **Workflow**: `src/agenticfleet/config/workflow.yaml`
- **Agents**: `src/agenticfleet/agents/<role>/config.yaml`

See [Configuration Guide](../getting-started/configuration.md).

### How do I change agent behavior?

Edit the agent's config file:

```bash
nano src/agenticfleet/agents/researcher/config.yaml
```

Modify:
- `system_prompt` for instructions
- `temperature` for creativity
- `model` for different AI models
- `tools` for available capabilities

### Can I use models other than OpenAI?

Currently, AgenticFleet is built for OpenAI models. However, the architecture supports:
- OpenAI (gpt-4o, gpt-5, o1-preview, etc.)
- Azure OpenAI (same models, different endpoint)

Future versions may support additional providers.

### How do I reduce API costs?

1. **Lower max_round_count**: Fewer iterations
   ```yaml
   orchestrator:
     max_round_count: 15  # Instead of 30
   ```

2. **Use cheaper models**: Where appropriate
   ```yaml
   researcher:
     model: gpt-4o-mini  # Instead of gpt-5
   ```

3. **Disable streaming**: Slight token savings
   ```yaml
   stream: false
   ```

4. **Reduce temperature**: More focused responses
   ```yaml
   temperature: 0.1
   ```

---

## Features

### What is Human-in-the-Loop (HITL)?

HITL adds approval gates for sensitive operations like code execution or file operations. When enabled, AgenticFleet pauses and asks for user approval before proceeding.

Enable in `workflow.yaml`:
```yaml
human_in_the_loop:
  enabled: true
  require_approval_for:
    - code_execution
    - file_operations
```

See [HITL Guide](../guides/human-in-the-loop.md).

### What is checkpointing?

Checkpointing saves workflow state after each round, allowing you to:
- Resume interrupted work
- Replay workflows
- Debug issues
- Avoid redundant API calls

Checkpoints are saved to `var/checkpoints/` by default.

### What is Mem0 memory?

Mem0 provides persistent memory across sessions using Azure AI Search and OpenAI embeddings. It remembers context from previous interactions.

Enable by setting environment variables:
```bash
MEM0_HISTORY_DB_PATH=./var/mem0.db
AZURE_AI_SEARCH_ENDPOINT=https://...
```

See [Memory Guide](../guides/memory.md).

### What is the Web UI?

AgenticFleet includes a React frontend for browser-based interaction with the REST API. Features:
- Visual workflow tracking
- Web-based HITL approvals
- SSE streaming
- Conversation history

See [Web UI Guide](../guides/web-ui.md).

---

## Troubleshooting

### Why am I getting "Module not found" errors?

**Cause**: Dependencies not installed or virtual environment not activated.

**Fix**:
```bash
# Reinstall dependencies
uv sync --all-extras

# Verify installation
uv run python -c "import agenticfleet"
```

### Why are agents not responding?

**Possible causes**:
1. Invalid API key
2. Rate limits exceeded
3. Model not accessible
4. Configuration error

**Fixes**:
```bash
# Check API key
echo $OPENAI_API_KEY

# Validate config
make test-config

# Check logs
tail -f logs/agenticfleet.log
```

### Why is my workflow stuck?

**Cause**: Agent stuck in loop or waiting for unresponsive service.

**Fixes**:
1. Reduce `max_stall_count` to trigger replanning sooner
2. Lower `max_round_count` to terminate earlier
3. Check tool configurations
4. Review orchestrator logs

### How do I enable debug logging?

```bash
# In .env
LOG_LEVEL=DEBUG

# Or environment variable
export LOG_LEVEL=DEBUG
```

Then check `logs/agenticfleet.log` for detailed information.

### Why am I getting rate limit errors?

**Cause**: Too many API requests in short time.

**Fixes**:
1. **Wait**: OpenAI rate limits reset over time
2. **Reduce rounds**: Lower max_round_count
3. **Upgrade tier**: Increase OpenAI usage limits
4. **Add delays**: Not currently configurable

---

## Advanced Topics

### Can I create custom agents?

Yes! Create a new agent directory:

```bash
cp -r src/agenticfleet/agents/researcher src/agenticfleet/agents/my_agent
```

Customize the config and register in `fleet_builder.py`.

See [Tool Development](../advanced/tool-development.md).

### Can I add custom tools?

Yes! Create a tool function:

```python
# agents/my_agent/tools/my_tool.py
from pydantic import BaseModel

class MyToolResponse(BaseModel):
    result: str

def my_tool(input: str) -> MyToolResponse:
    # Tool logic here
    return MyToolResponse(result="processed")
```

Add to agent config:
```yaml
tools:
  - name: my_tool
    enabled: true
```

### How do I integrate with external APIs?

Create a custom tool that calls your API:

```python
import httpx
from pydantic import BaseModel

class APIResponse(BaseModel):
    data: dict

async def api_tool(query: str) -> APIResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.example.com/endpoint",
            params={"q": query}
        )
        return APIResponse(data=response.json())
```

### Can I run AgenticFleet in production?

Yes, but consider:
1. **Environment variables**: Use secrets management
2. **Logging**: Centralized log aggregation
3. **Monitoring**: OpenTelemetry integration
4. **Rate limiting**: Handle gracefully
5. **Error handling**: Retry logic and fallbacks

See [Deployment Guide](../deployment/production.md).

### How do I contribute to AgenticFleet?

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

See [Contributing Guidelines](../../CONTRIBUTING.md).

---

## Performance

### How fast is AgenticFleet?

Speed depends on:
- **Model selected**: Faster models (gpt-4o) vs slower (o1-preview)
- **Task complexity**: Simple tasks ~10-30s, complex ~2-5 minutes
- **Round count**: More rounds = longer execution
- **API latency**: Network and OpenAI response times

### How much does it cost to run?

Costs vary by usage. Example (gpt-4o):
- Simple Q&A: $0.01-0.05
- Code generation: $0.05-0.15
- Research task: $0.10-0.30
- Complex multi-step: $0.30-1.00

Use token tracking to monitor costs:
```yaml
stream_options:
  include_usage: true
```

### Can I run AgenticFleet offline?

No, AgenticFleet requires:
- Internet connection for OpenAI API
- Active API key with credits

Local model support is not currently available but may be added in future versions.

---

## Comparison

### AgenticFleet vs LangChain?

| Feature | AgenticFleet | LangChain |
|---------|--------------|-----------|
| Focus | Multi-agent orchestration | General LLM chains |
| Architecture | Microsoft Agent Framework | Custom abstractions |
| Agents | Specialized roles | Custom agents |
| Checkpointing | Built-in | Via LangGraph |
| HITL | Native support | Custom implementation |
| Learning curve | Moderate | Steep |

### AgenticFleet vs AutoGPT?

| Feature | AgenticFleet | AutoGPT |
|---------|--------------|----------|
| Agent type | Multi-agent | Single agent |
| Planning | Magentic pattern | Autonomous |
| Control | Structured workflows | Autonomous loops |
| Safety | HITL approval gates | Limited |
| Customization | High | Moderate |

---

## Community

### Where can I get help?

- **Documentation**: [docs/](../README.md)
- **GitHub Issues**: [Report bugs](https://github.com/Qredence/agentic-fleet/issues)
- **Discussions**: [Ask questions](https://github.com/Qredence/agentic-fleet/discussions)
- **Email**: <contact@qredence.ai>

### How do I report a bug?

1. Check [existing issues](https://github.com/Qredence/agentic-fleet/issues)
2. If new, create an issue with:
   - Description of problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS)
   - Relevant logs

### How do I request a feature?

Open a [feature request](https://github.com/Qredence/agentic-fleet/issues/new) with:
- Use case description
- Proposed solution
- Alternative approaches considered
- Willingness to contribute

---

## Legal

### What license is AgenticFleet under?

MIT License. See [LICENSE](../../LICENSE) for full text.

### Can I use AgenticFleet commercially?

Yes, the MIT License allows commercial use. You're free to:
- Use in proprietary applications
- Modify and distribute
- Sell services built on AgenticFleet

### Do I need to open source my modifications?

No, the MIT License does not require sharing modifications. However, we welcome contributions back to the project!

---

**Still have questions?** Ask in [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions) or email <contact@qredence.ai>.
