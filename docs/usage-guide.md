# Usage Guide

## Getting Started

### Basic Usage

1. Start the server:
```bash
agenticfleet start
```

2. Access the web interface at `http://localhost:8001`

3. Start a conversation by typing your task or question

### Command Line Interface

AgenticFleet provides a CLI for common operations:

```bash
# Start server with default settings
agenticfleet start

# Start without OAuth
agenticfleet start --no-oauth

# Start with custom port
agenticfleet start --port 8080

# Start with debug logging
agenticfleet start --debug
```

## Web Interface Features

### Chat Interface

- **Code Highlighting**: Automatic syntax highlighting for code blocks
- **Markdown Support**: Rich text formatting using Markdown
- **File Upload**: Drag and drop file upload support
- **Progress Indicators**: Real-time task progress visualization

### Agent Interaction

1. **Task Submission**
   - Type your task in natural language
   - Attach relevant files if needed
   - Submit using Enter or the send button

2. **Response Interpretation**
   - Agent responses are color-coded
   - Code blocks are automatically formatted
   - File operations are clearly indicated
   - Web search results are linked

3. **Task Control**
   - Pause/Resume task execution
   - Cancel ongoing tasks
   - Save conversation history

## Advanced Features

### OAuth Authentication

Enable OAuth for secure access:

1. Configure OAuth variables in `.env`
2. Start server with OAuth enabled
3. Users will be redirected to login

### Custom Agent Configuration

Modify agent behavior in the settings panel:

- Adjust conversation rounds
- Set time limits
- Configure web search settings
- Customize agent system prompts

### File Operations

The FileSurfer agent supports:

- Directory scanning
- File content analysis
- Pattern matching
- Content extraction

### Web Integration

The WebSurfer agent provides:

- Web search capabilities
- Content extraction
- URL processing
- Data analysis

## Best Practices

1. **Task Description**
   - Be specific about requirements
   - Provide context when needed
   - Break complex tasks into steps

2. **Code Generation**
   - Specify language preferences
   - Include error handling requirements
   - Mention performance constraints

3. **File Management**
   - Organize files logically
   - Use consistent naming
   - Keep paths relative when possible

4. **Error Handling**
   - Monitor agent progress
   - Review error messages
   - Adjust settings if needed

## Troubleshooting

Common issues and solutions:

1. **Connection Issues**
   - Check server status
   - Verify port availability
   - Review OAuth configuration

2. **Performance Problems**
   - Reduce max_rounds setting
   - Limit concurrent tasks
   - Clear conversation history

3. **Authentication Errors**
   - Verify OAuth credentials
   - Check redirect URLs
   - Review scope settings
