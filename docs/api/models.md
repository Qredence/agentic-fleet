# Models API Reference

## Overview

AgenticFleet's models module provides interfaces and implementations for working with various language models and AI services. The module is built on top of AutoGen's model framework with additional enhancements for better error handling, logging, and configuration management.

## Core Components

### Model Clients

#### AzureOpenAIChatCompletionClient

The default model client using Azure OpenAI services.

```python
from agentic_fleet.models import create_azure_client

client = create_azure_client()
```

##### Configuration

The client can be configured using environment variables or direct parameters:

```python
# Environment variables
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_MODEL=gpt-4

# Or programmatically
client = create_azure_client(
    api_key="your_api_key",
    endpoint="your_endpoint",
    model="gpt-4"
)
```

#### CogCache Client

A caching layer for model responses to improve performance and reduce API calls.

```python
from agentic_fleet.models import create_cogcache_client

cached_client = create_cogcache_client()
```

### Message Types

#### TextMessage

Basic text-based message type.

```python
from autogen_agentchat.messages import TextMessage

message = TextMessage(content="Hello, world!")
```

#### MultiModalMessage

Support for messages containing both text and images.

```python
from autogen_agentchat.messages import MultiModalMessage, Image

message = MultiModalMessage([
    "Analyze this image:",
    Image(url="https://example.com/image.jpg")
])
```

## Usage Examples

### Basic Model Usage

```python
from agentic_fleet.models import create_azure_client

# Create a client
client = create_azure_client()

# Generate a response
response = await client.generate("Explain Python decorators")
```

### Advanced Usage

```python
# Create a cached client
cached_client = create_cogcache_client()

# Configure caching behavior
cached_client.set_cache_duration(hours=24)
cached_client.set_cache_size(max_items=1000)

# Use with an agent
agent = EnhancedAssistantAgent(
    name="cached_assistant",
    model_client=cached_client
)
```

### Error Handling

```python
try:
    client = create_azure_client()
    response = await client.generate("Query")
except Exception as e:
    if isinstance(e, RateLimitError):
        # Handle rate limiting
        await asyncio.sleep(60)
    elif isinstance(e, AuthenticationError):
        # Handle auth issues
        refresh_credentials()
    else:
        # Handle other errors
        logger.error(f"Unexpected error: {str(e)}")
```

## Best Practices

1. **Model Selection**
   - Use GPT-4 for complex reasoning tasks
   - Use GPT-3.5-Turbo for simpler tasks
   - Consider cost vs. performance tradeoffs

2. **Caching Strategy**
   - Cache frequently used responses
   - Set appropriate cache duration
   - Monitor cache hit rates

3. **Error Handling**
   - Implement proper retry logic
   - Handle rate limits gracefully
   - Log errors with context

4. **Performance Optimization**
   - Use batch processing when possible
   - Implement request pooling
   - Monitor token usage

## Configuration

### Environment Variables

```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_DEPLOYMENT=your_deployment
COGCACHE_ENABLED=true
COGCACHE_DURATION=24
```

### Model Parameters

```python
model_params = {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.95,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
}

client = create_azure_client(params=model_params)
```

## See Also

- [Agents Documentation](./agents.md)
- [Configuration Guide](./configuration.md)
- [Message Handling](./messages.md)
