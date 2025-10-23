# Agent Development Guide

## Overview

This guide covers creating new agents for AgenticFleet, including factory patterns, tool development, and configuration management.

## Prerequisites

- Understanding of AgenticFleet architecture
- Familiarity with Microsoft Agent Framework
- Python 3.12+ development environment
- Knowledge of agent's domain and required tools

## Agent Structure

Every agent follows a consistent structure:

```
src/agenticfleet/agents/<role>/
├── __init__.py           # Package initialization
├── agent.py               # Factory function and agent creation
├── config.yaml            # Agent configuration
├── tools/                 # Agent-specific tools
│   ├── __init__.py
│   ├── tool1.py
│   ├── tool2.py
│   └── ...
└── tests/                 # Agent-specific tests (optional)
    ├── test_agent.py
    └── test_tools.py
```

## Creating a New Agent

### 1. Scaffold Agent Structure

```bash
# Create agent directory and files
mkdir -p src/agenticfleet/agents/<role>/tools
touch src/agenticfleet/agents/<role>/{__init__.py,agent.py,config.yaml}
```

### 2. Agent Factory Function

Create the main factory function in `agent.py`:

```python
"""
Factory for creating the <role> agent.

This function loads configuration from YAML and constructs
a ChatAgent with appropriate tools and client configuration.
"""

from agent_framework import ChatAgent
from agent_framework.azure_ai import OpenAIResponsesClient
from agenticfleet.config.settings import settings
from agenticfleet.core.code_types import ToolResult  # Import base types

# Import agent-specific tools
from .tools import tool1, tool2, tool3

def create_<role>_agent() -> ChatAgent:
    """Create <role> agent with tools and configuration."""

    # Load agent-specific configuration
    config = settings.load_agent_config("<role>")
    agent_config = config.get("agent", {})

    # Create OpenAI client with configured model
    client = OpenAIResponsesClient(
        model_id=agent_config.get("model", settings.openai_model)
    )

    # Build tools list based on configuration
    tools = []
    tool_configs = agent_config.get("tools", [])

    for tool_config in tool_configs:
        if tool_config.get("enabled", False):
            tool_name = tool_config["name"]
            if tool_name == "tool1":
                tools.append(tool1.create_tool())
            elif tool_name == "tool2":
                tools.append(tool2.create_tool())
            # Add more tools as needed

    # Create and return the ChatAgent
    return ChatAgent(
        name=config["name"],
        model=agent_config.get("model", settings.openai_model),
        system_prompt=config["system_prompt"],
        client=client,
        tools=tools,
        temperature=agent_config.get("temperature", 0.2),
        max_tokens=agent_config.get("max_tokens", 4000)
    )
```

### 3. Agent Configuration

Create `config.yaml` with agent-specific settings:

```yaml
# Agent metadata
name: "<Role> Agent"
description: "Specialized agent for <domain> tasks"
model: "gpt-5"  # NEVER hardcode in Python code

# Agent behavior
temperature: 0.2
max_tokens: 4000
top_p: 1.0

# System prompt (multi-line YAML string)
system_prompt: |
  You are a specialized <role> agent with expertise in <domain>.

  Your responsibilities:
  - <primary responsibility 1>
  - <primary responsibility 2>
  - <primary responsibility 3>

  Guidelines:
  - Always provide accurate, well-structured responses
  - Use available tools when appropriate
  - Ask for clarification when tasks are ambiguous
  - Cite sources when using external information

# Tool configuration
tools:
  - name: tool1
    enabled: true
    description: "Description of what tool1 does"

  - name: tool2
    enabled: false  # Can be toggled via config
    description: "Description of what tool2 does"

  - name: tool3
    enabled: true
    parameters:
      param1: "value1"  # Tool-specific parameters
      param2: "value2"

# Optional runtime settings
capabilities:
  - "<capability1>"
  - "<capability2>"
  - "<capability3>"

# Integration settings
integrations:
  memory_provider: false  # Enable memory integration
  approval_required: false  # Requires HITL for all operations
```

### 4. Tool Development

#### Tool Structure

Each tool follows this pattern in `tools/<tool_name>.py`:

