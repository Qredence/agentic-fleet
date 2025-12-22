# Diagram Templates (Mermaid)

## Table of Contents

1. System Context
2. Component Diagram
3. Sequence Diagram
4. Data Flow
5. User Flow
6. State Diagram

## Diagram Guidelines

- Prefer Mermaid in Markdown unless the repo uses another tool.
- Keep diagrams small (5-9 nodes) and label edges clearly.
- Align diagrams with actual code or config names.
- Add a 1-2 sentence caption below each diagram.

## 1. System Context

```mermaid
flowchart LR
  User[User] --> UI[Web UI]
  UI --> API[API Service]
  API --> DB[(Database)]
  API --> LLM[LLM Provider]
```

## 2. Component Diagram

```mermaid
flowchart TB
  subgraph Backend
    API[API Layer]
    Services[Services]
    Workflows[Workflows]
  end
  subgraph Runtime
    Cache[(Cache)]
    Logs[(Logs)]
  end
  API --> Services --> Workflows
  Workflows --> Cache
  Workflows --> Logs
```

## 3. Sequence Diagram

```mermaid
sequenceDiagram
  participant U as User
  participant UI as UI
  participant API as API
  participant WF as Workflow
  U->>UI: Submit request
  UI->>API: POST /chat
  API->>WF: Start workflow
  WF-->>API: Stream events
  API-->>UI: SSE updates
  UI-->>U: Render output
```

## 4. Data Flow

```mermaid
flowchart LR
  Input[User Input] --> Router[Routing]
  Router --> Exec[Execution]
  Exec --> Store[(History)]
  Exec --> Output[Response]
```

## 5. User Flow

```mermaid
flowchart LR
  Start([Start]) --> Intent{Identify intent}
  Intent -->|Simple| Fast[Fast Path]
  Intent -->|Complex| Multi[Multi-agent]
  Fast --> Done([Done])
  Multi --> Done
```

## 6. State Diagram

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Running: start
  Running --> Waiting: request
  Waiting --> Running: response
  Running --> Completed: finish
  Completed --> [*]
```
