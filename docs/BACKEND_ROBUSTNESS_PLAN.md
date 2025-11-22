# Backend & FastAPI Robustness Improvement Plan

## 1. Security Enhancements

### 1.1 Authentication & Authorization

**Current State**: No authentication mechanism visible in `main.py`.
**Recommendation**:

- Implement **API Key Authentication** for service-to-service communication.
- Implement **OAuth2 / JWT** for user-facing endpoints if a frontend is involved.
- Use `fastapi.security` utilities to enforce auth on protected routes.

### 1.2 Security Headers

**Current State**: Only basic CORS.
**Recommendation**:

- Add **TrustedHostMiddleware** to prevent Host Header attacks.
- Add **HTTPSRedirectMiddleware** (if not handled by a reverse proxy like Nginx/Traefik).
- Implement a custom middleware or use a library (like `secure`) to set headers:
  - `Strict-Transport-Security` (HSTS)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`

### 1.3 CORS Configuration

**Current State**: Permissive `allow_origins=["*"]`.
**Recommendation**:

- Restrict `allow_origins` to specific frontend domains via environment variables.
- Validate `allow_credentials=True` is actually needed (requires specific origins, not `*`).

## 2. Reliability & Resilience

### 2.1 Rate Limiting

**Current State**: Missing.
**Recommendation**:

- Integrate **SlowAPI** or **FastAPI-Limiter** (Redis-backed).
- Apply global limits (e.g., 100 req/min) and stricter limits on expensive endpoints (e.g., `/workflows/run`).

### 2.2 Circuit Breakers

**Current State**: Not visible for external calls.
**Recommendation**:

- Implement circuit breakers (using libraries like `pybreaker` or `tenacity`) for:
  - OpenAI API calls
  - Tavily Search API
  - Cosmos DB operations
- Fail fast and return degraded responses (e.g., "Search unavailable") rather than hanging.

### 2.3 Deep Health Checks

**Current State**: Likely a simple "OK" response.
**Recommendation**:

- Enhance `/health` endpoint to check:
  - Database connectivity (Cosmos DB)
  - External API reachability (OpenAI, Tavily) - _optional/cached_
  - Disk space / Memory usage
- Use `fastapi-health` or custom logic to return 503 if critical dependencies are down.

## 3. Observability

### 3.1 Structured Logging

**Current State**: Custom text-based logging.
**Recommendation**:

- Switch to **JSON logging** in production (using `python-json-logger` or `structlog`).
- Ensure logs include correlation IDs (`request_id`) automatically (already partially handled by middleware, but needs to be consistent across threads).

### 3.2 Metrics (Prometheus)

**Current State**: Missing.
**Recommendation**:

- Add **PrometheusMiddleware** (via `starlette-exporter` or `prometheus-fastapi-instrumentator`).
- Track:
  - Request count / Latency / Error rates
  - Active workflow runs
  - Token usage / Cost estimates

### 3.3 Distributed Tracing

**Current State**: Configured in `workflow_config.yaml` but needs verification in FastAPI.
**Recommendation**:

- Ensure **OpenTelemetry** instrumentation is applied to the FastAPI app instance.
- Trace requests from API -> Workflow -> Agent -> Tool -> External API.

## 4. Architecture & Code Quality

### 4.1 Input Validation

**Current State**: `WorkflowRunRequest.inputs` is generic `dict[str, Any]`.
**Recommendation**:

- Use **Pydantic v2** features for stricter validation.
- If possible, define specific input schemas for different workflow types (using `Union` or `Discriminator`).

### 4.2 Dependency Injection

**Current State**: `lifespan` handles DB, but routes might be importing globals.
**Recommendation**:

- Use FastAPI's `Depends` for injecting:
  - `WorkflowRunner` instances
  - Database sessions
  - Configuration objects
- This improves testability by allowing easy mocking of dependencies.

### 4.3 Error Handling

**Current State**: Good custom exception hierarchy.
**Recommendation**:

- Ensure all custom exceptions (`AgentExecutionError`, etc.) are mapped to appropriate HTTP status codes in `error_handlers.py`.
- Don't expose internal stack traces in 500 responses (already handled by sanitization, but verify).

## 5. Implementation Roadmap

### Phase 1: Immediate Fixes (High Impact)

1.  [ ] Restrict CORS origins.
2.  [ ] Add Rate Limiting middleware.
3.  [ ] Implement Structured Logging (JSON).

### Phase 2: Resilience (Medium Impact)

4.  [ ] Add Circuit Breakers for OpenAI/Tavily.
5.  [ ] Implement Deep Health Checks.
6.  [ ] Add Security Headers.

### Phase 3: Observability & Auth (Long Term)

7.  [ ] Setup Prometheus Metrics.
8.  [ ] Implement API Key / OAuth Auth.
9.  [ ] Refactor for Dependency Injection.