```python
"""
<Tool Name> for <Role> Agent.

This tool provides <functionality> for <specific use case>.
"""

from pydantic import BaseModel
from typing import Any, Dict

# Define result model
class <ToolName>Result(BaseModel):
    """Result model for <tool_name> operation."""

    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

def <tool_name>_tool(parameter1: str, parameter2: int) -> <ToolName>Result:
    """
    Execute <tool_name> operation with given parameters.

    Args:
        parameter1: Description of parameter1
        parameter2: Description of parameter2

    Returns:
        <ToolName>Result: Tool execution result with status and data
    """

    try:
        # Tool implementation logic
        result_data = perform_<tool_name>_operation(parameter1, parameter2)

        return <ToolName>Result(
            success=True,
            result=result_data,
            metadata={"execution_time_ms": 1250}
        )

    except Exception as e:
        return <ToolName>Result(
            success=False,
            error=str(e),
            metadata={"error_type": type(e).__name__}
        )

def create_<tool_name>_tool() -> Any:
    """Create tool function for agent framework."""

    from agent_framework import FunctionTool

    return FunctionTool(
        name="<tool_name>_tool",
        description="Description of what this tool does and when to use it",
        function=<tool_name>_tool
    )
```

#### Tool Examples

**Web Search Tool (Researcher Agent):**

```python
# tools/web_search_tool.py
from pydantic import BaseModel
from typing import List, Dict, Any

class WebSearchResult(BaseModel):
    """Result from web search operation."""

    query: str
    results: List[Dict[str, Any]]
    sources: List[str]
    total_found: int

def web_search_tool(query: str, max_results: int = 10) -> WebSearchResult:
    """
    Search the web for information related to the query.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        WebSearchResult: Search results with sources
    """

    # Implementation would call actual search API
    search_results = perform_web_search(query, max_results)

    return WebSearchResult(
        query=query,
        results=search_results["items"],
        sources=[r["url"] for r in search_results["items"]],
        total_found=search_results["total_count"]
    )
```

**Code Execution Tool (Coder Agent):**

```python
# tools/code_interpreter_tool.py
from pydantic import BaseModel
from typing import Dict, Any

class CodeExecutionResult(BaseModel):
    """Result from code execution operation."""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: int = 0

def code_interpreter_tool(code: str, language: str = "python") -> CodeExecutionResult:
    """
    Execute code in a sandboxed environment.

    Args:
        code: Code to execute
        language: Programming language (default: python)

    Returns:
        CodeExecutionResult: Execution output and status
    """

    # Code execution implementation
    start_time = time.time()

    try:
        # Execute code in sandbox
        result = execute_in_sandbox(code, language)

        return CodeExecutionResult(
            success=True,
            output=result["stdout"],
            exit_code=result["exit_code"],
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        return CodeExecutionResult(
            success=False,
            error=str(e),
            exit_code=1,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
```

### 5. Package Integration

Update `src/agenticfleet/agents/__init__.py`:

```python
# Export new agent factory
from .<role>.agent import create_<role>_agent

__all__ = [
    "create_<role>_agent"
]
```

### 6. Fleet Integration

Update `src/agenticfleet/fleet/fleet_builder.py`:

```python
class FleetBuilder:
    def __init__(self):
        self._agents = {}

    def with_agents(self) -> 'FleetBuilder':
        """Register all available agents."""

        # Import and register agents
        from agenticfleet.agents.orchestrator.agent import create_orchestrator_agent
        from agenticfleet.agents.researcher.agent import create_researcher_agent
        from agenticfleet.agents.coder.agent import create_coder_agent
        from agenticfleet.agents.analyst.agent import create_analyst_agent
        from agenticfleet.agents.<role>.agent import create_<role>_agent  # New agent

        # Register all agents
        self._agents = {
            "orchestrator": create_orchestrator_agent(),
            "researcher": create_researcher_agent(),
            "coder": create_coder_agent(),
            "analyst": create_analyst_agent(),
            "<role>": create_<role>_agent(),  # New agent registration
        }

        return self
```

### 7. Testing

#### Configuration Tests

Add to `tests/test_config.py`:

```python
def test_<role>_agent_creation(test_config_path):
    """Test <role> agent can be created from config."""
    settings = Settings()
    agents = create_default_agents()

    assert "<role>" in agents
    agent = agents["<role>"]

    assert agent.name == "<Role> Agent"
    assert agent.model == "gpt-5"  # Or configured model
    assert len(agent.tools) >= 0  # Should have some tools
```

#### Unit Tests

Create `tests/test_<role>_agent.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from agenticfleet.agents.<role>.agent import create_<role>_agent
from agenticfleet.agents.<role>.tools.tool1 import <ToolName>Result

class Test<Role>Agent:
    """Test suite for <Role> agent."""

    def test_agent_creation(self):
        """Test agent can be created successfully."""
        with patch('agenticfleet.config.settings.settings.load_agent_config') as mock_config:
            mock_config.return_value = {
                "name": "<Role> Agent",
                "model": "gpt-5",
                "system_prompt": "You are a specialized agent..."
            }

            agent = create_<role>_agent()

            assert agent.name == "<Role> Agent"
            assert agent.model == "gpt-5"

    def test_tool_execution(self):
        """Test agent tool execution."""
        from agenticfleet.agents.<role>.tools.tool1 import <tool_name>_tool

        result = <tool_name>_tool("test_input")

        assert isinstance(result, <ToolName>Result)
        assert result.success is True
```

