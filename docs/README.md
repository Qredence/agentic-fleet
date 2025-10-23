# AgenticFleet Documentation

Welcome to the comprehensive documentation for AgenticFleet, a multi-agent orchestration system built on Microsoft Agent Framework's Magentic One pattern.

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation overview
├── api/
│   └── reference.md           # Complete API documentation
├── architecture/
│   └── decision-records.md  # Architectural Decision Records (ADRs)
├── development/
│   └── agent-development.md   # Agent development guide
├── troubleshooting/
│   └── troubleshooting-guide.md  # Common issues and solutions
└── Project_Architecture_Blueprint.md  # High-level system architecture
```

## Quick Navigation

### For Users

- **[Getting Started](../README.md#getting-started)** - Installation and first run
- **[API Reference](./api/reference.md)** - Complete REST API and SSE documentation
- **[Troubleshooting](./troubleshooting/troubleshooting-guide.md)** - Solutions to common issues

### For Developers

- **[Agent Development Guide](./development/agent-development.md)** - Creating new agents and tools
- **[Architectural Decision Records](./architecture/decision-records.md)** - ADRs and design rationale
- **[Project Architecture](./Project_Architecture_Blueprint.md)** - High-level system design

### For System Administrators

- **[API Documentation](./api/reference.md#deployment)** - Deployment and configuration
- **[Troubleshooting Guide](./troubleshooting/troubleshooting-guide.md#deployment-issues)** - Production deployment issues

## Key Documentation Features

### 📚 Comprehensive Coverage

- **Complete API Reference**: REST endpoints, SSE streaming, authentication, error handling
- **Agent Development Guide**: Step-by-step instructions for creating agents and tools
- **Architecture Decisions**: Detailed ADRs explaining design choices and alternatives
- **Troubleshooting Guide**: Systematic solutions for common problems across all components

### 🔧 Practical Examples

- **Code Samples**: Working examples for API clients, tool development, configuration
- **Configuration Examples**: Complete YAML configurations for different scenarios
- **Integration Patterns**: Best practices for frontend, backend, and agent integration
- **Debugging Techniques**: Systematic approaches to identifying and resolving issues

### 🚀 Production Ready

- **Security Considerations**: Authentication, authorization, input validation, CORS configuration
- **Performance Optimization**: Checkpointing, caching, resource management
- **Monitoring and Observability**: OpenTelemetry, logging, metrics collection
- **Deployment Strategies**: Containerization, environment management, CI/CD integration

### 📖 Well-Organized Structure

- **Logical Grouping**: Related topics grouped together for easy navigation
- **Cross-References**: Extensive linking between related documentation sections
- **Progressive Disclosure**: From user basics to advanced developer topics
- **Searchable Content**: Clear headings, consistent terminology, comprehensive indexing

## Documentation Standards

### Writing Style

- **Clear Headings**: Hierarchical structure with descriptive section titles
- **Code Blocks**: Syntax-highlighted, properly formatted examples
- **Consistent Terminology**: Standardized terms and definitions throughout
- **Practical Examples**: Real-world scenarios and working code samples
- **Error Messages**: Clear, actionable error descriptions with solutions

### Version Control

- **Current Version**: All documentation reflects AgenticFleet v0.5.4
- **Version-Specific Notes**: Clear indication of version-specific features or changes
- **Migration Guides**: Step-by-step instructions for version upgrades
- **Backward Compatibility**: Clear marking of deprecated features and alternatives

### Quality Assurance

- **Validation**: All code examples tested and verified to work
- **Completeness**: Coverage of all documented features and configurations
- **Accuracy**: Regular reviews and updates to match current implementation
- **Accessibility**: Documentation usable by developers with varying expertise levels

## Contributing to Documentation

### How to Contribute

1. **Identify Gaps**: Look for missing topics or unclear explanations
2. **Create Issues**: Report documentation bugs or suggest improvements
3. **Submit Changes**: Follow the contribution guidelines in the main repository
4. **Maintain Standards**: Keep consistency with existing documentation style

### Review Process

1. **Technical Review**: Verify technical accuracy and code examples
2. **User Experience Review**: Ensure clarity and usefulness for target audience
3. **Completeness Check**: Confirm all topics are adequately covered
4. **Link Verification**: Test all internal and external links

## Quick Reference

### Essential Commands

```bash
# Development
uv run agentic-fleet  # Full stack (frontend + backend)
uv run fleet          # CLI/REPL only
make dev              # Same as agentic-fleet
make test-config      # Validate configuration
make test             # Run test suite

# Individual Components
make haxui-server     # Backend only
make frontend-dev     # Frontend only

# Quality Assurance
make check            # All quality checks
make lint             # Code linting
make format           # Code formatting
```

### Configuration Files

- **[Workflow Configuration](../src/agenticfleet/config/workflow.yaml)**: Global orchestration settings
- **[Agent Configurations](../src/agenticfleet/agents/*/config.yaml)**: Per-agent configuration
- **[Project Configuration](../pyproject.toml)**: Dependencies and tool settings
- **[Environment Variables](.env.example)**: Available environment variables

### Key Architectural Components

- **[Magentic Orchestrator](../src/agenticfleet/fleet/magentic_fleet.py)**: Main coordination logic
- **[Agent Factory Pattern](../src/agenticfleet/agents/*/agent.py)**: Agent creation and configuration
- **[HITL Approval System](../src/agenticfleet/core/approval.py)**: Human-in-the-loop implementation
- **[SSE Streaming](../src/agenticfleet/haxui/sse_events.py)**: Real-time communication
- **[Checkpointing System](../src/agenticfleet/core/checkpoints.py)**: State persistence

## Getting Help

If you need help with AgenticFleet:

1. **[Check Existing Documentation]**: Look through these docs and the main README
2. **[Search Issues](https://github.com/Qredence/agentic-fleet/issues)**: See if your problem is already documented
3. **[Ask Questions](https://github.com/Qredence/agentic-fleet/discussions)**: Start a discussion for clarification
4. **[Report Issues](https://github.com/Qredence/agentic-fleet/issues)**: Report bugs or documentation gaps

## Documentation Maintenance

This documentation is actively maintained to reflect:

- **New Features**: As they are implemented in AgenticFleet
- **API Changes**: As endpoints are added or modified
- **Configuration Updates**: As new options become available
- **Best Practices**: As they emerge from community usage
- **Security Updates**: As new security considerations arise

For the latest documentation updates, check the [Git history](https://github.com/Qredence/agentic-fleet/commits/main/docs) of this documentation directory.

---

_This documentation covers everything you need to successfully develop with, deploy, and troubleshoot AgenticFleet. Whether you're a user wanting to get started, a developer extending the system, or a system administrator managing production deployments, you'll find comprehensive guides and references here._
