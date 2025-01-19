# Web Interface API Reference

## Overview

AgenticFleet provides a web-based interface built with Chainlit, offering real-time interaction with the multi-agent system. The interface supports code highlighting, markdown rendering, file operations, and OAuth authentication.

## Core Components

### Session Management

#### initialize_session

```python
async def initialize_session() -> None
```

Initializes a new user session and sets up the agent team.

Example:
```python
@cl.on_chat_start
async def start():
    await initialize_session()
```

### Message Handling

#### handle_message

```python
async def handle_message(message: cl.Message) -> None
```

Processes incoming user messages and coordinates agent responses.

Example:
```python
@cl.on_message
async def main(message: cl.Message):
    await handle_message(message)
```

### Response Processing

#### process_response

```python
async def process_response(
    response: Any,
    collected_responses: List[str]
) -> None
```

Processes agent responses while preserving attribution and showing inner messages.

### Authentication

#### oauth_callback

```python
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User
) -> None
```

Handles OAuth authentication callbacks.

## UI Components

### Input Widgets

```python
from chainlit.input_widget import Select, Slider, TextInput

# Dropdown selection
model_select = Select(
    label="Model",
    values=["gpt-4", "gpt-3.5-turbo"],
    initial_value="gpt-4"
)

# Parameter slider
temperature = Slider(
    label="Temperature",
    min_value=0.0,
    max_value=1.0,
    step=0.1,
    initial_value=0.7
)

# Text input
system_prompt = TextInput(
    label="System Prompt",
    initial_value="You are a helpful assistant"
)
```

### Message Display

```python
# Send text message
await cl.Message(content="Processing your request...").send()

# Send code snippet
await cl.Message(
    content="Here's an example:",
    language="python",
    code=code_snippet
).send()

# Send error message
await cl.Message(
    content="An error occurred",
    type="error"
).send()
```

## File Operations

### File Upload

```python
@cl.on_upload
async def handle_file_upload(file: cl.File):
    content = file.content
    await process_file(content)
```

### File Download

```python
# Create downloadable file
file = cl.File(
    name="result.txt",
    content="Results data".encode(),
    mime="text/plain"
)

# Send file to user
await cl.Message(
    content="Here are your results",
    files=[file]
).send()
```

## Settings Management

### update_settings

```python
async def update_settings(settings: dict) -> None
```

Handles settings updates from the UI.

Example:
```python
@cl.on_settings_update
async def setup_agent(settings: dict):
    await update_settings(settings)
```

## Best Practices

1. **Error Handling**
   ```python
   try:
       await process_user_input(message)
   except Exception as e:
       await cl.Message(
           content=f"Error: {str(e)}",
           type="error"
       ).send()
   ```

2. **Progress Updates**
   ```python
   async with cl.Step("Processing"):
       await long_running_task()
   ```

3. **Resource Cleanup**
   ```python
   @cl.on_chat_end
   async def cleanup():
       await cleanup_resources()
   ```

## Examples

### Basic Chat Interface

```python
import chainlit as cl
from agentic_fleet.app import initialize_session, handle_message

@cl.on_chat_start
async def start():
    await initialize_session()

@cl.on_message
async def main(message: cl.Message):
    await handle_message(message)

@cl.on_chat_end
async def end():
    await cleanup()
```

### Advanced Features

```python
# Multi-step process
async with cl.Step("Analyzing code"):
    result = await analyze_code(message.content)

async with cl.Step("Generating solution"):
    solution = await generate_solution(result)

# Interactive elements
elements = [
    cl.Select(...),
    cl.Slider(...),
    cl.TextInput(...)
]
await cl.Message(
    content="Configure parameters:",
    elements=elements
).send()
```

## See Also

- [Chainlit Documentation](https://docs.chainlit.io)
- [Authentication Guide](./authentication.md)
- [Configuration Guide](./configuration.md)