## Configuration Management

### Environment Variables

Agent configuration can reference environment variables in YAML:

```yaml
# config.yaml example
name: "My Agent"
model: "${AGENT_MODEL:-gpt-5}"  # Use AGENT_MODEL env var or default
api_key: "${API_KEY}"         # Require API_KEY env var
timeout: ${TIMEOUT:-300}           # Use TIMEOUT env var or default 300
```

### Dynamic Configuration

Allow runtime configuration changes:

```python
# Allow tool enablement/disablement at runtime
def create_<role>_agent() -> ChatAgent:
    config = settings.load_agent_config("<role>")

    # Check environment for feature flags
    enable_advanced_features = os.getenv("ENABLE_ADVANCED_FEATURES", "false").lower() == "true"

    # Modify tool list based on configuration
    tools = build_tools_list(config, enable_advanced_features)

    return ChatAgent(
        name=config["name"],
        model=config["model"],
        tools=tools,
        # ... other parameters
    )
```

## Best Practices

### Tool Design

1. **Single Responsibility**: Each tool does one thing well
2. **Pure Functions**: Avoid side effects and global state
3. **Error Handling**: Comprehensive error handling with meaningful messages
4. **Type Safety**: Use Pydantic models for all inputs/outputs
5. **Documentation**: Clear docstrings and parameter descriptions
6. **Testing**: Unit tests for all tool functions
7. **Idempotency**: Multiple calls with same input produce same result

### Agent Design

1. **YAML-First**: Never hardcode prompts, models, or behavior
2. **Tool Integration**: Load tools dynamically based on configuration
3. **Configuration Validation**: Validate required settings at startup
4. **Graceful Degradation**: Function without optional tools
5. **Memory Integration**: Support optional memory providers
6. **Approval Integration**: Respect HITL settings for sensitive operations

### Performance

1. **Tool Caching**: Cache expensive tool results when appropriate
2. **Async Operations**: Use async patterns for I/O operations
3. **Resource Management**: Clean up resources properly
4. **Monitoring**: Add metrics for tool usage and performance
5. **Batching**: Batch multiple operations when possible

### Security

1. **Input Validation**: Validate all inputs using Pydantic
2. **Sanitization**: Sanitize user inputs to prevent injection
3. **Approval Integration**: Use HITL for sensitive operations
4. **Error Information**: Don't expose sensitive information in errors
5. **Resource Limits**: Limit resource usage per operation

## Deployment Considerations

### Configuration

1. **Environment-Specific Configs**: Different configs for dev/staging/prod
2. **Secret Management**: Use environment variables for sensitive data
3. **Feature Flags**: Enable/disable features via configuration
4. **Validation**: Validate all required settings at startup

### Monitoring

1. **Logging**: Use structured logging with correlation IDs
2. **Metrics**: Track tool usage, execution time, success rates
3. **Health Checks**: Implement health endpoints for agent status
4. **Error Tracking**: Monitor and alert on error patterns
5. **Performance**: Track resource utilization and response times

## Migration Guide

When updating existing agents:

1. **Backward Compatibility**: Maintain existing configuration format
2. **Migration Path**: Provide clear upgrade instructions
3. **Deprecation Warnings**: Warn about deprecated settings
4. **Versioning**: Version configuration schemas
5. **Testing**: Test migration scenarios thoroughly

## Troubleshooting

### Common Issues

1. **Import Errors**: Check circular imports and missing dependencies
2. **Configuration Errors**: Validate YAML syntax and required fields
3. **Tool Registration**: Ensure tools are properly exported and imported
4. **Model Configuration**: Verify model names match available models
5. **Memory Issues**: Check memory provider configuration and permissions

### Debugging

1. **Logging**: Enable debug logging for detailed traces
2. **Configuration Dump**: Print loaded configuration for verification
3. **Tool Testing**: Test tools independently before integration
4. **Agent Testing**: Test agent creation in isolation
5. **Integration Testing**: Test agent within full fleet context

This guide provides the foundation for creating robust, well-integrated agents for AgenticFleet. For specific examples, refer to the existing agent implementations in the codebase.
