# Technology Stack - AgenticFleet

## Core Backend

- **Language:** Python 3.12+ (managed via `uv`)
- **Web Framework:** FastAPI (Async, Pydantic v2)
- **AI Orchestration:** Microsoft Agent Framework (Magentic Fleet pattern)
- **Intelligence Layer:** DSPy (Programmatic LLM pipelines)
- **Data Validation:** Pydantic (Typed signatures and output models)

## Frontend

- **Framework:** React 19 (Vite-based)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** Radix UI, Lucide Icons, Shadcn UI
- **State Management:** Zustand (inferred from `stores/`)
- **API Interaction:** SSE and WebSockets for real-time orchestration streaming

## Infrastructure & Storage

- **Primary Database:** Azure Cosmos DB (NoSQL)
- **Local/Caching:** SQLite, local file-based persistence
- **Containerization:** Docker & Docker Compose
- **Cloud Provider:** Azure (AI Foundry, Cosmos, Monitor)

## Observability & Performance

- **Distributed Tracing:** OpenTelemetry (Jaeger, Azure Monitor)
- **Evaluation:** Azure AI Evaluation, Langfuse
- **Metrics:** Prometheus, StatsD
- **Resilience:** Tenacity (Retries), AnyIO/Asyncer (Concurrency)
