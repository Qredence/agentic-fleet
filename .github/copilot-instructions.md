# AI Agent Instructions for AgenticFleet

## Project Overview

AgenticFleet is a multi-agent orchestration system built on **Microsoft Agent Framework** (using official Python APIs). It implements a **sequential orchestration pattern** where an Orchestrator delegates tasks to specialized agents (Researcher, Coder, Analyst). Each agent is a `ChatAgent` instance with dedicated tools returning **Pydantic-modeled structured responses**.

**Critical Architecture**: This uses the official Microsoft Agent Framework Python implementation with `ChatAgent` and `OpenAIChatClient` patterns—NOT Azure AI Foundry's `AgentsClient` or .NET's `MagenticBuilder`.

## Essential Commands (ALWAYS use `uv`)

```bash
# Install/sync dependencies
uv sync

# Run application
uv run python main.py

# Validate configuration
uv run python test_config.py

# Format and lint (REQUIRED before commits)
uv run black .
uv run ruff check .
```

**Never use `pip` or plain `python`—always prefix with `uv run` or work in activated venv.**

## Official Framework APIs Reference

**Do NOT use these** (they don't exist in Python or are from wrong SDK):
- ❌ `MagenticBuilder()` — .NET only, not in Python
- ❌ `from agent_framework.core import ChatAgent` — use `from agent_framework import ChatAgent`
- ❌ `OpenAIResponsesClient` — not official API
- ❌ `from azure.ai.agents import AgentsClient` — separate Azure AI SDK
- ❌ `context_provider` parameter — not in official docs

**DO use these** (official Python Agent Framework):
- ✅ `from agent_framework import ChatAgent`
- ✅ `from agent_framework.openai import OpenAIChatClient`
- ✅ `ChatAgent(chat_client=..., instructions="...", tools=[functions])`
- ✅ `await agent.run("query")` for execution
- ✅ Plain Python functions for tools with type hints

For full documentation, see the updated instructions in the file.
