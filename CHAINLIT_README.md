# AgenticFleet - Chainlit Interface

This document provides instructions for running the AgenticFleet application with the Chainlit UI interface.

## Setup

The Chainlit integration requires specific dependencies. We've prepared a script to help you set up everything correctly.

### Prerequisites

- Python 3.10+ installed
- Virtual environment already created (`.venv` directory in project root)

### Installation

1. Make sure your virtual environment is activated:
   ```bash
   source .venv/bin/activate
   ```

2. Run the provided setup script:
   ```bash
   ./scripts/setup_chainlit.sh
   ```

   This script will:
   - Install Chainlit v2.4.4.00
   - Resolve dependency conflicts (especially numpy version issues)
   - Install necessary AutoGen components

### Running the Application

After successful setup, you can run the application in one of two ways:

**Method 1 (Recommended)**: Use the chainlit command directly:
```bash
chainlit run src/agentic_fleet/chainlit_app.py
```

**Method 2**: Use the Python module:
```bash
python -m src.agentic_fleet.chainlit_app
```

The application will start a local web server. By default, it will be accessible at:
http://localhost:8080

If you encounter any issues with the chainlit command not being found, ensure you've run the setup script:
```bash
./scripts/setup_chainlit.sh
```

## Features

### Chat Profiles

The application provides two chat profiles:

1. **MagenticFleet** (Default)
   - Uses TaskList elements for visualizing plans and execution
   - Shows detailed step-by-step task progress
   - Has standard reset agent functionality

2. **MCP Focus**
   - Uses Canvas-like Custom elements for rendering
   - Provides rich code rendering capabilities
   - Includes additional "List MCP Tools" functionality
   - Optimized for Model Context Protocol (MCP) interactions
   - Supports connecting to MCP servers via stdio or SSE protocols

### UI Components

- **TaskList/Task**: Shows task execution progress
- **Custom Elements**: Renders rich content like articles and code
- **Actions**: Profile-specific buttons for additional functionality

### Content Types

The application supports multiple content types:
- Text (with streaming)
- Code (with syntax highlighting)
- Images
- Custom elements (articles, rich code)
- Error messages

### MCP Support

The application includes full support for the Model Context Protocol (MCP):

1. **Connecting to MCP Servers**
   - Click the settings gear icon in the UI
   - Select "Add MCP" from the menu
   - Choose connection type (stdio or SSE)
   - For stdio: Enter a name and command (e.g., "math-tool", "npx @modelcontextprotocol/math-tool")
   - For SSE: Enter a name and URL endpoint

2. **Using MCP Tools**
   - After connecting, click the "List MCP Tools" button in the MCP Focus profile
   - Tools will be listed with their descriptions
   - You can ask the AI to use these tools in your conversation

3. **Required Setup**
   - MCP support requires additional packages (installed via setup_chainlit.sh)
   - The .chainlit/config.toml file has MCP features enabled by default

## Development

### Key Files

- `src/agentic_fleet/chainlit_app.py`: Main entry point
- `src/agentic_fleet/mcp_handlers.py`: MCP connection handlers
- `src/agentic_fleet/ui/message_handler.py`: Message processing
- `src/agentic_fleet/ui/task_manager.py`: Task management
- `src/agentic_fleet/message_processing/__init__.py`: Content processing
- `public/custom_renderer.js`: Custom frontend rendering
- `chainlit.md`: Chat profiles configuration
- `.chainlit/config.toml`: Chainlit configuration including MCP settings

### Adding New Features

When extending the application:

1. **New Content Types**: Add detection in `message_processing/__init__.py`
2. **UI Components**: Update `message_handler.py` to handle rendering
3. **Profile Actions**: Add to profile initialization in `chainlit_app.py`

## Troubleshooting

### Common Issues

1. **Missing Chainlit Command**:
   - Make sure you've run the setup script
   - Verify your virtual environment is activated

2. **Dependency Conflicts**:
   - The setup script should resolve numpy conflicts
   - If issues persist, try `pip install numpy==1.26.0` explicitly

3. **MCP Connection Issues**:
   - For stdio connections, verify the command exists and is executable
   - For SSE connections, check network connectivity to the endpoint
   - Check that MCP is enabled in .chainlit/config.toml

4. **Rendering Issues**:
   - Verify `public/custom_renderer.js` is loaded correctly
   - Check browser console for errors

### Getting Help

If you encounter issues, check:
- Application logs
- Browser console for frontend errors
- The error messages in the UI
