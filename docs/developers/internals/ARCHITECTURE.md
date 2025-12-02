# AgenticFleet Architecture

## Overview

**AgenticFleet** is a hybrid orchestration runtime that combines the cognitive reasoning capabilities of **DSPy** with the robust execution framework of **Microsoft Agent Framework**. It is designed to manage a self-optimizing fleet of specialized AI agents that can adapt to complex tasks through dynamic routing, tool usage, and continuous quality improvement.

## Core Architecture

The system is layered into four main components:

1.  **Cognitive Layer (DSPy)**: Handles high-level reasoning, task analysis, and decision-making.
2.  **Orchestration Layer**: Manages the workflow lifecycle, state, and agent coordination.
3.  **Agent Layer**: Specialized workers that execute specific subtasks.
4.  **Infrastructure Layer**: Provides persistence, tooling, and configuration.

---

## 1. Cognitive Layer (`src/agentic_fleet/dspy_modules`)

The "brain" of the system is the `DSPyReasoner` (in `reasoner.py`). It uses DSPy `ChainOfThought` modules to perform complex reasoning steps that guide the workflow.

### Key Modules

- **Task Analysis**: Decomposes user requests into structured requirements, estimating complexity and identifying necessary capabilities.
- **Routing**: Decides which agents to engage and how (Delegated, Sequential, Parallel). It supports "Fast Path" for simple queries to minimize latency.
- **Quality Assessment**: Evaluates agent outputs against dynamic criteria, assigning scores and identifying missing elements.
- **Progress Evaluation**: Determines if a task is complete or requires refinement loops.
- **Tool Planning**: Generates ReAct-style plans for tool usage.

### Signatures

Typed DSPy signatures (in `signatures.py` and `workflow_signatures.py`) define the input/output contracts for these reasoning modules, ensuring structured and predictable behavior from the LLM.

---

## 2. Orchestration Layer (`src/agentic_fleet/workflows`)

The orchestration layer wires the cognitive decisions into executable actions.

### `SupervisorWorkflow`

The entry point for task execution. It:

1.  **Fast Path Check**: Quickly identifies simple tasks (e.g., "hello", "2+2") and generates immediate responses without spinning up the full agent fleet.
2.  **Workflow Initialization**: Uses `build_fleet_workflow` to construct a `agent_framework.Workflow` instance based on the current context.
3.  **Execution Management**: Runs the workflow, captures events, and manages the "Fast Path" vs. "Full Fleet" logic.
4.  **Persistence**: Saves execution history to `HistoryManager` (and optionally Cosmos DB).

### `WorkflowBuilder`

Constructs the actual execution graph. It integrates the `DSPyReasoner` as a decision node that routes tasks to specific `ChatAgent` executors.

---

## 3. Agent Layer (`src/agentic_fleet/agents`)

Agents are the workers that perform the actual tasks. They are built on top of `agent_framework.ChatAgent`.

### `DSPyEnhancedAgent`

A wrapper class (in `base.py`) that extends `ChatAgent` with DSPy capabilities:

- **ReAct Strategy**: Autonomous thought-action-observation loops for research and complex problem solving.
- **Program of Thought (PoT)**: Generates and executes Python code for precise calculations (used by the Analyst).
- **Caching**: Built-in TTL caching for responses.

### `AgentFactory`

A factory class (in `coordinator.py`) that creates agents from YAML configuration (`workflow_config.yaml`). It handles:

- Model assignment (e.g., `gpt-4.1`, `gpt-5-mini`).
- Tool resolution and validation.
- Instruction loading (from `prompts.py`).

### Standard Agents

- **Researcher**: Equipped with `TavilyMCPTool` and `BrowserTool`. Enforced to use search for time-sensitive queries.
- **Analyst**: Equipped with `HostedCodeInterpreterTool` for data analysis.
- **Writer/Reviewer**: Specialized for content generation and quality control.

---

## 4. Infrastructure Layer (`src/agentic_fleet/utils`, `src/agentic_fleet/tools`)

### Tooling

- **`ToolRegistry`**: Central repository for managing and retrieving tools.
- **`TavilyMCPTool`**: Integration with Tavily for high-quality web search.
- **`BrowserTool`**: Playwright-based tool for deep web scraping and interaction.

### Persistence & Optimization

- **Cosmos DB**: Optional integration (`cosmos.py`) for long-term memory and history.
- **GEPA Optimizer**: The **Genetic Evolutionary Prompt Algorithm** (`gepa_optimizer.py`) optimizes DSPy prompts over time based on execution history and quality scores.

### Configuration

- **`workflow_config.yaml`**: Central configuration file controlling models, thresholds, and agent behaviors.

---

## Execution Flow

1.  **User Request**: Enters via CLI or API.
2.  **Fast Path**: `SupervisorWorkflow` checks if the task is trivial. If so, `DSPyReasoner.generate_simple_response` returns immediately.
3.  **Analysis**: If complex, `DSPyReasoner.analyze_task` breaks it down.
4.  **Routing**: `DSPyReasoner.route_task` selects agents (e.g., Researcher + Writer).
5.  **Execution**: Selected agents execute (potentially using Tools).
6.  **Quality Check**: `DSPyReasoner.assess_quality` scores the result.
7.  **Output**: Final result is returned to the user.
