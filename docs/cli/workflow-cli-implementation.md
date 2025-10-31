# Workflow CLI Implementation Summary

## Overview

Created an interactive CLI tool (`workflow_cli.py`) for testing and running AgenticFleet workflows. The tool provides a rich terminal interface for exploring workflows, viewing configurations, and executing workflows with real-time streaming output.

## Implementation Details

### File Created

**`src/agenticfleet/cli/workflow_cli.py`** (325 lines)

### Key Features

1. **Interactive Menu System**
   - Menu-driven interface with 5 options
   - List workflows, view configs, run workflows
   - Uses Rich library for beautiful terminal UI

2. **Workflow Discovery**
   - Lists all available workflows from YAML configuration
   - Displays workflow metadata (ID, name, description, factory)
   - Uses `WorkflowFactory` to read from `magentic_fleet.yaml`

3. **Configuration Viewer**
   - Detailed workflow configuration display
   - Shows manager settings (model, limits, temperature, tokens)
   - Shows agent configurations (models, tools, instructions)
   - Displays instruction previews

4. **Interactive Execution**
   - Runs workflows with real-time streaming output
   - Processes events as they arrive (deltas, messages, results)
   - Shows manager coordination messages
   - Displays agent outputs with proper formatting
   - Displays final results with markdown rendering

5. **Error Handling**
   - Graceful error handling for missing workflows
   - Keyboard interrupt handling
   - Clean exit on errors
   - User-friendly error messages

### Event Processing

The CLI processes workflow events in real-time:

- **MagenticOrchestratorMessageEvent** - Manager planning/coordination messages
- **MagenticAgentDeltaEvent** - Streaming agent output (real-time)
- **MagenticAgentMessageEvent** - Complete agent responses
- **MagenticFinalResultEvent** - Final synthesized result
- **WorkflowOutputEvent** - Structured workflow output

### Rich Terminal UI

Uses Rich library for enhanced terminal experience:

- **Tables** - Formatted workflow listings and configurations
- **Panels** - Grouped information display
- **Markdown** - Formatted text rendering
- **Colors** - Color-coded output (cyan for info, green for success, red for errors)
- **Progress Indicators** - Visual feedback during execution

### Script Entry Point

Added to `pyproject.toml`:

```toml
[project.scripts]
workflow = "agenticfleet.cli.workflow_cli:main"
```

Usage:

```bash
uv run workflow
```

## Architecture

### Class Structure

- **WorkflowCLI** - Main CLI class
  - `display_banner()` - Welcome banner
  - `list_workflows()` - Get available workflows
  - `display_workflows_table()` - Format and display workflows
  - `display_workflow_config()` - Show detailed configuration
  - `run_workflow_interactive()` - Execute workflow with streaming
  - `interactive_menu()` - Main menu loop
  - `run()` - Entry point

### Integration Points

1. **WorkflowFactory** - Creates workflows from YAML config
2. **Event Handlers** - Uses handlers from `workflow.py` for logging
3. **Rich Console** - Terminal output formatting
4. **Async/Await** - Handles async workflow execution

## Usage Examples

### Basic Usage

```bash
# Run interactive CLI
uv run workflow

# Direct Python execution
uv run python -m agentic_fleet.cli.app
```

### Interactive Flow

1. User runs `uv run workflow`
2. Banner displayed
3. Menu shown with 5 options
4. User selects option (1-5)
5. Action executed (list/view/run)
6. Results displayed with rich formatting
7. Menu loop continues until exit

### Example Session

```
╔═══════════════════════════════════════════════════════════════╗
║          AgenticFleet - Interactive Workflow CLI               ║
║          Test and Run Multi-Agent Workflows                    ║
╚═══════════════════════════════════════════════════════════════╝

Main Menu
1. List available workflows
2. View workflow configuration
3. Run workflow interactively
4. Run workflow with custom input
5. Exit

Select an option [1]: 1

┌─────────────────────────────────────────────────────────────┐
│                     Available Workflows                     │
├─────────────┬──────────────────────────┬──────────────────┤
│ ID          │ Name                     │ Factory           │
├─────────────┼──────────────────────────┼──────────────────┤
│ collaboration│ Collaboration Workflow   │ create_collabora...│
│ magentic_fleet│ Magentic Fleet Workflow│ create_magentic...│
└─────────────┴──────────────────────────┴──────────────────┘
```

## Benefits

1. **Developer Experience** - Easy testing of workflows without frontend
2. **Debugging** - Real-time event inspection
3. **Documentation** - Configuration viewer helps understand workflows
4. **Accessibility** - Terminal-based, works over SSH
5. **Integration** - Fits into existing CLI ecosystem

## Testing Recommendations

1. **Manual Testing**
   - Run `uv run workflow` and test all menu options
   - Verify workflow listing works
   - Test configuration viewing
   - Execute workflows with different inputs
   - Test error handling (invalid workflow IDs, etc.)

2. **Automated Testing** (Future)
   - Unit tests for WorkflowCLI class methods
   - Integration tests for workflow execution
   - Mock workflow factory for testing
   - Test error scenarios

## Dependencies

- `rich` - Already in dependencies (v13.7.0+)
- `asyncio` - Standard library
- `logging` - Standard library
- `WorkflowFactory` - From `agenticfleet.api.workflow_factory`
- Event handlers - From `agenticfleet.workflow`

## Future Enhancements

1. **Checkpoint Support** - Resume from checkpoints
2. **History Viewing** - View past executions
3. **Export Results** - Save execution results to file
4. **Batch Mode** - Run multiple workflows from file
5. **Performance Metrics** - Display execution time, token usage
6. **Configuration Editing** - Modify workflow configs interactively

## Documentation

Created `docs/cli/workflow-cli.md` with:

- Usage instructions
- Feature descriptions
- Examples
- Configuration details
- Error handling guide

## Integration with Existing Tools

- `uv run fleet` - Main CLI/REPL
- `uv run workflow` - New interactive workflow tool
- `uv run agentic-fleet` - Full stack (frontend + backend)
- `uv run dynamic-fleet` - Dynamic workflow mode

All tools work together in the AgenticFleet ecosystem.
