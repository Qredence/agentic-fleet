---
title: '[OPT-04] Integrate Agent Framework DevUI'
labels: ['enhancement', 'optimization', 'agent-framework', 'developer-experience']
---

## Priority Level

🟡 **Medium Priority** - Developer Productivity

## Overview

Integrate the official Agent Framework DevUI package to provide a visual interface for workflow debugging, agent testing, and interactive development.

## Current State

### Limitations

- CLI-only interface for testing
- No visual workflow representation
- Difficult to debug multi-agent interactions
- Cannot inspect agent internal state
- Manual log parsing for debugging

## Proposed Implementation

```python
# File: src/agenticfleet/cli/devui_server.py
from agent_framework_devui import start_devui
from agenticfleet.fleet import create_default_fleet
from agenticfleet.agents import (
    create_orchestrator_agent,
    create_researcher_agent,
    create_coder_agent,
    create_analyst_agent,
)

def start_development_ui(port=8000):
    """Start the Agent Framework DevUI server."""

    # Create workflow and agents
    workflow = create_default_fleet()
    agents = {
        "orchestrator": create_orchestrator_agent(),
        "researcher": create_researcher_agent(),
        "coder": create_coder_agent(),
        "analyst": create_analyst_agent(),
    }

    # Start DevUI server
    start_devui(
        workflow=workflow,
        agents=agents,
        port=port,
        title="AgenticFleet Development UI",
        config={
            "enable_workflow_viz": True,
            "enable_real_time_logs": True,
            "enable_agent_inspector": True,
        }
    )

    print(f"DevUI running at http://localhost:{port}")

# Add CLI command
# python -m agenticfleet.cli.devui_server
if __name__ == "__main__":
    start_development_ui()
```

## Benefits

### Developer Experience

- ✅ **Visual Workflow**: See agent interactions in real-time
- ✅ **Interactive Testing**: Test agents without writing code
- ✅ **Debug Inspector**: View agent state, context, and decisions
- ✅ **Faster Iteration**: Test changes immediately in UI
- ✅ **Better Onboarding**: New developers understand system visually

### Debugging

- ✅ **Trace Execution**: Follow workflow execution step-by-step
- ✅ **Inspect Messages**: See all agent messages and tool calls
- ✅ **View Context**: Inspect workflow context at any point
- ✅ **Error Analysis**: Visual error messages with stack traces

### Collaboration

- ✅ **Share Sessions**: Demo workflows to stakeholders
- ✅ **Record Sessions**: Save and replay workflows
- ✅ **Export Data**: Download logs and execution traces

## Features

### Workflow Visualization

- Graph view of agent connections
- Real-time execution highlighting
- Edge conditions displayed
- Execution path history

### Agent Inspector

- View agent configuration
- Inspect current state
- See tool availability
- Monitor token usage

### Interactive Testing

- Input panel for queries
- Real-time response streaming
- Manual approval controls
- Context editor

### Logs & Metrics

- Structured log viewer
- Performance metrics
- Token cost tracking
- Error aggregation

## Implementation Steps

### Phase 1: Basic Integration (Week 1)

- [ ] Install agent-framework-devui package
- [ ] Create devui_server.py module
- [ ] Wire up workflow and agents
- [ ] Add CLI command to start DevUI
- [ ] Test basic functionality

### Phase 2: Configuration (Week 1)

- [ ] Add DevUI configuration options
- [ ] Enable/disable features in config
- [ ] Add authentication (optional)
- [ ] Configure port and host
- [ ] Add custom branding

### Phase 3: Advanced Features (Week 2)

- [ ] Integrate with checkpointing
- [ ] Add session recording
- [ ] Enable workflow export
- [ ] Add custom visualizations
- [ ] Integrate approval UI

## Configuration

```yaml
# config/devui.yaml
devui:
  enabled: true
  port: 8000
  host: localhost
  authentication:
    enabled: false
    username: admin
    password_hash: <hash>
  features:
    workflow_visualization: true
    agent_inspector: true
    real_time_logs: true
    session_recording: true
    workflow_export: true
  branding:
    title: "AgenticFleet Development UI"
    logo_url: "./assets/logo.png"
    theme: dark  # light, dark, auto
```

## CLI Commands

```bash
# Start DevUI server
agentic-fleet devui start

# Start on custom port
agentic-fleet devui start --port 3000

# Start with auth enabled
agentic-fleet devui start --auth

# Open browser automatically
agentic-fleet devui start --open
```

## Testing Requirements

### Unit Tests

```python
def test_devui_starts():
    """Test DevUI server starts successfully."""
    server = start_development_ui(port=0)  # Random port
    assert server.is_running()
    server.stop()

def test_devui_workflow_loaded():
    """Test workflow is loaded in DevUI."""
    # Start DevUI
    # Check workflow is accessible
    # Verify agents are listed
```

### Integration Tests

- Test DevUI with real workflow
- Test agent inspection
- Test interactive execution
- Test session recording

### Manual Verification

1. Start DevUI server
2. Open <http://localhost:8000> in browser
3. Verify workflow graph displays
4. Test running a query through UI
5. Inspect agent details
6. Check logs panel

## Documentation Updates

### README.md

```markdown
## Development UI

AgenticFleet includes a visual development interface:

\`\`\`bash
# Start the DevUI
agentic-fleet devui start

# Open http://localhost:8000 in your browser
\`\`\`

Features:
- Visual workflow debugging
- Interactive agent testing
- Real-time execution monitoring
- Detailed logs and metrics
```

### New Guide: docs/guides/using-devui.md

```markdown
# Using the Development UI

The AgenticFleet DevUI provides a visual interface for developing
and debugging multi-agent workflows.

## Starting the UI

\`\`\`bash
agentic-fleet devui start
\`\`\`

Navigate to http://localhost:8000

## Features

### Workflow Visualization
- See all agents and their connections
- Watch execution flow in real-time
- Inspect edge conditions

### Agent Inspector
- View agent configuration
- Monitor tool usage
- Track token consumption

### Interactive Testing
- Submit queries through UI
- See real-time responses
- Approve actions visually

## Screenshots

[Include screenshots here]
```

## Estimated Effort

🔨 **Low** (3-5 days)

The agent-framework-devui package handles most functionality. We just need to integrate it with our workflow.

## Dependencies

- agent-framework-devui package
- WorkflowBuilder implementation (#OPT-01) preferred but not required
- Web browser for UI access

## Related Resources

- [DevUI Documentation](https://github.com/microsoft/agent-framework/tree/main/python/packages/devui)
- [DevUI Demo Video](https://www.youtube.com/watch?v=mOAaGY4WPvc)

## Success Criteria

- ✅ DevUI server starts without errors
- ✅ Workflow visualizes correctly
- ✅ Can execute queries through UI
- ✅ Agent inspector shows accurate data
- ✅ Logs display in real-time
- ✅ Documentation is complete with screenshots

---
Status: Ready for Implementation
Priority: Medium (Developer Productivity)
Related: #OPT-01, #OPT-03
