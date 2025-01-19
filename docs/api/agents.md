# Agents API Reference

## Overview

AgenticFleet provides enhanced agent implementations built on top of AutoGen's agent framework. These agents are designed to handle complex interactions, provide better error handling, and support advanced features like multimodal processing.

## Agent Types

### EnhancedAssistantAgent

An enhanced version of AutoGen's AssistantAgent with improved capabilities and error handling.

```python
from agentic_fleet.models import EnhancedAssistantAgent

agent = EnhancedAssistantAgent(
    name="coding_assistant",
    system_message="You are an expert coding assistant",
    model_client=optional_custom_client
)
```

#### Parameters

- `name` (str): Unique identifier for the agent
- `system_message` (str): Initial system prompt that defines agent behavior
- `model_client` (Optional[ChatCompletionClient]): Custom model client, defaults to Azure OpenAI
- `**kwargs`: Additional arguments passed to AssistantAgent

#### Methods

##### process_message

```python
async def process_message(
    message: Union[str, Dict],
    context: Optional[Any] = None
) -> Any
```

Processes incoming messages with enhanced error handling and logging.

**Parameters:**
- `message`: The message to process (string or dictionary)
- `context`: Optional context information

**Returns:**
- Processed message response

**Raises:**
- Logs and re-raises any exceptions encountered during processing

### EnhancedUserProxyAgent

An enhanced version of AutoGen's UserProxyAgent with improved capabilities.

```python
from agentic_fleet.models import EnhancedUserProxyAgent

agent = EnhancedUserProxyAgent(
    name="user_proxy",
    system_message="Optional system message"
)
```

#### Parameters

- `name` (str): Unique identifier for the agent
- `system_message` (Optional[str]): Custom system message
- `**kwargs`: Additional arguments passed to UserProxyAgent

## Agent Teams

### Creating Agent Teams

```python
from agentic_fleet.models import create_agent_team

team = await create_agent_team(
    task="Implement a REST API",
    model_client=optional_custom_client
)
```

#### Parameters

- `task` (str): The task description for the team
- `model_client` (Optional[ChatCompletionClient]): Custom model client

#### Returns

Returns a configured `MagenticOneGroupChat` instance with:
- Assistant Agent
- Code Executor Agent
- Web Surfer Agent
- File System Agent

## Best Practices

1. **Error Handling**
   ```python
   try:
       result = await agent.process_message(message)
   except Exception as e:
       logger.error(f"Error in agent {agent.name}: {str(e)}")
   ```

2. **Custom Model Clients**
   ```python
   from agentic_fleet.models import create_azure_client
   
   client = create_azure_client()
   agent = EnhancedAssistantAgent(..., model_client=client)
   ```

3. **Team Configuration**
   ```python
   team = await create_agent_team(task)
   team.add_agent(custom_agent)  # Add custom agents
   ```

## Examples

### Basic Usage

```python
# Create an assistant agent
assistant = EnhancedAssistantAgent(
    name="python_expert",
    system_message="You are an expert Python developer"
)

# Create a user proxy
user_proxy = EnhancedUserProxyAgent(
    name="user",
    system_message="You are a helpful user proxy"
)

# Process a message
response = await assistant.process_message("How do I implement a decorator?")
```

### Advanced Usage

```python
# Create a team for a complex task
team = await create_agent_team("Build a web scraper")

# Configure team behavior
team.set_max_rounds(10)
team.enable_async_execution()

# Start the task
result = await team.execute()
```

## See Also

- [Models Documentation](./models.md)
- [Message Handling](./messages.md)
- [Configuration Guide](./configuration.md)
