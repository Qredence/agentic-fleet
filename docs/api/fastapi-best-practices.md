# FastAPI Best Practices Documentation

**Version**: 0.5.5
**Last Updated**: Current Session

---

## Table of Contents

1. [Overview](#overview)
2. [Database Session Management](#database-session-management)
3. [Request Validation](#request-validation)
4. [Exception Handling](#exception-handling)
5. [Configuration Management](#configuration-management)
6. [Health Check Endpoint](#health-check-endpoint)
7. [API Reference](#api-reference)
8. [Best Practices](#best-practices)
9. [Examples](#examples)

---

## Overview

This document describes the FastAPI best practices implemented in AgenticFleet, focusing on:

- **Reliability**: Automatic transaction rollback and error handling
- **Security**: Input validation and sanitization
- **Maintainability**: Type-safe configuration and consistent patterns
- **Observability**: Comprehensive health checks and error reporting

---

## Database Session Management

### Overview

Database sessions are automatically managed with proper transaction handling:

- **Automatic commit** on successful completion
- **Automatic rollback** on exceptions
- **Session cleanup** always occurs

### Implementation

The `get_db()` dependency in `src/agenticfleet/persistance/database.py` handles all transaction management:

```python
def get_db() -> Any:
    """Database session dependency with automatic transaction management."""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Automatic commit on success
    except Exception:
        db.rollback()  # Automatic rollback on error
        raise
    finally:
        db.close()  # Always close session
```

### Usage in Routes

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from agenticfleet.persistance.database import get_db

@router.post("/v1/approvals")
async def create_approval_request(
    request: CreateApprovalRequest,
    db: Session = Depends(get_db),  # Automatic transaction management
) -> JSONResponse:
    approval_request = ApprovalRequest(...)
    db.add(approval_request)
    # Commit happens automatically on success
    # Rollback happens automatically on exception
    return JSONResponse(...)
```

### Benefits

- ✅ **No manual commits needed** - Handled automatically
- ✅ **No forgotten rollbacks** - Always rolled back on errors
- ✅ **Consistent behavior** - Same pattern across all routes
- ✅ **Prevents data corruption** - No partial commits

### Example

```python
@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Create a new item with automatic transaction management."""
    db_item = Item(**item.model_dump())
    db.add(db_item)
    # If this succeeds, commit happens automatically
    # If an exception occurs, rollback happens automatically
    return ItemResponse.from_orm(db_item)
```

---

## Request Validation

### Overview

All POST/PUT endpoints use Pydantic models for automatic request validation:

- **Type validation** - Ensures correct data types
- **Field validation** - Min/max length, required fields, etc.
- **Clear error messages** - Detailed validation errors
- **OpenAPI schema** - Auto-generated API documentation

### Creating Request Models

Define Pydantic models in `src/agenticfleet/api/models/`:

```python
from pydantic import BaseModel, Field

class CreateApprovalRequest(BaseModel):
    """Request model for creating approval requests."""

    conversation_id: str = Field(
        ...,
        min_length=1,
        description="Conversation ID (UUID format)",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )

    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional approval details",
    )
```

### Using in Routes

```python
@router.post("/v1/approvals")
async def create_approval_request(
    request: CreateApprovalRequest,  # FastAPI auto-validates
    db: Session = Depends(get_db),
) -> JSONResponse:
    # No manual JSON parsing needed
    # No manual validation needed
    # request.conversation_id is guaranteed to be non-empty string
    ...
```

### Validation Error Response

When validation fails, FastAPI automatically returns:

```json
{
  "error": "validation_error",
  "detail": [
    {
      "loc": ["body", "conversation_id"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ],
  "path": "/v1/approvals"
}
```

### Benefits

- ✅ **Automatic validation** - No manual checks needed
- ✅ **Better error messages** - Clear field-level errors
- ✅ **Type safety** - IDE autocomplete and type checking
- ✅ **OpenAPI docs** - Auto-generated API documentation

---

## Exception Handling

### Overview

Centralized exception handling provides consistent error responses across all endpoints.

### Custom Exception Types

Located in `src/agenticfleet/api/exceptions.py`:

```python
from agenticfleet.api.exceptions import (
    APIException,
    NotFoundError,
    ValidationError,
    InternalServerError,
)

# Usage examples
raise NotFoundError("approval request", request_id)
raise ValidationError("Invalid conversation ID", "conversation_id")
raise InternalServerError("Database connection failed", original_error)
```

### Exception Types

#### `APIException`

Base exception class for all API errors:

```python
raise APIException(
    status_code=400,
    detail="Bad request",
    error_code="bad_request"
)
```

#### `NotFoundError`

For 404 errors:

```python
raise NotFoundError("approval request", request_id)
# Returns: {"error": "not_found", "detail": "approval request '123' not found"}
```

#### `ValidationError`

For 422 validation errors:

```python
raise ValidationError("Invalid value", "field_name")
# Returns: {"error": "validation_error", "detail": "Validation error for field 'field_name': Invalid value"}
```

#### `InternalServerError`

For 500 errors:

```python
raise InternalServerError("Database failed", exc)
# Returns: {"error": "internal_server_error", "detail": "Database failed"}
```

### Global Exception Handlers

Exception handlers are registered automatically in `server.py`:

```python
from agenticfleet.api.exceptions import register_exception_handlers

app = FastAPI(...)
register_exception_handlers(app)  # Registers all handlers
```

### Error Response Format

All errors follow this structure:

```json
{
  "error": "error_code",
  "detail": "Human-readable error message",
  "path": "/v1/approvals/123"
}
```

### Using in Routes

```python
from agenticfleet.api.exceptions import NotFoundError

@router.get("/approvals/{request_id}")
async def get_approval(
    request_id: str,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    approval = db.query(ApprovalRequest).filter_by(request_id=request_id).first()
    if not approval:
        raise NotFoundError("approval request", request_id)
    return ApprovalResponse.from_orm(approval)
```

---

## Configuration Management

### Overview

Configuration is managed through Pydantic Settings, providing:

- **Type-safe access** - IDE autocomplete and type checking
- **Environment variable support** - Override via `.env` file
- **Validation** - Invalid values caught at startup
- **Single source of truth** - All settings in one place

### Accessing Settings

```python
from agenticfleet.core.settings import settings

# Type-safe access
redis_url = settings.redis_url  # str
ttl = settings.redis_ttl_seconds  # int
timeout = settings.workflow_timeout_seconds  # float
```

### Available Settings

Located in `src/agenticfleet/core/settings.py`:

```python
class AppSettings(BaseSettings):
    # API Configuration
    api_title: str = "AgenticFleet API"
    api_version: str = "0.5.5"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_ttl_seconds: int = 3600
    redis_enabled: bool = True

    # Workflow Configuration
    workflow_timeout_seconds: float = 120.0
    default_workflow_id: str = "magentic_fleet"

    # Database Configuration
    database_url: str = "sqlite:///var/agenticfleet/approvals.db"

    # CORS Configuration
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
```

### Environment Variables

Override defaults via `.env` file:

```bash
# .env
REDIS_URL=redis://production-server:6379
REDIS_TTL_SECONDS=7200
WORKFLOW_TIMEOUT_SECONDS=300
CORS_ORIGINS=["https://app.example.com"]
```

### Using Settings

```python
from agenticfleet.core.settings import settings

def create_app() -> FastAPI:
    # Use settings instead of os.getenv()
    redis_client = RedisClient(
        redis_url=settings.redis_url,
        ttl_seconds=settings.redis_ttl_seconds,
    )

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        ...
    )
```

---

## Health Check Endpoint

### Overview

The `/health` endpoint provides comprehensive system health information:

- **Dependency status** - Database, Redis connectivity
- **System metrics** - Background tasks, versions
- **HTTP status codes** - 200 for healthy, 503 for degraded

### Endpoint

```
GET /health
```

### Response Format

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "0.5.5",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "background_tasks": 3
  }
}
```

### Status Codes

- **200 OK** - All dependencies healthy
- **503 Service Unavailable** - One or more dependencies unhealthy

### Usage

```bash
# Check health
curl http://localhost:8000/health

# Use in monitoring
if curl -f http://localhost:8000/health; then
    echo "Service is healthy"
else
    echo "Service is degraded"
fi
```

### Kubernetes Integration

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## API Reference

### Approval Endpoints

#### Create Approval Request

```http
POST /v1/approvals
Content-Type: application/json

{
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "details": {
    "operation_type": "code_execution",
    "code": "print('Hello')"
  }
}
```

**Response**: `201 Created`

```json
{
  "request_id": "abc-123-def-456"
}
```

#### Respond to Approval

```http
POST /v1/approvals/{request_id}
Content-Type: application/json

{
  "decision": "approved",
  "reason": "Code looks safe",
  "modified_code": null
}
```

**Response**: `200 OK`

```json
{
  "status": "approved",
  "decision": "approved",
  "details": {
    "decision_reason": "Code looks safe"
  }
}
```

### Health Check

```http
GET /health
```

**Response**: `200 OK` or `503 Service Unavailable`

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "0.5.5",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "background_tasks": 0
  }
}
```

---

## Best Practices

### 1. Always Use Pydantic Models

✅ **Good**:

```python
@router.post("/items")
async def create_item(item: ItemCreate) -> ItemResponse:
    ...
```

❌ **Bad**:

```python
@router.post("/items")
async def create_item(request: Request) -> JSONResponse:
    data = await request.json()  # No validation!
    ...
```

### 2. Use Dependency Injection for Database

✅ **Good**:

```python
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    ...
```

❌ **Bad**:

```python
async def create_item(item: ItemCreate) -> ItemResponse:
    db = SessionLocal()  # Manual session management
    try:
        ...
        db.commit()
    except:
        db.rollback()
```

### 3. Use Custom Exceptions

✅ **Good**:

```python
if not item:
    raise NotFoundError("item", item_id)
```

❌ **Bad**:

```python
if not item:
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"}
    )
```

### 4. Access Settings from Config

✅ **Good**:

```python
from agenticfleet.core.settings import settings

redis_url = settings.redis_url
```

❌ **Bad**:

```python
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
```

---

## Examples

### Complete Example: Creating an Approval

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from agenticfleet.api.exceptions import InternalServerError
from agenticfleet.api.models.approval import CreateApprovalRequest
from agenticfleet.persistance.database import ApprovalRequest, get_db

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])

@router.post("")
async def create_approval_request(
    request: CreateApprovalRequest,  # Pydantic validation
    db: Session = Depends(get_db),  # Automatic transaction management
) -> JSONResponse:
    """Create a new approval request."""
    try:
        approval_request = ApprovalRequest(
            request_id=str(uuid4()),
            conversation_id=request.conversation_id,  # Validated
            details=request.details,  # Validated
        )
        db.add(approval_request)
        # Commit happens automatically on success
        # Rollback happens automatically on exception

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"request_id": approval_request.request_id},
        )
    except Exception as exc:
        # Rollback happens automatically via get_db dependency
        raise InternalServerError(
            "Failed to create approval request",
            exc
        ) from exc
```

### Error Handling Example

```python
from agenticfleet.api.exceptions import NotFoundError, ValidationError

@router.get("/approvals/{request_id}")
async def get_approval(
    request_id: str,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Get approval request by ID."""
    # Validate request_id format
    if not request_id or len(request_id) < 1:
        raise ValidationError("Invalid request ID", "request_id")

    # Query database
    approval = db.query(ApprovalRequest).filter_by(request_id=request_id).first()

    # Handle not found
    if not approval:
        raise NotFoundError("approval request", request_id)

    return ApprovalResponse.from_orm(approval)
```

---

## Troubleshooting

### Database Transactions Not Committing

**Problem**: Changes not persisted to database.

**Solution**: Ensure you're using `Depends(get_db)`:

```python
async def my_route(db: Session = Depends(get_db)):
    # get_db handles commit automatically
```

### Validation Errors Not Clear

**Problem**: Validation errors lack detail.

**Solution**: Use Pydantic models with Field descriptions:

```python
conversation_id: str = Field(
    ...,
    min_length=1,
    description="Conversation ID (UUID format)",
)
```

### Settings Not Loading

**Problem**: Settings have wrong values.

**Solution**: Check `.env` file and environment variables:

```bash
# Settings load from .env file
# Check for typos or missing env vars
```

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

**Last Updated**: Current Session
**Maintained By**: AgenticFleet Team
