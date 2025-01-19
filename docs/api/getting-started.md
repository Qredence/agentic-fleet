# Getting Started with AgenticFleet

## Introduction

AgenticFleet is a powerful multi-agent system that combines Chainlit's interactive interface with AutoGen's multi-agent capabilities. This guide will help you get up and running with AgenticFleet quickly.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- An Azure OpenAI API key (for default model client)
- Basic understanding of Python async programming

## Installation

1. **Install AgenticFleet**

```bash
pip install agentic-fleet
```

2. **Set up environment variables**

Create a `.env` file in your project root:

```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_DEPLOYMENT=your_deployment
```

## Quick Start

### 1. Basic Usage

Create a file named `basic_example.py`:

```python
from agentic_fleet.models import create_agent_team
import asyncio

async def main():
    # Create an agent team
    team = await create_agent_team("Write a Python function to calculate Fibonacci numbers")
    
    # Start the interaction
    result = await team.execute()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

Run the example:

```bash
python basic_example.py
```

### 2. Web Interface

Create a file named `web_app.py`:

```python
import chainlit as cl
from agentic_fleet.app import initialize_session, handle_message

@cl.on_chat_start
async def start():
    await initialize_session()

@cl.on_message
async def main(message: cl.Message):
    await handle_message(message)
```

Run the web interface:

```bash
chainlit run web_app.py
```

## Common Use Cases

### 1. Code Generation

```python
from agentic_fleet.models import EnhancedAssistantAgent

async def generate_code():
    agent = EnhancedAssistantAgent(
        name="code_expert",
        system_message="You are an expert Python developer"
    )
    
    prompt = """
    Create a Flask API endpoint that:
    1. Accepts POST requests
    2. Validates JSON input
    3. Returns processed data
    """
    
    response = await agent.process_message(prompt)
    print(response)
```

### 2. Multi-Agent Collaboration

```python
from agentic_fleet.models import create_agent_team

async def solve_complex_task():
    team = await create_agent_team(
        "Create a web scraper that:
        1. Fetches data from a website
        2. Processes the data
        3. Stores results in a database"
    )
    
    result = await team.execute()
    print(result)
```

### 3. File Operations

```python
import chainlit as cl
from agentic_fleet.app import initialize_session

@cl.on_chat_start
async def start():
    session = await initialize_session()
    
    # Upload a file
    @cl.on_upload
    async def handle_file(file: cl.File):
        content = file.content
        # Process file content
        result = await session.process_file(content)
        
        # Send results back
        await cl.Message(
            content=f"Processed file: {result}",
        ).send()
```

## Advanced Features

### 1. Custom Model Client

```python
from agentic_fleet.models import create_azure_client
from agentic_fleet.models import EnhancedAssistantAgent

# Create custom client
client = create_azure_client(
    temperature=0.7,
    max_tokens=2000
)

# Use custom client with agent
agent = EnhancedAssistantAgent(
    name="custom_agent",
    system_message="Custom system message",
    model_client=client
)
```

### 2. Error Handling

```python
from agentic_fleet.models import EnhancedAssistantAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_errors():
    try:
        agent = EnhancedAssistantAgent(
            name="error_handler",
            system_message="Test error handling"
        )
        
        result = await agent.process_message("Test message")
        return result
        
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        # Implement retry logic or fallback behavior
```

### 3. Custom Agent Teams

```python
from agentic_fleet.models import create_agent_team
from autogen_ext.agents import CustomAgent

async def custom_team():
    # Create base team
    team = await create_agent_team("Custom task")
    
    # Add custom agent
    custom_agent = CustomAgent(
        name="specialist",
        system_message="You are a domain specialist"
    )
    
    team.add_agent(custom_agent)
    return team
```

## Best Practices

1. **Environment Management**
   - Use `.env` files for configuration
   - Keep API keys secure
   - Use different environments for development and production

2. **Error Handling**
   - Implement proper logging
   - Use try-except blocks for API calls
   - Implement retry mechanisms for network operations

3. **Performance Optimization**
   - Use cached model clients for repeated operations
   - Implement batch processing when possible
   - Monitor token usage and API calls

4. **Security**
   - Never expose API keys in code
   - Validate user input
   - Implement proper authentication for web interfaces

## Troubleshooting

### Common Issues

1. **API Key Issues**
   ```python
   # Check if API key is properly loaded
   import os
   from dotenv import load_dotenv

   load_dotenv()
   assert os.getenv("AZURE_OPENAI_API_KEY"), "API key not found"
   ```

2. **Model Client Errors**
   ```python
   # Test model client connection
   from agentic_fleet.models import create_azure_client

   client = create_azure_client()
   response = await client.generate("Test message")
   assert response, "Model client not responding"
   ```

3. **Web Interface Issues**
   ```python
   # Check Chainlit configuration
   import chainlit as cl

   @cl.on_chat_start
   async def test_connection():
       try:
           await cl.Message("Testing connection...").send()
       except Exception as e:
           print(f"Chainlit error: {str(e)}")
   ```

## Next Steps

- Explore the [API Documentation](./README.md)
- Check out [Example Projects](../examples/)
- Join our [Community Discord](https://discord.gg/agenticfleet)
- Contribute to [GitHub](https://github.com/qredence/agenticfleet)

## Support

If you encounter any issues or need help:
1. Check our [FAQ](../faq.md)
2. Open an issue on [GitHub](https://github.com/qredence/agenticfleet/issues)
3. Contact support at support@qredence.ai
