# Developer Guide - FastAPI Improvements

**Version**: 0.5.5
**Audience**: Backend Developers

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Database Session Management](#database-session-management)
3. [Request Validation](#request-validation)
4. [Exception Handling](#exception-handling)
5. [Configuration Management](#configuration-management)
6. [Health Checks](#health-checks)
7. [Testing](#testing)
8. [Common Patterns](#common-patterns)

---

## Quick Start

### Adding a New Endpoint

When creating a new endpoint, follow these patterns:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agenticfleet.api.exceptions import NotFoundError
from agenticfleet.api.models.your_model import YourRequestModel
from agenticfleet.persistance.database import get_db

router = APIRouter(prefix="/v1/your-resource", tags=["your-resource"])

@router.post("")
async def create_resource(
    request: YourRequestModel,  # Pydantic model for validation
    db: Session = Depends(get_db),  # Automatic transaction management
) -> JSONResponse:
    """Create a new resource."""
    # Your implementation here
    # Commit happens automatically on success
    # Rollback happens automatically on exception
    ...
```

---

## Database Session Management

### Understanding the Pattern

The `get_db()` dependency automatically manages transactions:

1. **Yields** the database session
2. **Commits** on successful completion
3. **Rollbacks** on exceptions
4. **Closes** the session always

### Example: Creating a Resource

```python
@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Create a new item."""
    db_item = Item(**item.model_dump())
    db.add(db_item)
    # No manual commit needed - happens automatically
    # If exception occurs, rollback happens automatically
    db.flush()  # Get ID without committing
    return ItemResponse.from_orm(db_item)
```

### Example: Updating a Resource

```python
@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Update an existing item."""
    db_item = db.query(Item).filter_by(id=item_id).first()
    if not db_item:
        raise NotFoundError("item", item_id)

    # Update fields
    for field, value in item_update.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)

    # Commit happens automatically
    return ItemResponse.from_orm(db_item)
```

### Example: Error Handling

```python
@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Create a new item with error handling."""
    try:
        db_item = Item(**item.model_dump())
        db.add(db_item)
        # If this succeeds, commit happens automatically
        return ItemResponse.from_orm(db_item)
    except IntegrityError as exc:
        # Rollback happens automatically via get_db
        raise ValidationError("Item already exists", "name") from exc
```

---

## Request Validation

### Creating Request Models

Create Pydantic models in `src/agenticfleet/api/models/`:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ItemCreate(BaseModel):
    """Request model for creating items."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name",
        examples=["My Item"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Item description",
    )

    price: float = Field(
        ...,
        gt=0,
        description="Item price (must be positive)",
    )
```

### Using in Routes

```python
@router.post("/items")
async def create_item(
    item: ItemCreate,  # FastAPI validates automatically
    db: Session = Depends(get_db),
) -> ItemResponse:
    # item.name is guaranteed to be non-empty string
    # item.price is guaranteed to be positive float
    # item.description is Optional[str] or None
    ...
```

### Validation Error Handling

Validation errors are handled automatically:

```python
# Client sends invalid data
POST /items
{
  "name": "",  # Empty string - invalid
  "price": -10  # Negative - invalid
}

# FastAPI automatically returns:
{
  "error": "validation_error",
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    },
    {
      "loc": ["body", "price"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ],
  "path": "/items"
}
```

---

## Exception Handling

### Using Custom Exceptions

Import and use custom exceptions:

```python
from agenticfleet.api.exceptions import (
    NotFoundError,
    ValidationError,
    InternalServerError,
)

@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Get item by ID."""
    # Validate ID format
    if not item_id or len(item_id) < 1:
        raise ValidationError("Invalid item ID", "item_id")

    # Query database
    item = db.query(Item).filter_by(id=item_id).first()

    # Handle not found
    if not item:
        raise NotFoundError("item", item_id)

    return ItemResponse.from_orm(item)
```

### Exception Response Format

All exceptions return consistent format:

```json
{
  "error": "not_found",
  "detail": "item '123' not found",
  "path": "/v1/items/123"
}
```

### Handling Different Error Types

```python
@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Create item with comprehensive error handling."""
    try:
        # Check for duplicates
        existing = db.query(Item).filter_by(name=item.name).first()
        if existing:
            raise ValidationError("Item with this name already exists", "name")

        # Create item
        db_item = Item(**item.model_dump())
        db.add(db_item)

        return ItemResponse.from_orm(db_item)
    except ValidationError:
        # Re-raise validation errors (status 422)
        raise
    except Exception as exc:
        # Handle unexpected errors (status 500)
        raise InternalServerError(
            "Failed to create item",
            exc
        ) from exc
```

---

## Configuration Management

### Accessing Settings

```python
from agenticfleet.core.settings import settings

# Type-safe access
redis_url = settings.redis_url  # str
ttl = settings.redis_ttl_seconds  # int
timeout = settings.workflow_timeout_seconds  # float
```

### Using Settings in Code

```python
from agenticfleet.core.settings import settings

def create_redis_client():
    """Create Redis client using settings."""
    return RedisClient(
        redis_url=settings.redis_url,
        ttl_seconds=settings.redis_ttl_seconds,
    )

async def run_workflow():
    """Run workflow with timeout from settings."""
    result = await asyncio.wait_for(
        workflow.run(),
        timeout=settings.workflow_timeout_seconds,
    )
    return result
```

### Environment Variable Overrides

Settings can be overridden via `.env` file:

```bash
# .env
REDIS_URL=redis://production-server:6379
REDIS_TTL_SECONDS=7200
WORKFLOW_TIMEOUT_SECONDS=300
```

### Adding New Settings

1. Add to `AppSettings` class:

```python
class AppSettings(BaseSettings):
    # Existing settings...

    # New setting
    new_feature_enabled: bool = Field(
        default=True,
        description="Enable new feature",
    )
```

2. Access in code:

```python
if settings.new_feature_enabled:
    # Use new feature
    ...
```

---

## Health Checks

### Adding Dependency Checks

Extend the health check in `src/agentic_fleet/api/routers/health.py`:

```python
@router.get("/health")  # Mounted at /v1/system in app.py
async def health(state: BackendState = Depends(get_backend)) -> JSONResponse:
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api_version,
        "checks": {
            "database": "unknown",
            "redis": "unknown",
            "background_tasks": len(state.background_tasks),
            "your_service": "unknown",  # Add your check
        },
    }

    # Add your service check
    try:
        # Check your service
        await your_service.ping()
        health_status["checks"]["your_service"] = "healthy"
    except Exception as exc:
        health_status["checks"]["your_service"] = f"unhealthy: {exc}"
        health_status["status"] = "degraded"

    # Determine status code
    status_code = (
        status.HTTP_200_OK if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(content=health_status, status_code=status_code)
```

---

## Testing

### Testing Database Sessions

```python
def test_create_item(db_session: Session):
    """Test item creation with automatic transaction."""
    item = Item(name="Test", price=10.0)
    db_session.add(item)
    db_session.commit()  # Manual commit in test

    # Verify item was saved
    retrieved = db_session.query(Item).filter_by(name="Test").first()
    assert retrieved is not None

    # Cleanup
    db_session.delete(retrieved)
    db_session.commit()
```

### Testing Request Validation

```python
def test_create_item_validation(client: TestClient):
    """Test request validation."""
    # Invalid request (empty name)
    response = client.post(
        "/items",
        json={"name": "", "price": 10.0},
    )

    assert response.status_code == 422
    assert "validation_error" in response.json()["error"]
```

### Testing Exception Handling

```python
def test_not_found_error(client: TestClient):
    """Test NotFoundError handling."""
    response = client.get("/items/nonexistent")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
```

---

## Common Patterns

### Pattern 1: Create Resource

```python
@router.post("/resources")
async def create_resource(
    request: ResourceCreate,
    db: Session = Depends(get_db),
) -> ResourceResponse:
    """Create a new resource."""
    resource = Resource(**request.model_dump())
    db.add(resource)
    return ResourceResponse.from_orm(resource)
```

### Pattern 2: Get Resource by ID

```python
@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
) -> ResourceResponse:
    """Get resource by ID."""
    resource = db.query(Resource).filter_by(id=resource_id).first()
    if not resource:
        raise NotFoundError("resource", resource_id)
    return ResourceResponse.from_orm(resource)
```

### Pattern 3: Update Resource

```python
@router.put("/resources/{resource_id}")
async def update_resource(
    resource_id: str,
    request: ResourceUpdate,
    db: Session = Depends(get_db),
) -> ResourceResponse:
    """Update resource."""
    resource = db.query(Resource).filter_by(id=resource_id).first()
    if not resource:
        raise NotFoundError("resource", resource_id)

    # Update only provided fields
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)

    return ResourceResponse.from_orm(resource)
```

### Pattern 4: Delete Resource

```python
@router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Delete resource."""
    resource = db.query(Resource).filter_by(id=resource_id).first()
    if not resource:
        raise NotFoundError("resource", resource_id)

    db.delete(resource)
    # Commit happens automatically
    return Response(status_code=204)
```

---

## Code Checklist

When creating a new endpoint, ensure:

- [ ] Uses Pydantic model for request validation
- [ ] Uses `Depends(get_db)` for database access
- [ ] Uses custom exceptions for errors
- [ ] Has proper docstring
- [ ] Returns appropriate response model
- [ ] Handles edge cases (not found, validation errors)
- [ ] Has tests

---

## Next Steps

- Review [API Reference](./fastapi-best-practices.md)
- Check [Test Examples](../tests/test_improvements.py)
- See [FastAPI Docs](https://fastapi.tiangolo.com/)

---

**Last Updated**: Current Session
**Maintained By**: AgenticFleet Team
