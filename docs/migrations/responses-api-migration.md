# Migration to OpenAI Responses API

## Overview

This document describes the migration from `OpenAIChatClient` to `OpenAIResponsesClient` in AgenticFleet, aligning with Microsoft Agent Framework best practices for structured AI responses.

---

## Why OpenAIResponsesClient?

The Microsoft Agent Framework provides two OpenAI client types:

1. **OpenAIChatClient**: For basic chat completions
2. **OpenAIResponsesClient**: For OpenAI Responses API with structured outputs ✓

`OpenAIResponsesClient` is the recommended choice for agent applications because it:
- Provides structured response handling
- Better supports multi-agent workflows
- Aligns with Microsoft's agent framework design patterns
- Offers enhanced type safety and validation

---

## Changes Made

### 1. Import Statements

**Before:**
```python
from agent_framework.openai import OpenAIChatClient
```

**After:**
```python
from agent_framework.openai import OpenAIResponsesClient
```

### 2. Client Initialization

**Before:**
```python
client = OpenAIChatClient(
    model_id=agent_config.get("model", settings.openai_model),
)
```

**After:**
```python
client = OpenAIResponsesClient(
    model_id=agent_config.get("model", settings.openai_model),
)
```

### 3. Files Modified

All agent factories and the workflow manager were updated:

- ✓ `agents/orchestrator_agent/agent.py`
- ✓ `agents/researcher_agent/agent.py`
- ✓ `agents/coder_agent/agent.py`
- ✓ `agents/analyst_agent/agent.py`
- ✓ `workflows/magentic_workflow.py`

---

## API Parameters

### OpenAIResponsesClient Constructor

```python
OpenAIResponsesClient(
    model_id: str,           # Required: Model identifier (e.g., "gpt-4o", "gpt-5")
    api_key: str = None,     # Optional: Defaults to OPENAI_API_KEY env var
    # ... other optional parameters
)
```

### Key Points

1. **model_id**: Required parameter for the model to use
2. **api_key**: Read from `OPENAI_API_KEY` environment variable by default
3. **temperature**: Configured at agent or model call level, not in client constructor

---

## Environment Configuration

Ensure your `.env` file contains:

```bash
OPENAI_API_KEY=sk-proj-...your-key...
```

---

## Usage with UV Package Manager

Always use `uv run` for executing Python commands:

```bash
# Run configuration tests
uv run python test_config.py

# Start the application
uv run python main.py

# Run pytest
uv run pytest

# Run code formatting
uv run black .

# Run linting
uv run ruff check .
```

---

## Verification

### Test Configuration
```bash
uv run python test_config.py
```
Expected: All 6/6 tests pass

### Test Application Startup
```bash
echo "quit" | uv run python main.py
```
Expected: Application starts successfully with workflow creation message

---

## Migration Checklist

For any new agent or client code:

- [ ] Import `OpenAIResponsesClient` from `agent_framework.openai`
- [ ] Use `model_id` parameter (not `model`)
- [ ] Don't pass `temperature` or `api_key` to constructor
- [ ] Ensure `OPENAI_API_KEY` is set in environment
- [ ] Use `uv run` for all Python command executions
- [ ] Test with `uv run python test_config.py`
- [ ] Verify application startup

---

## Example: Creating a New Agent

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from config.settings import settings

def create_my_agent() -> ChatAgent:
    """Create a new agent using OpenAI Responses API."""
    
    # Load configuration
    config = settings.load_agent_config("agents/my_agent")
    agent_config = config.get("agent", {})
    
    # Create OpenAI Responses client
    # API key is read from OPENAI_API_KEY environment variable
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model),
    )
    
    # Create agent with tools
    agent = ChatAgent(
        name=agent_config.get("name", "my_agent"),
        instructions=config.get("system_prompt", ""),
        chat_client=client,
        tools=[],  # Add your tools here
    )
    
    return agent
```

---

## Common Issues

### Issue: "OpenAI model ID is required"

**Solution:** Ensure `model_id` parameter is provided to `OpenAIResponsesClient`

```python
# Wrong
client = OpenAIResponsesClient(model=...)

# Correct
client = OpenAIResponsesClient(model_id=...)
```

### Issue: "No API key found"

**Solution:** Set `OPENAI_API_KEY` in your `.env` file

```bash
echo "OPENAI_API_KEY=sk-proj-your-key" >> .env
```

---

## References

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [OpenAI Responses API Guide](https://github.com/microsoft/agent-framework/tree/main/python/examples)
- [UV Package Manager](https://github.com/astral-sh/uv)

---

## Status

**Migration Status:** ✅ Complete  
**Verification Status:** ✅ All Tests Passing  
**Production Ready:** ✅ Yes  
**Last Updated:** October 10, 2025
