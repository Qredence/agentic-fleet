# Architectural Decision Records (ADRs)

## Overview

This document contains architectural decisions made during the development of AgenticFleet. Each decision follows the [Architecture Decision Record](https://adr.github.io/) format for transparency and future reference.

## Table of Contents

- [ADR-001: YAML-First Configuration](#adr-001-yaml-first-configuration)
- [ADR-002: Magentic Pattern Adoption](#adr-002-magentic-pattern-adoption)
- [ADR-003: Hybrid Modular Monolith Architecture](#adr-003-hybrid-modular-monolith-architecture)
- [ADR-004: Server-Sent Events for Streaming](#adr-004-server-sent-events-for-streaming)
- [ADR-005: Human-in-the-Loop Approval System](#adr-005-human-in-the-loop-approval-system)
- [ADR-006: uv Package Manager Mandate](#adr-006-uv-package-manager-mandate)
- [ADR-007: Pydantic Schemas for Tool Outputs](#adr-007-pydantic-schemas-for-tool-outputs)
- [ADR-008: Checkpointing Strategy](#adr-008-checkpointing-strategy)

---

## ADR-001: YAML-First Configuration

**Status**: Accepted
**Date**: 2025-01-15
**Decision**: All agent configuration, prompts, and behavior settings must be defined in YAML files rather than hardcoded in Python.

### Context

AgenticFleet needed a way to configure agent behavior without requiring code changes for:

- Model selection per agent
- System prompts and instructions
- Tool enablement/disablement
- Workflow limits and behavior

### Decision

Implement a hierarchical YAML configuration system:

1. **Global Workflow Configuration** (`config/workflow.yaml`)

   - Manager instructions and limits
   - Workflow-level settings (HITL, checkpointing)
   - Callback configurations

2. **Per-Agent Configuration** (`agents/<role>/config.yaml`)

   - Model selection
   - System prompts
   - Temperature and token limits
   - Tool configurations

3. **Environment Variables** (`.env`)
   - API keys and secrets
   - Feature flags
   - Infrastructure settings

### Consequences

**Benefits:**

- Non-technical users can modify agent behavior
- Easy A/B testing of prompts and configurations
- Clear separation of configuration from code
- Runtime configuration changes possible

**Costs:**

- Additional complexity in configuration loading
- Need for configuration validation
- Performance overhead of YAML parsing

**Alternatives Considered:**

- Database-backed configuration
- JSON configuration files
- Environment-only configuration
- Code-based configuration with decorators

### Implementation

```python
# Configuration loading pattern
def load_agent_config(role: str) -> dict:
    config_path = f"agents/{role}/config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
```

---

## ADR-002: Magentic Pattern Adoption

**Status**: Accepted
**Date**: 2025-01-20
**Decision**: Adopt Microsoft Agent Framework's Magentic One pattern for orchestration.

### Context

AgenticFleet needed a robust orchestration pattern for coordinating multiple specialized agents. Key requirements:

- Dynamic task decomposition
- Progress evaluation and stall detection
- Intelligent agent selection
- Structured planning and execution cycles

### Decision

Implement Magentic One pattern with PLAN → EVALUATE → ACT → OBSERVE cycle:

1. **PLAN**: Manager analyzes task and creates structured action plan
2. **EVALUATE**: Progress ledger checks completion, stall status, and next agent selection
3. **ACT**: Selected specialist executes with domain-specific tools
4. **OBSERVE**: Manager reviews response and updates context

### Consequences

**Benefits:**

- Proven orchestration pattern from Microsoft
- Built-in stall detection and recovery
- Structured progress tracking
- Extensible to new agent types

**Costs:**

- Dependency on Microsoft Agent Framework
- Learning curve for Magentic pattern
- Potential framework limitations

**Alternatives Considered:**

- Custom orchestration implementation
- State machine-based workflow
- Simple round-robin delegation
- Event-driven architecture without planning

### Implementation

```python
# Magentic workflow cycle
class MagenticFleet:
    async def run(self, task: str) -> str:
        # Plan phase
        plan = await self.manager.create_plan(task)

        # Main orchestration loop
        while not self.is_complete():
            # Evaluate phase
            progress = self.evaluate_progress()

            # Act phase
            if progress.next_agent:
                result = await self.delegate_to_agent(progress.next_agent)

            # Observe phase
            self.update_context(result)
```

---

## ADR-003: Hybrid Modular Monolith Architecture

**Status**: Accepted
**Date**: 2025-01-25
**Decision**: Structure AgenticFleet as a single deployable unit with clear internal module boundaries.

### Context

Initial architecture needed to balance:

- Development simplicity (single deployment)
- Clear separation of concerns
- Independent scaling of components
- Ease of development and testing

### Decision

Implement Hybrid Modular Monolith with these principles:

1. **Layered Architecture**

   - Core layer (no upward dependencies)
   - Agent layer (specialized logic)
   - Orchestration layer (coordination)
   - Interface layer (API + CLI)

2. **Package Boundaries**

   - Each package has single responsibility
   - Clear dependency rules (no circular imports)
   - Interface-based communication between layers

3. **Runtime Deployment**
   - Single Python process
   - Shared resources and configuration
   - Separate processes for scaling only if needed

### Consequences

**Benefits:**

- Simple deployment and operations
- Clear code organization
- Shared resources and context
- Easy debugging and profiling

**Costs:**

- Potential single point of failure
- Resource contention at scale
- Technology lock-in at process level

**Alternatives Considered:**

- Microservices architecture
- Modular monolith with separate processes
- Serverless functions per component
- Container composition with separate containers

### Implementation

```python
# Package dependency rules
# Core: No dependencies on other packages
# Config: Depends only on Core
# Agents: Depend on Core + Config
# Fleet: Depends on Agents + Core + Config
# Interface: Depends on Fleet + Core
```

---

## ADR-004: Server-Sent Events for Streaming

**Status**: Accepted
**Date**: 2025-02-01
**Decision**: Use Server-Sent Events (SSE) for real-time streaming of agent responses to frontend.

### Context

Frontend required real-time updates from backend for:

- Agent response streaming
- Progress updates
- Error notifications
- Approval request notifications

### Decision

Implement SSE streaming with typed events:

1. **Event Type System**

   - Standardized event formats
   - Backward compatibility
   - Extensible event types

2. **Connection Management**

   - Automatic reconnection
   - Heartbeat messages
   - Graceful degradation

3. **Event Serialization**
   - JSON-based event format
   - Consistent field naming
   - Version tolerance

### Consequences

**Benefits:**

- Simple infrastructure (HTTP-based)
- Firewall-friendly
- Built-in browser support
- Low latency for real-time updates

**Costs:**

- Uni-directional communication only
- Connection management complexity
- No built-in message queuing

**Alternatives Considered:**

- WebSockets
- Long polling
- WebRTC data channels
- gRPC streaming

### Implementation

```typescript
// SSE event handling
class EventStreamManager {
  private eventSource: EventSource;
  private eventHandlers: Map<string, Function>;

  connect(streamUrl: string) {
    this.eventSource = new EventSource(streamUrl);

    this.eventSource.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      this.handleEvent(data);
    });
  }

  private handleEvent(event: StreamEvent) {
    const handler = this.eventHandlers.get(event.type);
    if (handler) {
      handler(event.data);
    }
  }
}
```

---

## ADR-005: Human-in-the-Loop Approval System

**Status**: Accepted
**Date**: 2025-02-10
**Decision**: Implement configurable approval system for sensitive operations with abstract handler interface.

### Context

Safety requirements for:

- Code execution
- File system operations
- External API calls
- Sensitive data access

Need for:

- Configurable approval requirements
- Multiple approval interfaces (CLI, Web)
- Audit trail of all approvals

### Decision

Implement abstract approval system:

1. **ApprovalHandler Interface**

   - Standardized approval flow
   - Pluggable implementations
   - Timeout and retry support

2. **Operation Classification**

   - Trusted operations (auto-approved)
   - Required approval operations
   - Configurable per operation type

3. **Decision Flow**
   - Approve, Reject, Modify options
   - Audit logging
   - Integration with orchestration

### Consequences

**Benefits:**

- Configurable safety levels
- Multiple approval interfaces
- Complete audit trail
- Non-blocking for non-sensitive operations

**Costs:**

- Added complexity for tool execution
- Potential delays for approved operations
- User interface requirements

**Alternatives Considered:**

- No approvals (trust all operations)
- Always block on sensitive operations
- External approval service
- Blockchain-based approval system

### Implementation

```python
# Approval system interface
class ApprovalRequest(BaseModel):
    operation_type: str
    description: str
    details: dict[str, Any]
    timeout_seconds: int = 300

class ApprovalDecision(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"

class ApprovalHandler(ABC):
    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        pass
```

---

## ADR-006: uv Package Manager Mandate

**Status**: Accepted
**Date**: 2025-02-15
**Decision**: Mandate uv as the exclusive package manager for all Python operations.

### Context

Python ecosystem fragmentation required:

- Consistent dependency management
- Fast installation and resolution
- Lockfile reliability
- Development environment parity

### Decision

Standardize on uv exclusively:

1. **Development Commands**

   - All Python commands prefixed with `uv run`
   - Makefile wraps uv commands
   - No direct pip usage

2. **Dependency Management**

   - `uv sync` for dependency updates
   - `uv lockfile` for reproducible builds
   - `pyproject.toml` as single source of truth

3. **Environment Management**
   - uv-managed virtual environments
   - No manual venv management
   - Consistent Python versions

### Consequences

**Benefits:**

- Dramatically faster installations
- Reliable dependency resolution
- Excellent lockfile support
- Consistent development environments

**Costs:**

- Learning curve for developers
- Tooling ecosystem dependency
- Potential compatibility issues with legacy packages

**Alternatives Considered:**

- pip + venv
- pipenv
- poetry
- conda package manager

### Implementation

```makefile
# Makefile wrapper for uv commands
.PHONY: install sync test lint format type-check

install:
    uv pip install agentic-fleet
    uv sync --all-extras

sync:
    uv sync

test:
    uv run pytest

lint:
    uv run ruff check .
```

---

## ADR-007: Pydantic Schemas for Tool Outputs

**Status**: Accepted
**Date**: 2025-02-20
**Decision**: Mandate Pydantic models for all tool outputs to ensure type safety and serialization consistency.

### Context

Multi-agent system required:

- Reliable data interchange between agents
- Type safety for tool results
- Serialization/deserialization
- Validation of tool outputs

### Decision

Standardize on Pydantic models:

1. **Schema Definition**

   - All tool outputs inherit from BaseModel
   - Strict type definitions
   - Validation rules and constraints

2. **Contract Stability**

   - Backward compatibility guarantees
   - Versioned schema evolution
   - Migration path for breaking changes

3. **Integration Benefits**
   - Automatic validation
   - IDE autocomplete
   - Documentation generation
   - Error handling improvements

### Consequences

**Benefits:**

- Type safety at compile time
- Automatic validation and error handling
- IDE support and documentation
- Consistent serialization

**Costs:**

- Additional code complexity
- Learning curve for Pydantic
- Performance overhead of validation
- Schema evolution complexity

**Alternatives Considered:**

- Plain Python dictionaries
- dataclasses for structured data
- JSON Schema validation
- Custom validation framework

### Implementation

```python
# Tool output pattern
from pydantic import BaseModel

class CodeExecutionResult(BaseModel):
    """Standard result format for code execution tools."""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: int = 0

class ToolResult(ABC):
    """Base class for all tool results."""

    @classmethod
    def get_pydantic_model(cls) -> Type[BaseModel]:
        raise NotImplementedError
```

---

## ADR-008: Checkpointing Strategy

**Status**: Accepted
**Date**: 2025-02-25
**Decision**: Implement file-based checkpointing to save workflow state and enable cost-efficient recovery.

### Context

Long-running agent workflows required:

- State persistence across restarts
- Recovery from failures
- Cost optimization (avoiding recomputation)
- Debugging and inspection capabilities

### Decision

Implement comprehensive checkpointing system:

1. **Checkpoint Content**

   - Complete workflow state
   - Message history
   - Progress ledger
   - Agent context and memories

2. **Storage Strategy**

   - File-based storage for simplicity
   - JSON serialization for transparency
   - Metadata for listing and selection

3. **Resume Capability**
   - Automatic resume on failure
   - Manual resume selection
   - State validation on resume

### Consequences

**Benefits:**

- 50-80% cost reduction on retries
- Failure recovery without data loss
- Debugging inspection of workflow state
- Long-running workflow support

**Costs:**

- Storage I/O overhead
- Complexity in state management
- Larger container disk usage
- Recovery validation complexity

**Alternatives Considered:**

- In-memory checkpoints only
- Database-backed persistence
- External state storage service
- No checkpointing (full recomputation)

### Implementation

```python
# Checkpointing pattern
class FileCheckpointStorage(CheckpointStorage):
    def save_checkpoint(self, workflow_id: str, state: dict) -> str:
        checkpoint_id = f"ckpt_{int(time.time())}"
        filepath = Path(f"var/checkpoints/{checkpoint_id}.json")

        checkpoint_data = {
            "id": checkpoint_id,
            "workflow_id": workflow_id,
            "created_at": datetime.utcnow().isoformat(),
            "state": state
        }

        with open(filepath, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        return checkpoint_id
```

## Future Decisions

This section is reserved for future architectural decisions that will be added as AgenticFleet evolves.

### Decision Process

1. **Proposal**: Any team member can propose an ADR
2. **Discussion**: Technical discussion and refinement
3. **Decision**: Final acceptance or rejection
4. **Implementation**: Update codebase and documentation
5. **Review**: Regular review of implemented ADRs

### Template

```markdown
## ADR-XXX: [Title]

**Status**: [Accepted/Rejected/Superseded]
**Date**: [YYYY-MM-DD]
**Decision**: [Brief statement of decision]

### Context

[Background and problem statement]

### Decision

[Chosen approach and reasoning]

### Consequences

**Benefits:**

- [Positive outcomes]

**Costs:**

- [Negative outcomes or trade-offs]

**Alternatives Considered:**

- [Other approaches considered]

### Implementation

[Code examples or implementation details]
```

---

_This document should be updated whenever significant architectural decisions are made. All ADRs should be numbered sequentially and include clear implementation guidance for future developers._
