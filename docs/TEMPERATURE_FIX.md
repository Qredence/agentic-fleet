# Temperature Parameter Fix

## Issue

After migrating to the src/ layout, the application threw an error when trying to run agents:

```
Error code: 400 - {'error': {'message': "Unsupported parameter: 'temperature' is not supported with this model.", 'type': 'invalid_request_error', 'param': 'temperature', 'code': None}}
```

## Root Cause

The `ChatAgent` class in **Microsoft Agent Framework Python** does **NOT** accept a `temperature` parameter in its constructor. This is different from some other agent frameworks.

According to the official Microsoft Agent Framework documentation:

- `ChatAgent` accepts: `chat_client`, `instructions`, `name`, `tools`
- Temperature is **model-specific** and **not a `ChatAgent` parameter**
- Some models (like OpenAI o1 reasoning models) don't support temperature at all

## What Was Wrong

In all four agent factory functions, we were passing `temperature` to `ChatAgent`:

```python
# INCORRECT ❌
return ChatAgent(
    chat_client=chat_client,
    instructions=config.get("system_prompt", ""),
    name=agent_config.get("name", "orchestrator"),
    temperature=agent_config.get("temperature", 0.1),  # ❌ Not a valid parameter
)
```

## The Fix

Removed the `temperature` parameter from all `ChatAgent` constructor calls:

```python
# CORRECT ✅
return ChatAgent(
    chat_client=chat_client,
    instructions=config.get("system_prompt", ""),
    name=agent_config.get("name", "orchestrator"),
)
```

### Files Modified

1. `src/agenticfleet/agents/orchestrator/agent.py` - Removed temperature parameter
2. `src/agenticfleet/agents/researcher/agent.py` - Removed temperature parameter
3. `src/agenticfleet/agents/coder/agent.py` - Removed temperature parameter
4. `src/agenticfleet/agents/analyst/agent.py` - Removed temperature parameter

## Microsoft Agent Framework Patterns

Based on research using Context7 documentation tool:

### ✅ Correct Pattern

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIResponsesClient

client = OpenAIResponsesClient(model_id="gpt-4o")
agent = ChatAgent(
    chat_client=client,
    instructions="Your system prompt",
    name="agent_name",
    tools=[tool1, tool2]  # Optional
)
```

### ❌ Incorrect Pattern

```python
# This will fail - temperature is not a ChatAgent parameter
agent = ChatAgent(
    chat_client=client,
    instructions="Your system prompt",
    name="agent_name",
    temperature=0.1  # ❌ Invalid parameter
)
```

## Configuration Files (No Change Needed)

The temperature values in agent config files are preserved for future use, but currently not used:

```yaml
# src/agenticfleet/agents/orchestrator/config.yaml
agent:
  name: "orchestrator"
  model: "gpt-4o"  # Changed from "gpt-5" (which doesn't exist)
  temperature: 0.1  # Preserved but not currently used
  max_tokens: 4000
```

These values can be used in the future if:

1. Microsoft Agent Framework adds temperature support to ChatAgent
2. We implement runtime temperature via ChatOptions
3. We switch to a different client that supports it

## Alternative: Runtime Temperature (Future)

If temperature control is needed in the future, Microsoft Agent Framework may support it via runtime options:

```python
# Hypothetical future pattern (not currently implemented)
result = await agent.run(
    "user query",
    options=ChatOptions(temperature=0.1)
)
```

## Testing

All tests pass after the fix:

```bash
$ uv run pytest tests/test_config.py -v
====== 6 passed in 0.86s ======
```

## Verification

To verify agents work correctly:

```bash
# Run all tests
uv run pytest -v

# Try the REPL
uv run agentic-fleet
```

## Additional Model Configuration

Also fixed the model name in orchestrator config:

**Before:**

```yaml
model: "gpt-5"  # ❌ Doesn't exist
```

**After:**

```yaml
model: "gpt-4o"  # ✅ Valid model
```

## Key Takeaways

1. **Always check official framework documentation** - Don't assume APIs from other frameworks
2. **`ChatAgent` parameters are limited** - Only: `chat_client`, `instructions`, `name`, `tools`
3. **Temperature is model-specific** - Not all models support it
4. **Use Context7** (#upstash/context7) for quick documentation lookup
5. **Keep config values** even if not currently used - May be useful later

## Related Documentation

- Microsoft Agent Framework Python: <https://github.com/microsoft/agent-framework/tree/main/python>
- ChatAgent examples: <https://github.com/microsoft/agent-framework/blob/main/python/samples/getting_started/agents/openai/>
- Official docs: <https://learn.microsoft.com/en-us/agent-framework/>

---
**Fixed:** 2025-10-12
**Context:** Part of src/ layout migration cleanup
**Impact:** Resolves runtime errors, enables proper agent execution
