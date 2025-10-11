---
description: Patterns and best practices for Microsoft Agent Framework Python implementation
applyTo: "agents/**/*.py"
---

# Microsoft Agent Framework Memory

Essential patterns for building reliable agent systems with the official Python SDK

## Use OpenAIResponsesClient for Agent Chat Clients

Prefer `OpenAIResponsesClient` over `OpenAIChatClient` when creating agents:

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

client = OpenAIResponsesClient(
    model_id="gpt-4o"  # Required parameter
)

agent = ChatAgent(
    chat_client=client,
    instructions="System prompt",
    name="agent_name",
    temperature=0.2,
    tools=[tool1, tool2]
)
```

**Why**: `OpenAIResponsesClient` provides:

- Structured output support with better type safety
- Access to newer OpenAI Responses API features
- Better integration with Pydantic models for tool responses
- Official recommended pattern for agent applications

**When migrating**: Update three locations per agent file:

1. Import statement: `from agent_framework.openai import OpenAIResponsesClient`
2. Client instantiation: `OpenAIResponsesClient(model_id=...)`
3. Docstrings referencing the client type

**Validation**: Run `python test_config.py` to verify all agent factories remain callable after migration.

## Preserve Existing Model Names During Migrations

When updating agent client implementations, maintain the configured model names from `agent_config.yaml`:

```python
# Load model from config
config = settings.load_agent_config("agents/analyst_agent")
agent_config = config.get("agent", {})

# Use configured model, fall back to settings default
client = OpenAIResponsesClient(
    model_id=agent_config.get("model", settings.openai_model)
)
```

**Why**: Model names may include custom or preview models (e.g., `gpt-5`, `gpt-5-codex`) that should not be automatically updated to current stable versions during refactoring.

## Use Official Framework Documentation as Source of Truth

When uncertain about Microsoft Agent Framework APIs, fetch documentation from the official repository:

```bash
# Use mcp_cognitionai_d_read_wiki_contents tool
# Repository: microsoft/agent-framework
```

**Avoid**: Assuming APIs from Azure AI Foundry SDK (`azure.ai.agents`) or .NET implementations (`MagenticBuilder`) exist in the Python SDK—they don't share the same API surface.

**Reference**: The Python implementation centers on `ChatAgent` + client patterns, not the `AgentsClient` from Azure AI SDK.
