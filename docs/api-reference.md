# API Reference

## Core Classes

### MagenticOneCoderAgent

The primary coding agent responsible for code generation and analysis.

```python
class MagenticOneCoderAgent:
    """
    A specialized agent for code-related tasks.
    
    Attributes:
        model_client: The Azure OpenAI client for API communication
        system_prompt: Custom system prompt for the agent
        tools: List of available coding tools
    """
```

#### Key Methods

- `analyze_code(code: str) -> CodeAnalysis`: Analyzes code structure and quality
- `generate_code(spec: str) -> str`: Generates code based on specifications
- `review_pr(diff: str) -> PRReview`: Reviews code changes and provides feedback

### MultimodalWebSurfer

Agent for web content analysis and data extraction.

```python
class MultimodalWebSurfer:
    """
    Web surfing agent with multimodal capabilities.
    
    Attributes:
        base_url: Starting point for web searches
        max_depth: Maximum depth for recursive searches
    """
```

#### Key Methods

- `search(query: str) -> List[SearchResult]`: Performs web searches
- `extract_content(url: str) -> WebContent`: Extracts content from URLs
- `analyze_page(url: str) -> PageAnalysis`: Analyzes webpage structure

### FileSurfer

Agent for file system operations and content analysis.

```python
class FileSurfer:
    """
    File system navigation and analysis agent.
    
    Attributes:
        root_dir: Base directory for file operations
        allowed_extensions: List of processable file types
    """
```

#### Key Methods

- `scan_directory(path: str) -> FileTree`: Scans directory structure
- `analyze_file(path: str) -> FileAnalysis`: Analyzes file content
- `search_files(pattern: str) -> List[str]`: Searches for files matching pattern

## Message Types

### AgentMessage

```python
class AgentMessage:
    """
    Represents a message in the agent communication system.
    
    Attributes:
        content: Message content
        agent_name: Name of the sending agent
        timestamp: Message creation time
        message_type: Type of message (code, text, error, etc.)
    """
```

### CodeBlock

```python
class CodeBlock:
    """
    Represents a code block in agent communications.
    
    Attributes:
        code: The actual code content
        language: Programming language
        metadata: Additional code metadata
    """
```

## Configuration Options

### AgentConfig

```python
class AgentConfig:
    """
    Configuration settings for agent behavior.
    
    Attributes:
        max_rounds: Maximum conversation rounds
        max_time: Maximum task time in minutes
        max_stalls: Maximum allowed stalls
    """
```

## Error Handling

### AgentError

```python
class AgentError(Exception):
    """
    Base class for agent-related errors.
    
    Attributes:
        message: Error description
        agent_name: Name of the agent raising the error
        error_code: Unique error identifier
    """
```

## Events

### AgentEvent

```python
class AgentEvent:
    """
    Represents an event in the agent system.
    
    Attributes:
        event_type: Type of event
        data: Event data
        timestamp: Event occurrence time
    """
```
