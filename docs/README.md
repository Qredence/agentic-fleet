# AgenticFleet Documentation

**Version:** 0.5.3
**Last Updated:** October 20, 2025

Welcome to AgenticFleet! This documentation helps you get started quickly and master multi-agent orchestration with the Microsoft Agent Framework.

---

## 📚 Documentation Structure

### 🚀 Getting Started
Perfect for first-time users and quick setup.

- **[Installation](getting-started/installation.md)** – System requirements, installation steps, and environment setup
- **[Quick Start Guide](getting-started/quickstart.md)** – Your first workflow in 5 minutes
- **[Command Reference](getting-started/command-reference.md)** – Complete CLI and Makefile commands
- **[Configuration Guide](getting-started/configuration.md)** – Environment variables, YAML files, and agent settings

### 📖 User Guides
Step-by-step tutorials for common tasks.

- **[Working with Agents](guides/agents.md)** – Understanding and customizing the specialist agents
- **[Human-in-the-Loop (HITL)](guides/human-in-the-loop.md)** – Approval workflows and safety controls
- **[Checkpointing & Resume](guides/checkpointing.md)** – Save and restore workflow state
- **[Memory Management](guides/memory.md)** – Persistent context with Mem0 integration
- **[YAML Workflows](guides/yaml-workflows.md)** – Creating custom workflow definitions
- **[Web UI Integration](guides/web-ui.md)** – Using the React frontend and API endpoints

### 🔧 Advanced Topics
Deep dives for power users.

- **[Magentic Fleet Architecture](architecture/magentic-fleet.md)** – How the orchestration system works
- **[Observability & Tracing](features/observability.md)** – OpenTelemetry integration and debugging
- **[Tool Development](advanced/tool-development.md)** – Creating custom agent tools
- **[Workflow Customization](advanced/workflow-customization.md)** – Building your own orchestration patterns
- **[Performance Tuning](advanced/performance.md)** – Optimization strategies and best practices

### 📡 API Reference
Integration and API documentation.

- **[REST API](api/rest-api.md)** – HTTP endpoints for workflow execution
- **[SSE Streaming](api/sse-streaming.md)** – Server-Sent Events for real-time updates
- **[Reflection Endpoint](api/reflection-endpoint.md)** – Worker-reviewer pattern API
- **[Python API](api/python-api.md)** – Programmatic usage and SDK reference

### 🎯 Features
Detailed feature documentation.

- **[Magentic Fleet](features/magentic-fleet.md)** – Manager/executor orchestration pattern
- **[Checkpointing System](features/checkpointing-summary.md)** – State persistence and recovery
- **[HITL Implementation](features/hitl-implementation-summary.md)** – Approval system design
- **[Observability](features/observability.md)** – Tracing and monitoring
- **[Web HITL](features/web-hitl-integration.md)** – Browser-based approval interface
- **[Workflow-as-Agent](features/workflow-as-agent-integration.md)** – Composable workflow patterns

### 🛠️ Development
Contributing and development workflows.

- **[Developer Setup](operations/developer-environment.md)** – Local development environment
- **[Testing Guide](development/testing.md)** – Writing and running tests
- **[Contributing Guidelines](../CONTRIBUTING.md)** – How to contribute to AgenticFleet
- **[Code Standards](operations/repository-guidelines.md)** – Coding conventions and review practices
- **[CI/CD Pipeline](operations/github-workflows-overview.md)** – GitHub Actions workflows

### 🔍 Troubleshooting
Common issues and solutions.

- **[Troubleshooting Guide](runbooks/troubleshooting.md)** – Common problems and fixes
- **[FAQ](troubleshooting/faq.md)** – Frequently asked questions
- **[Known Issues](troubleshooting/known-issues.md)** – Current limitations and workarounds
- **[Migration Guides](migrations/)** – Upgrading between versions

### 📋 Reference
Additional resources and information.

- **[Agent Catalog](AGENTS.md)** – Complete list of available agents and their capabilities
- **[Changelog](../CHANGELOG.md)** – Version history and release notes
- **[Release Notes](releases/)** – Detailed release documentation
- **[Glossary](reference/glossary.md)** – Terms and concepts
- **[Architecture Diagrams](architecture/)** – System architecture documentation

---

## Quick Navigation

### I want to

| Goal | Start Here |
|------|------------|
| **Install AgenticFleet** | [Installation Guide](getting-started/installation.md) |
| **Run my first workflow** | [Quick Start](getting-started/quickstart.md) |
| **Understand the agents** | [Agent Catalog](AGENTS.md) + [Working with Agents](guides/agents.md) |
| **Add approval gates** | [HITL Guide](guides/human-in-the-loop.md) |
| **Save workflow progress** | [Checkpointing Guide](guides/checkpointing.md) |
| **Enable memory/context** | [Memory Management](guides/memory.md) |
| **Create custom tools** | [Tool Development](advanced/tool-development.md) |
| **Use the REST API** | [REST API Reference](api/rest-api.md) |
| **Deploy to production** | [Deployment Guide](deployment/production.md) |
| **Troubleshoot issues** | [Troubleshooting](runbooks/troubleshooting.md) |
| **Contribute code** | [Contributing Guidelines](../CONTRIBUTING.md) |

---

## 🆘 Getting Help

- **Issues:** Found a bug? [Open an issue](https://github.com/Qredence/agentic-fleet/issues)
- **Discussions:** Questions? [Start a discussion](https://github.com/Qredence/agentic-fleet/discussions)
- **Email:** Contact us at <contact@qredence.ai>

---

## 📝 Documentation Conventions

Throughout this documentation:

- 💡 **Tips** provide helpful hints and best practices
- ⚠️ **Warnings** highlight potential pitfalls
- 📌 **Notes** offer additional context
- 🔒 **Security** notes indicate security considerations

Code examples use:
- `bash` for shell commands
- `python` for Python code
- `yaml` for configuration files

---

## 🤝 Contributing to Documentation

We welcome documentation improvements! To contribute:

1. Edit files in the `docs/` directory
2. Use kebab-case for filenames (e.g., `my-guide.md`)
3. Update this README when adding new pages
4. Follow the existing structure and style
5. Test links and code examples

See [Contributing Guidelines](../CONTRIBUTING.md) for more details.

---

**Last updated:** October 20, 2025
**Version:** 0.5.3
