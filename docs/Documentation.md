# Comprehensive AgenticFleet Documentation

Welcome to the detailed documentation for AgenticFleet. This guide explains the complete agentic system concept, architectural structure, and the usage of each module.

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
    - [Core Agents](#core-agents)
    - [Tools](#tools)
    - [Agentic Reasoning Module](#agentic-reasoning-module)
    - [Multi-Agent Patterns for Enhanced Reasoning](#multi-agent-patterns-for-enhanced-reasoning)
    - [LLM Integration](#llm-integration)
    - [Supporting Modules](#supporting-modules)
3. [Module Descriptions](#module-descriptions)
    - [MindMapAgent & MindMapTool](#mindmapagent--mindmaptool)
    - [WebSearchAgent & WebSearchTool](#websearchagent--websearchtool)
    - [CodingAgent & CodeExecutionTool](#codingagent--codeexecutiontool)
    - [Agentic Reasoning Utilities](#agentic-reasoning-utilities)
4. [Usage Guidelines](#usage-guidelines)
5. [Best Practices](#best-practices)
6. [References](#references)

---

## Introduction

AgenticFleet is a modular multi-agent reasoning system that leverages specialized agents to solve complex tasks. It is designed to orchestrate various agent functionalities such as knowledge graph construction, web searching, and code execution, while incorporating advanced chain-of-thought reasoning and dynamic self-reflection.

The system uses modern LLMs (e.g., Azure OpenAI) along with strict coding standards enforced via Black, isort, and ruff, ensuring both reliability and readability.

---

## System Architecture

### Core Agents

The heart of AgenticFleet consists of specialized agents, each focusing on a distinct functionality:

- **MindMapAgent**: Builds and analyzes knowledge graphs using the MindMapTool. It extracts key entities and relationships, performs community detection, and provides actionable insights.

- **WebSearchAgent**: Conducts advanced web searches using the WebSearchTool. It refines queries with LLM assistance, scores results based on relevance, and synthesizes a coherent narrative from disparate data sources.

- **CodingAgent**: Automates the process of code generation and execution using the CodeExecutionTool. It is especially geared towards statistical modeling and data analysis, ensuring safe code execution with thorough validation and formatting.

### Tools

Each core agent leverages specialized tools:

- **MindMapTool**: Offers a graph-based framework to store and analyze structured knowledge, supporting tasks like entity extraction and relationship mapping.

- **WebSearchTool**: Performs asynchronous web searches with capabilities for result scoring (e.g., TF-IDF) and content synthesis.

- **CodeExecutionTool**: Enables dynamic code generation, validation, formatting, and execution. It enforces security measures such as resource and module restrictions.

### Agentic Reasoning Module

This module provides utilities to enhance the decision-making and introspective capabilities of agents:

- **Chain-of-Thought Generation**: The `generate_chain_of_thought` function enables detailed reasoning, producing step-by-step logical flows.

- **Self-Reflection**: Use `reflect_on_decision` to gain insights and critique previous decisions.

- **Planning and Critique**: The `plan_and_critique` function helps create structured plans and offers constructive critiques of these plans.

- **Integration of Insights**: The `integrate_agentic_reasoning` function assimilates outputs from multiple agents to generate a unified report that highlights common themes and future action items.

### Multi-Agent Patterns for Enhanced Reasoning

AgenticFleet leverages advanced multi-agent patterns inspired by Autogen to enhance model reasoning. At its core, the framework deploys external LLM-based agents during the reasoning process, allowing the primary reasoning LLM to interact with external information sources in an agentic way.

During the reasoning process, the model determines in real-time when additional information is required. When such a need is detected, the reasoning model proactively embeds specialized tokens into its reasoning flow. These tokens are categorized into:

- **Web-Search Token**: Triggers the use of external search engines to retrieve up-to-date information.
- **Coding Token**: Invokes the CodingAgent to generate, review, and execute code for problem-solving and statistical modeling.
- **Mind-Map Calling Token**: Engages the MindMapAgent to extract, store, or update knowledge within a structured mind map.

When the model detects one of these tokens, it temporarily halts its reasoning to extract a precise query along with its current context. This query, combined with the reasoning context, is dispatched to the relevant external agent. The agent processes the request and generates information that is then reintegrated into the original reasoning chain. This iterative retrieval-and-reasoning cycle continues, dynamically refining the model's conclusions until a fully reasoned final answer is achieved.

#### Pattern Implementation

The pattern is implemented in the following components:

1. **RetrievalReasoningOrchestrator**: 
   - Manages the iterative reasoning process
   - Coordinates between the main reasoning LLM and specialized agents
   - Processes embedded tokens and collects external information
   - Maintains reasoning state and manages iterations

2. **Specialized Tokens**:
   - `[WEB_SEARCH: query]`: Triggers web search operations
   - `[CODING: task]`: Initiates code generation or execution
   - `[MIND_MAP: query]`: Accesses or updates the knowledge graph

3. **Reasoning Flow**:
   ```
   Initial Query
        ↓
   Generate Reasoning
        ↓
   Extract Tokens ←←←←←←←←←←←
        ↓                    ↑
   Process Tokens            ↑
        ↓                    ↑
   Collect Information       ↑
        ↓                    ↑
   Continue Reasoning →→→→→→→
   ```

4. **State Management**:
   - Tracks the original query
   - Maintains current reasoning chain
   - Records embedded tokens
   - Stores collected information
   - Monitors iteration count

#### Usage Example

```python
# Initialize the orchestrator
orchestrator = await create_reasoning_orchestrator(config)

# Execute reasoning process
result = await orchestrator.reason(
    "Analyze the performance impact of recent code changes"
)

# Access results
final_reasoning = result["final_reasoning"]
collected_info = result["collected_information"]
iterations = result["iterations"]
```

This implementation allows the model to:
1. Dynamically identify when external information is needed
2. Embed appropriate tokens in its reasoning
3. Collect and integrate information from specialized agents
4. Refine its reasoning through multiple iterations
5. Produce comprehensive, well-supported conclusions

For more details on the multi-agent patterns and their implementation, please refer to the [Autogen Agentchat User Guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide).

### LLM Integration

AgenticFleet centrally manages LLM configurations using a dedicated factory located in `src/agentic_fleet/core/llm/factory.py`. This allows for:

- Consistent and declarative configuration of LLM clients.
- Support for multiple providers (e.g., Azure OpenAI).
- Seamless LLM integration across different agents and modules.

### Supporting Modules

Additional modules provide critical support through messaging, API routing, workflow orchestration, and configuration management. These ensure that the system remains scalable, maintainable, and easily extensible.

---

## Module Descriptions

### MindMapAgent & MindMapTool

- **MindMapAgent**: Implements methods to process and analyze information in the form of knowledge graphs. It registers functions that enable entity extraction and semantic relationship analysis.

- **MindMapTool**: Manages the creation and querying of knowledge graphs. It supports operations like adding entities, linking relationships, community detection, and performing path analyses.

### WebSearchAgent & WebSearchTool

- **WebSearchAgent**: Uses the WebSearchTool to perform targeted searches. It refines search queries using LLM-generated prompts and synthesizes the results to construct a cohesive overview.

- **WebSearchTool**: Handles asynchronous web requests, applies scoring and content analysis techniques, and maintains a history of searches for reliable diagnostics.

### CodingAgent & CodeExecutionTool

- **CodingAgent**: Automates code generation and statistical modeling tasks. It integrates with LLMs to create code blocks, validates them, and safely executes code with robust error handling.

- **CodeExecutionTool**: Provides a secure execution environment with built-in code formatting (Black, isort) and linting checks (ruff). It enforces execution limits and supports module restrictions.

### Agentic Reasoning Utilities

The Agentic Reasoning Module encapsulates the following functions:

- `generate_chain_of_thought`: Generates detailed reasoning steps.
- `reflect_on_decision`: Provides self-reflection on decisions made by agents.
- `plan_and_critique`: Constructs a plan and critiques it for continuous improvement.
- `integrate_agentic_reasoning`: Consolidates multiple agent outputs into a unified report.

---

## Usage Guidelines

1. **Deployment**: The system is deployed as a FastAPI backend that exposes REST and WebSocket endpoints. Launch the API gateway using the provided `app.py` file.

2. **Agent Interaction**: Agents register their functionalities with a centralized base class, making them accessible through standardized interfaces. Use the Chainlit interface for interactive communication with agents.

3. **Extensibility**: New agents and tools can be added by following the modular architecture. Ensure new modules comply with code quality standards and integrate seamlessly with the LLM configuration.

---

## Best Practices

- **Code Consistency**: Always use `black`, `isort`, and `ruff` to maintain code formatting and style.
- **Testing**: Conduct both unit and integration tests. Tests are available under the `src/agentic_fleet/tests` directory.
- **Resource Management**: Adhere to the memory and execution limits defined in each agent’s configuration.
- **Documentation**: Keep this document and inline code documentation updated to reflect any system changes.

---

## References

- [Microsoft Autogen Documentation](https://microsoft.github.io/autogen/stable/index.html)
- [Chainlit Documentation](https://docs.chainlit.io/)
- [Agentic Reasoning GitHub Repository](https://github.com/theworldofagents/Agentic-Reasoning.git)

---

## Conclusion

AgenticFleet is at the forefront of modern agentic systems. Through specialized agents, robust reasoning utilities, and integrated LLM support, the system is designed to be scalable, extensible, and highly effective for complex problem solving.

For additional support or detailed modification guides, please refer to the internal developer documentation or contact the project maintainers.
