# AgenticFleet Documentation

Welcome to **AgenticFleet**, a modular, agentic reasoning system designed to harness specialized agents for intelligent reasoning, web search, and code execution. This document provides a comprehensive overview of the architecture, modules, and usage based on the latest agentic system concepts.

---

## Overview

AgenticFleet is built with the core idea of **Agentic Reasoning** wherein the system employs several specialized agents that collaborate to address complex tasks. Using advanced chain-of-thought reasoning, self-reflection, and dynamic planning, the system can:

- Construct and analyze knowledge graphs using the *MindMapAgent* and *MindMapTool*.
- Perform targeted web searches and synthesize relevant information using the *WebSearchAgent* and *WebSearchTool*.
- Generate, validate, and execute code for statistical modeling with the *CodingAgent* and *CodeExecutionTool*.
- Integrate and consolidate reasoning processes across agents using the *Agentic Reasoning Module*.

The system is designed to integrate with modern LLMs (Language Models) like Azure OpenAI and follows best practices in code formatting and linting via tools such as Black, isort, and ruff.

---

## Architecture

AgenticFleet is organized into several key components:

### 1. Core Agents

The agents are at the heart of the system, each responsible for specialized tasks:

- **MindMapAgent**: Utilizes the *MindMapTool* to build and analyze knowledge graphs. It extracts entities, identifies relationships, and generates insights through community detection and path analysis.

- **WebSearchAgent**: Leverages the *WebSearchTool* to perform asynchronous web searches. It refines queries via LLM, scores results based on relevance, and synthesizes a cohesive report from gathered data.

- **CodingAgent**: Focused on generating and executing code, particularly for statistical modeling and data analysis. It incorporates safety checks, validation procedures, and code formatting to ensure robust execution.

### 2. Tools

Each agent uses specialized tools to perform its functions:

- **MindMapTool**: Provides a graph-based interface for managing entities and relationships, enabling structured knowledge representation and analysis.

- **WebSearchTool**: Executes web searches, applies TF-IDF for result scoring, and maintains an execution history along with content analysis for reliable querying.

- **CodeExecutionTool**: Responsible for generating, validating, and executing code with rigorous safety checks. It supports formatting (via Black, isort) and enforces resource limits and module allowances.

### 3. Agentic Reasoning Module

This module consolidates and extends agent capabilities by offering reasoning utilities:

- **Chain-of-Thought Generation**: Use the function `generate_chain_of_thought` to produce detailed reasoning paths based on an LLM prompt.

- **Reflection and Self-Critique**: With `reflect_on_decision`, agents can introspect on their decisions, yielding potential improvements.

- **Planning & Critique**: The `plan_and_critique` function facilitates creating structured plans and critiquing past insights, helping in iterative task refinement.

- **Integration of Insights**: `integrate_agentic_reasoning` combines outputs from various agents to generate a unified reasoning report that identifies common themes and outlines next steps.

### 4. LLM Integration

AgenticFleet uses a centralized LLM factory (located in `src/agentic_fleet/core/llm/factory.py`) to instantiate and manage LLM clients across the system. This ensures consistent configurations, supports Azure OpenAI integration, and maintains declarative setups.

### 5. Supporting Modules

Additional modules support messaging, API routing, workflows, and configuration management:

- **Messaging and Workflows**: Facilitate structured communication between agents and external systems, with supporting schemas and middleware.

- **Configuration Management**: Ensures global settings and dependency management align with best practices.

---

## How to Use

1. **Deployment**: Launch the FastAPI backend (see `app.py` in the root of the project) which integrates the agents and exposes REST and WebSocket APIs.

2. **Agent Interaction**: Agents are designed as microservices that register their functionalities via a common base. They can be accessed either through custom UIs or integrated directly within the Chainlit interface.

3. **Extending Functionality**: Developers can extend or modify agents by following the modular structure. New tools and agents can be added by adhering to the declarative configurations outlined in the existing modules.

---

## Best Practices

- **Code Quality**: Use `black`, `isort`, and `ruff` to maintain a consistent code style.
- **Testing**: Leverage the unit and integration tests provided under `src/agentic_fleet/tests`.
- **Documentation**: Regularly update documentation as new features or agents are integrated.
- **Memory and Resource Management**: Adhere to resource limits specified in the configuration (e.g., in the CodingAgent).

---

## References

- [Microsoft Autogen Documentation](https://microsoft.github.io/autogen/stable/index.html)
- [Chainlit Documentation](https://docs.chainlit.io/)
- [Agentic Reasoning GitHub Repository](https://github.com/theworldofagents/Agentic-Reasoning.git)

---

## Conclusion

AgenticFleet represents a state-of-the-art approach to multi-agent collaboration, integrating advanced reasoning, robust data processing, and intelligent code execution. By combining specialized agents with sophisticated reasoning utilities, the system empowers developers to tackle complex problems with modular and scalable solutions.
