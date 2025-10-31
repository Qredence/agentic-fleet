# Workflow CLI - Interactive Testing and Execution Tool

## Overview

The Workflow CLI provides an interactive terminal interface for testing and running AgenticFleet workflows. It offers a rich, user-friendly experience for exploring available workflows, viewing configurations, and executing workflows with real-time streaming output.

## Features

- 📋 **List Workflows** - View all available workflows from YAML configuration
- 🔍 **View Configuration** - Inspect detailed workflow settings including agents, models, and instructions
- ▶️ **Interactive Execution** - Run workflows with real-time streaming output
- 🎨 **Rich Terminal UI** - Beautiful formatting with colors, tables, and panels
- ⚡ **Real-time Streaming** - See agent responses as they're generated

## Usage

### Basic Usage

```bash
# Run the interactive CLI
uv run workflow

# Or directly with the module path
uv run python -m agentic_fleet.cli.app
```

### Interactive Menu

The CLI provides a menu-driven interface:

1. **List available workflows** - Shows all configured workflows with their details
2. **View workflow configuration** - Display detailed configuration for a specific workflow
3. **Run workflow interactively** - Execute a workflow with prompted input
4. **Run workflow with custom input** - Execute with your own input text
5. **Exit** - Quit the CLI

## Workflow Events

The CLI displays various workflow events in real-time:

- **Manager Messages** - Planning and coordination messages from the orchestrator
- **Agent Deltas** - Streaming text output from agents (real-time)
- **Agent Messages** - Complete agent responses
- **Final Results** - Synthesized final output from the workflow
- **Workflow Output** - Structured data output

## Configuration

The CLI reads workflows from `src/agenticfleet/magentic_fleet.yaml` by default. It uses the `WorkflowFactory` to create workflows from YAML configuration.

## Keyboard Shortcuts

- `Ctrl+C` - Interrupt workflow execution
- `Ctrl+D` - Exit the CLI
- `↑` / `↓` - Navigate menu options (when using prompt)

## Requirements

- Python 3.12+
- `rich` library (already included in dependencies)
- Valid YAML workflow configuration
- OpenAI API key set in environment (`OPENAI_API_KEY`)

## Integration with Existing CLI

The workflow CLI integrates with the existing AgenticFleet CLI ecosystem:

- `uv run fleet` - Main CLI/REPL interface
- `uv run workflow` - Interactive workflow testing tool (this CLI)
- `uv run agentic-fleet` - Full stack (frontend + backend)

## Error Handling

The CLI handles various error scenarios gracefully:

- Missing workflows → Shows friendly error message
- Invalid workflow IDs → Prompts for valid selection
- Execution errors → Displays error details and continues
- Keyboard interrupts → Cleanly exits with confirmation
