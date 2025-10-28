# LiteLLM Integration

AgenticFleet now supports LiteLLM as a universal LLM proxy, enabling you to use multiple LLM providers (OpenAI, Anthropic, Azure OpenAI, Google, and many more) through a single unified interface with built-in caching and tracing capabilities.

## What is LiteLLM?

[LiteLLM](https://github.com/BerriAI/litellm) is a lightweight Python package that provides:

- **Universal Interface**: Call 100+ LLMs using the same format (OpenAI, Anthropic, Azure, Google, Cohere, etc.)
- **Built-in Caching**: Reduce costs with automatic response caching
- **Native Tracing**: Built-in observability for tracking LLM calls
- **Load Balancing**: Automatically distribute requests across multiple models
- **Fallback Support**: Automatically retry with different models on failure

## Quick Start

### 1. Enable LiteLLM

Set the following environment variables in your `.env` file:

```bash
# Enable LiteLLM
USE_LITELLM=true

# Specify the model to use - can be from any supported provider
LITELLM_MODEL="gpt-4o-mini"
```

### 2. Run AgenticFleet

```bash
uv run agentic-fleet
```

All agents will now use LiteLLM to communicate with your chosen LLM provider!

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_LITELLM` | No | `false` | Enable LiteLLM client for all agents |
| `LITELLM_MODEL` | Yes* | - | Model identifier (see examples below) |
| `LITELLM_API_KEY` | No | - | API key (can also use provider-specific env vars) |
| `LITELLM_BASE_URL` | No | - | Base URL for custom endpoints or LiteLLM proxy |
| `LITELLM_TIMEOUT` | No | `600` | Request timeout in seconds |

*Required when `USE_LITELLM=true`

### Model Identifiers

#### OpenAI
```bash
LITELLM_MODEL="gpt-4o-mini"
LITELLM_MODEL="gpt-4o"
# API key: Use OPENAI_API_KEY
```

#### Anthropic
```bash
LITELLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
LITELLM_MODEL="anthropic/claude-3-5-haiku-20241022"
# API key: Use ANTHROPIC_API_KEY
```

#### Azure OpenAI
```bash
LITELLM_MODEL="azure/gpt-4o"
# API keys: Use AZURE_API_KEY, AZURE_API_BASE, AZURE_API_VERSION
```

See the full list of supported providers at: https://docs.litellm.ai/docs/providers

## Example: Using Anthropic Claude

```bash
# .env
USE_LITELLM=true
LITELLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
ANTHROPIC_API_KEY="sk-ant-..."
```

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Supported Providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM Proxy Guide](https://docs.litellm.ai/docs/proxy/quick_start)
