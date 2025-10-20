# Glossary

Common terms and concepts used in AgenticFleet.

---

## A

### Agent
An AI-powered entity with specialized capabilities. AgenticFleet includes orchestrator, researcher, coder, and analyst agents.

### Agent Framework
Microsoft's Agent Framework - the underlying system that powers AgenticFleet's multi-agent orchestration.

### Approval Handler
Component responsible for managing human-in-the-loop approval requests.

### Approval Request
A request for human review before executing potentially sensitive operations.

---

## C

### Callback
A function that's called when specific events occur during workflow execution (e.g., agent responses, tool calls).

### Checkpoint
A saved snapshot of workflow state that can be used to resume execution later.

### ChatAgent
The base agent type from Microsoft Agent Framework that AgenticFleet agents build upon.

### Coder Agent
Specialist agent focused on code generation, execution, and debugging.

---

## D

### Delegation
The act of the orchestrator assigning a task to a specialist agent.

---

## E

### Executor
An agent that performs actual work (researcher, coder, analyst) as opposed to the manager/orchestrator.

---

## F

### Fleet
The collection of all agents (orchestrator + specialists) working together.

### FleetBuilder
The builder pattern class used to construct and configure a fleet.

---

## H

### HITL (Human-in-the-Loop)
A pattern where humans review and approve agent actions before execution, adding a safety layer.

---

## M

### Magentic Fleet
The Microsoft Agent Framework's orchestration pattern using a manager and specialist executors.

### Manager
See Orchestrator.

### Mem0
Memory system providing persistent context across workflow sessions using vector storage.

---

## O

### Orchestrator
The manager agent responsible for planning, delegating tasks, and synthesizing results.

### OpenTelemetry (OTel)
Observability framework for collecting traces, metrics, and logs from AgenticFleet.

### OTLP
OpenTelemetry Protocol - the wire protocol for sending telemetry data.

---

## P

### Plan
The structured breakdown of a task into steps created by the orchestrator.

### Progress Ledger
JSON structure tracking workflow progress, including facts, status, and next actions.

### Prompt
The instructions given to an agent, including system prompt and user input.

---

## R

### Researcher Agent
Specialist agent focused on information gathering and research.

### Round
A single iteration of the workflow loop where an agent takes an action.

---

## S

### SSE (Server-Sent Events)
Protocol for streaming real-time updates from server to client.

### Stall
When a workflow makes no progress for multiple rounds, triggering replanning.

### Streaming
Real-time delivery of agent responses as they're generated, rather than waiting for completion.

### System Prompt
Instructions defining an agent's role, capabilities, and behavior patterns.

---

## T

### Tool
A function or capability that an agent can invoke to perform specific actions (e.g., web search, code execution).

### Temperature
A parameter (0.0-2.0) controlling randomness in AI responses. Lower = more deterministic, higher = more creative.

---

## U

### uv
Fast Python package manager used by AgenticFleet for dependency management.

---

## W

### Workflow
A complete execution from task input to final result, involving planning, delegation, and synthesis.

### Workflow YAML
Configuration file defining workflow-level settings like round limits and checkpointing.

---

## Related Resources

- [Architecture Documentation](../architecture/magentic-fleet.md)
- [Feature Guides](../features/)
- [API Reference](../api/)

---

**Missing a term?** [Suggest an addition](https://github.com/Qredence/agentic-fleet/issues/new).
