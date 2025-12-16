# Documentation Index

Welcome to AgenticFleet documentation. This index organizes documentation by audience to help you find what you need quickly.

**Current Version:** See `pyproject.toml` (`[project].version`).

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

1. **[Getting Started](users/getting-started.md)** - Your first task in 5 minutes
   - Step-by-step installation
   - "Hello World" tutorial with explanation
   - Progressive examples (simple → research → multi-step → parallel)
   - Understanding output and quality scores
2. **[Overview](users/overview.md)** - Deep dive into how AgenticFleet works
   - The problem AgenticFleet solves
   - The 5-phase pipeline explained with diagrams
   - Core concepts: Agents, Tools, Execution Modes
   - Real-world use cases with walkthroughs
3. **[User Guide](users/user-guide.md)** - Complete usage guide
   - Core concepts and features
   - Usage patterns and examples
   - Tool integration
   - Quality assessment
   - Monitoring and history
4. **[Frontend Guide](users/frontend.md)** - Web interface guide
   - Starting the frontend
   - Chat interface features
   - Workflow visualization
   - WebSocket protocol + message flow diagrams (new run, HITL, resume)
   - Configuration and development
5. **[Configuration](users/configuration.md)** - Configuration guide
   - All configuration options
   - Environment variables
   - Performance tuning
   - Migration guide
6. **[Performance Optimization](PERFORMANCE_OPTIMIZATION.md)** - Performance analysis and recommendations
   - Identified bottlenecks and solutions
   - Configuration caching and history indexing
   - Priority-ranked optimization opportunities
7. **[Profiling Guide](PROFILING_GUIDE.md)** - Performance monitoring utilities
   - Using `timed_operation` and `@profile_function`
   - Tracking operations with `PerformanceTracker`
   - Practical examples and best practices
8. **[Troubleshooting](users/troubleshooting.md)** - Common issues and solutions
   - Installation problems
   - Runtime issues
   - Performance tuning
   - Debugging tips
9. **[Self-Improvement](users/self-improvement.md)** - Automatic learning from history
   - How self-improvement works
   - Usage and configuration
   - Best practices
   - Statistics and monitoring

## For Developers

Developer-facing documentation for extending and contributing:

1. **[System Overview](developers/system-overview.md)** - Comprehensive technical guide
   - Purpose and scope of AgenticFleet
   - Complete system architecture with diagrams
   - Five-phase execution pipeline deep dive
   - Agent system (Factory, Roles, Tools, Handoffs)
   - DSPy integration (GEPA, Training, Self-improvement)
   - User interfaces (CLI, Python API, Web Frontend)
   - Observability (Events, OpenTelemetry, Middleware)
2. **[Architecture](developers/architecture.md)** - System architecture
   - Component overview
   - Full-stack architecture diagram (Web + CLI)
   - Data flow
   - Module structure
   - DSPy integration
3. **[Operations Runbook](developers/operations.md)** - Production operations
   - Backpressure / concurrency limits
   - Rate limiting guidance
   - Scaling considerations (WebSocket + state)
   - Production checklist
4. **[API Reference](developers/api-reference.md)** - API documentation
   - Core classes and methods
   - Type hints
   - Examples
   - Events and exceptions
5. **[Testing](developers/testing.md)** - Testing guide
   - Running tests
   - Writing tests
   - Test patterns
   - Debugging
6. **[Contributing](developers/contributing.md)** - Development guidelines
   - Code style
   - Commit conventions
   - Pull request process
   - Adding features
7. **[Code Quality](developers/code-quality.md)** - Code quality improvements
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
├── CHANGELOG.md                # Version history (symlink to root)
├── PERFORMANCE_OPTIMIZATION.md # Performance analysis
├── PROFILING_GUIDE.md          # Profiling utilities
├── users/                      # User-facing documentation
│   ├── getting-started.md
│   ├── overview.md             # What AgenticFleet is
│   ├── user-guide.md
│   ├── frontend.md             # Web interface guide
│   ├── configuration.md
│   ├── troubleshooting.md
│   └── self-improvement.md
├── developers/                 # Developer documentation
│   ├── system-overview.md      # Comprehensive technical guide (NEW)
│   ├── architecture.md
│   ├── api-reference.md
│   ├── testing.md
│   ├── contributing.md
│   ├── code-quality.md
│   ├── operations.md           # Production runbook
│   └── internals/             # Internal documentation
│       ├── tool-awareness.md
│       ├── handoffs.md
│       ├── AGENTS.md
│       ├── ARCHITECTURE.md
│       └── SYNERGY.md
├── guides/                     # Feature guides
│   ├── dspy-optimizer.md
│   ├── dspy-agent-framework-integration.md
│   ├── evaluation.md
│   ├── tracing.md
│   ├── logging-history.md
│   └── quick-reference.md
└── plans/                      # Implementation plans
    ├── current.md              # Active/completed work
    └── archive/                # Historical plans
```
