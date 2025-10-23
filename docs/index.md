# AgenticFleet Documentation Index

Complete documentation for AgenticFleet v0.5.4 - a multi-agent orchestration system built on Microsoft Agent Framework's Magentic One pattern.

## 📖 Documentation Overview

This directory contains comprehensive documentation for AgenticFleet, organized by audience and purpose:

### 🏗️ Architecture Documentation

- **[Project Architecture Blueprint](./Project_Architecture_Blueprint.md)**
  - High-level system design and component interaction
  - Technology stack analysis and architectural patterns
  - Data flow and service communication
  - Deployment and scaling considerations

- **[Architectural Decision Records](./architecture/decision-records.md)**
  - ADRs (Architecture Decision Records) for major design choices
  - Historical decisions with context and alternatives considered
  - Decision-making process and implementation rationale

### 🔧 Development Documentation

- **[Agent Development Guide](./development/agent-development.md)**
  - Complete guide for creating new agents and tools
  - Factory patterns and configuration management
  - Testing strategies and best practices
  - Tool development with Pydantic models

### 📡 API Documentation

- **[API Reference](./api/reference.md)**
  - RESTful API endpoints and request/response formats
  - Server-Sent Events (SSE) streaming documentation
  - Authentication, authorization, and error handling
  - Client SDK examples and integration patterns

### 🚨 Troubleshooting Documentation

- **[Troubleshooting Guide](./troubleshooting/troubleshooting-guide.md)**
  - Systematic solutions to common issues
  - Installation, configuration, and deployment problems
  - Performance and debugging techniques
  - Error resolution and recovery procedures

## 🎯 Quick Navigation

### For New Users

1. **[Read Main README](../README.md)** - Installation and quick start guide
2. **[API Basics](./api/reference.md#overview)** - Understand how to use the system
3. **[Common Issues](./troubleshooting/troubleshooting-guide.md)** - Get help with problems

### For Developers

1. **[Agent Development](./development/agent-development.md)** - Learn to extend the system
2. **[Architecture](./architecture/decision-records.md)** - Understand design decisions
3. **[API Integration](./api/reference.md)** - Integrate with the backend
4. **[Testing](../README.md#testing)** - Run and extend tests

### For System Administrators

1. **[Deployment](./troubleshooting/troubleshooting-guide.md#deployment-issues)** - Production deployment
2. **[Configuration](./api/reference.md#configuration)** - System configuration
3. **[Monitoring](./api/reference.md#monitoring-and-observability)** - System observability
4. **[Security](./api/reference.md#security-considerations)** - Security best practices

## 📚 Key Documentation Features

### ✅ Comprehensive Coverage

- **Complete API Documentation**: All endpoints, event types, error conditions
- **Development Patterns**: Agent factories, tool development, configuration management
- **Architecture Decisions**: Historical records with complete decision context
- **Troubleshooting Matrix**: Systematic problem-solving approach

### 🔧 Practical Examples

- **Working Code Examples**: All documentation includes tested, copy-paste ready code
- **Configuration Samples**: Complete YAML and environment variable examples
- **Integration Patterns**: Real-world usage patterns and best practices
- **Client SDK Examples**: Python and TypeScript client implementations

### 🚀 Production Ready

- **Security Guidelines**: Authentication, authorization, input validation
- **Performance Optimization**: Checkpointing, caching, resource management
- **Monitoring Setup**: OpenTelemetry, logging, metrics, health checks
- **Deployment Strategies**: Containerization, environment management, scaling

### 🔄 Living Documentation

This documentation evolves with AgenticFleet:

- **Version-Specific**: All content reflects current v0.5.4 features
- **Community Contributions**: Regular updates from community feedback and usage
- **Change Management**: Clear documentation of breaking changes and migrations
- **Quality Assured**: Regular reviews ensure accuracy and completeness

## 📋 Documentation Quality Standards

### Writing Guidelines

- **Clear Structure**: Hierarchical organization with logical content flow
- **Consistent Terminology**: Standardized terms and definitions throughout
- **Code Quality**: All examples tested, formatted, and well-documented
- **Practical Focus**: Real-world scenarios and solutions over theoretical discussions

### Technical Standards

- **Accuracy Verified**: All technical content validated against current implementation
- **Completeness**: Comprehensive coverage of all features and configurations
- **Cross-References**: Extensive linking between related topics
- **Version Alignment**: Documentation matches actual implementation in v0.5.4

### Maintenance Process

1. **Regular Reviews**: Documentation accuracy checked against codebase changes
2. **User Feedback**: Community input incorporated through issues and discussions
3. **Testing Examples**: Code examples validated with each release
4. **Version Updates**: Documentation versioned alongside software releases

## 🔍 Finding Information

### Search Strategy

1. **Start with Index**: Use this document to identify relevant documentation
2. **Use Headings**: Navigate to specific sections using the structure above
3. **Follow Links**: Cross-references provide deeper exploration of topics
4. **Check Context**: Related documentation sections linked for comprehensive understanding

### Key Topics

- **Agent Configuration**: YAML-based agent setup and tool integration
- **Magentic Workflow**: PLAN → EVALUATE → ACT → OBSERVE cycle
- **HITL System**: Human-in-the-loop approval for sensitive operations
- **SSE Streaming**: Real-time event streaming to frontend
- **Checkpointing**: State persistence and recovery mechanisms
- **API Integration**: REST endpoints and client SDK usage
- **Tool Development**: Creating agent tools with Pydantic models

## 🚀 Getting Started Quickly

### 5-Minute Quick Start

```bash
# 1. Install AgenticFleet
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet
make install

# 2. Configure Environment
cp .env.example .env
# Edit .env to add OPENAI_API_KEY=sk-your-key

# 3. Start Development Server
make dev

# 4. Access Web Interface
# Open http://localhost:5173 in your browser

# 5. Read Documentation
# Start with ../README.md for detailed guidance
```

### Essential Reading Order

1. **[Main README](../README.md)** - Project overview and basic usage
2. **[Troubleshooting](./troubleshooting/troubleshooting-guide.md)** - Common problems and solutions
3. **[Agent Development](./development/agent-development.md)** - If extending the system
4. **[API Reference](./api/reference.md)** - If integrating with APIs
5. **[Architecture](./architecture/decision-records.md)** - For understanding design decisions

## 🤝 Contributing to Documentation

### How to Contribute

1. **Report Gaps**: Create issues for missing or unclear documentation
2. **Suggest Improvements**: Propose better organization or examples
3. **Submit Changes**: Follow contribution guidelines for documentation updates
4. **Review Process**: Participate in documentation review discussions

### Quality Standards

- **Technical Accuracy**: All code examples tested and verified
- **User Experience**: Clear, actionable documentation for all skill levels
- **Completeness**: Comprehensive coverage of topics and features
- **Maintainability**: Documentation structure supports easy updates and navigation

---

*This index provides complete navigation to all AgenticFleet documentation. For the most current information, always refer to the version-specific documentation and the main project README.*
