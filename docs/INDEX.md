# Documentation Index

Welcome to AgenticFleet documentation. This index organizes documentation by audience to help you find what you need quickly.

**Current Version:** 0.6.7

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet
make dev-setup

# Configure
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run
make dev
```

- **[Getting Started](users/getting-started.md)** - Full installation guide
- **[Quick Reference](guides/quick-reference.md)** - All commands at a glance
- **[Configuration](users/configuration.md)** - Configuration options

## For Users

User-facing documentation for using the framework:

1. **[Getting Started](users/getting-started.md)** - Installation, setup, and first steps
2. **[User Guide](users/user-guide.md)** - Complete usage guide
   - Core concepts and features
   - Usage patterns and examples
   - Tool integration
   - Quality assessment
   - Monitoring and history
3. **[Frontend Guide](users/frontend.md)** - Web interface guide
   - Starting the frontend
   - Chat interface features
   - Workflow visualization
   - Configuration and development
4. **[Configuration](users/configuration.md)** - Configuration guide
   - All configuration options
   - Environment variables
   - Performance tuning
   - Migration guide
5. **[Troubleshooting](users/troubleshooting.md)** - Common issues and solutions
   - Installation problems
   - Runtime issues
   - Performance tuning
   - Debugging tips
6. **[Self-Improvement](users/self-improvement.md)** - Automatic learning from history
   - How self-improvement works
   - Usage and configuration
   - Best practices
   - Statistics and monitoring

## For Developers

Developer-facing documentation for extending and contributing:

1. **[Architecture](developers/architecture.md)** - System architecture
   - Component overview
   - Data flow
   - Module structure
   - DSPy integration
2. **[API Reference](developers/api-reference.md)** - API documentation
   - Core classes and methods
   - Type hints
   - Examples
   - Events and exceptions
3. **[Testing](developers/testing.md)** - Testing guide
   - Running tests
   - Writing tests
   - Test patterns
   - Debugging
4. **[Contributing](developers/contributing.md)** - Development guidelines
   - Code style
   - Commit conventions
   - Pull request process
   - Adding features
5. **[Code Quality](developers/code-quality.md)** - Code quality improvements
   - Error handling enhancements
   - Type safety improvements
   - Caching optimizations
   - Code organization
   - Performance improvements

### Frontend Development

The React/Vite frontend lives in `src/frontend/`:

- **[Frontend AGENTS.md](../src/frontend/AGENTS.md)** - Frontend architecture and development guide
  - Directory structure
  - State management (hooks/useChat.ts)
  - WebSocket streaming
  - Component patterns
  - Testing

### Internal Documentation

Advanced topics for framework developers:

- **[Tool Awareness](developers/internals/tool-awareness.md)** - Tool registry system and web search detection
- **[Handoffs](developers/internals/handoffs.md)** - Structured agent handoff system

## Guides

Detailed guides for specific features and workflows:

1. **[DSPy Optimizer Guide](guides/dspy-optimizer.md)** - DSPy optimization
   - BootstrapFewShot vs GEPA
   - Training examples
   - Cache management
   - Best practices
2. **[Evaluation Guide](guides/evaluation.md)** - Evaluation framework
   - Standard evaluation
   - History-based evaluation
   - Metrics and baselines
   - Regression testing
3. **[Tracing Guide](guides/tracing.md)** - OpenTelemetry observability
   - Configuration
   - Viewing traces
   - Troubleshooting
4. **[Logging and History](guides/logging-history.md)** - Logging system
   - Four-phase logging
   - Execution history
   - Analysis tools
5. **[Quick Reference](guides/quick-reference.md)** - Quick command reference
   - Common commands
   - History analysis
   - Configuration snippets

## Project Information

- **[README.md](../README.md)** - Project overview and quick start
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and changes

## External Resources

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [DSPy Documentation](https://dspy.ai)
- [OpenAI API](https://platform.openai.com/docs)
- [Tavily Search API](https://tavily.com)

## Getting Help

1. Check [Troubleshooting](users/troubleshooting.md) for common issues
2. Review [User Guide](users/user-guide.md) for usage questions
3. See [API Reference](developers/api-reference.md) for implementation details
4. Check [Configuration](users/configuration.md) for config issues
5. Open an issue on GitHub for bugs or feature requests

## Documentation Structure

```
docs/
├── INDEX.md                    # This file
├── users/                      # User-facing documentation
│   ├── getting-started.md
│   ├── user-guide.md
│   ├── configuration.md
│   ├── troubleshooting.md
│   └── self-improvement.md
├── developers/                 # Developer documentation
│   ├── architecture.md
│   ├── api-reference.md
│   ├── testing.md
│   ├── contributing.md
│   └── internals/             # Internal documentation
│       ├── tool-awareness.md
│       └── handoffs.md
└── guides/                     # Feature guides
    ├── dspy-optimizer.md
    ├── evaluation.md
    ├── tracing.md
    ├── logging-history.md
    └── quick-reference.md
```
