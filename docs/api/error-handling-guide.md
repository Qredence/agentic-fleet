# Error Handling Guide

**Version**: 0.5.5
**Last Updated**: Current Session

---

## Overview

AgenticFleet uses centralized exception handling to provide consistent, structured error responses across all API endpoints.

---

## Error Response Format

All errors follow this consistent structure:

```json
{
  "error": "error_code",
  "detail": "Human-readable error message",
  "path": "/v1/approvals/123"
}
```

### Error Codes

| Error Code              | Status Code | Description               |
| ----------------------- | ----------- | ------------------------- |
| `not_found`             | 404         | Resource not found        |
| `validation_error`      | 422         | Request validation failed |
| `internal_server_error` | 500         | Internal server error     |
| `api_error`             | 400-499     | Generic API error         |

---

## Exception Types

### NotFoundError (404)

Used when a requested resource doesn't exist.

```python
from agenticfleet.api.exceptions import NotFoundError

@router.get("/approvals/{request_id}")
async def get_approval(request_id: str, db: Session = Depends(get_db)):
    approval = db.query(ApprovalRequest).filter_by(request_id=request_id).first()
    if not approval:
        raise NotFoundError("approval request", request_id)
    return approval
```

**Response**:

```json
{
  "error": "not_found",
  "detail": "approval request '123' not found",
  "path": "/v1/approvals/123"
}
```

---

### ValidationError (422)

Used for validation errors (alternative to Pydantic validation).

```python
from agenticfleet.api.exceptions import ValidationError

@router.post("/approvals")
async def create_approval(conversation_id: str):
    if not conversation_id or len(conversation_id) < 1:
        raise ValidationError("Invalid conversation ID", "conversation_id")
    ...
```

**Response**:

```json
{
  "error": "validation_error",
  "detail": "Validation error for field 'conversation_id': Invalid conversation ID",
  "path": "/v1/approvals"
}
```

---

### InternalServerError (500)

Used for unexpected server errors.

```python
from agenticfleet.api.exceptions import InternalServerError

@router.post("/approvals")
async def create_approval(request: CreateApprovalRequest, db: Session = Depends(get_db)):
    try:
        # Complex operation
        result = await complex_operation()
        return result
    except Exception as exc:
        raise InternalServerError("Failed to create approval", exc) from exc
```

**Response**:

```json
{
  "error": "internal_server_error",
  "detail": "Failed to create approval",
  "path": "/v1/approvals"
}
```

---

### APIException (Custom)

Base exception for custom error codes.

```python
from agenticfleet.api.exceptions import APIException

@router.post("/approvals")
async def create_approval(request: CreateApprovalRequest):
    if rate_limit_exceeded():
        raise APIException(
            status_code=429,
            detail="Rate limit exceeded",
            error_code="rate_limit_exceeded"
        )
```

**Response**:

```json
{
  "error": "rate_limit_exceeded",
  "detail": "Rate limit exceeded",
  "path": "/v1/approvals"
}
```

---

## Automatic Validation Errors

Pydantic validation errors are handled automatically:

### Request Validation

When a request fails Pydantic validation:

```python
class CreateApprovalRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)

# Client sends invalid request
POST /v1/approvals
{
  "conversation_id": ""  # Empty string - invalid
}
```

**Automatic Response**:

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

---

## Error Handling Patterns

### Pattern 1: Resource Not Found

```python
@router.get("/resources/{resource_id}")
async def get_resource(resource_id: str, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter_by(id=resource_id).first()
    if not resource:
        raise NotFoundError("resource", resource_id)
    return resource
```

### Pattern 2: Validation Before Processing

```python
@router.post("/resources")
async def create_resource(request: ResourceCreate, db: Session = Depends(get_db)):
    # Check business rules
    if duplicate_exists(request.name):
        raise ValidationError("Resource with this name already exists", "name")

    # Create resource
    resource = Resource(**request.model_dump())
    db.add(resource)
    return resource
```

### Pattern 3: Comprehensive Error Handling

```python
@router.post("/resources")
async def create_resource(request: ResourceCreate, db: Session = Depends(get_db)):
    try:
        # Validate business rules
        if duplicate_exists(request.name):
            raise ValidationError("Duplicate name", "name")

        # Create resource
        resource = Resource(**request.model_dump())
        db.add(resource)
        return resource

    except ValidationError:
        # Re-raise validation errors (422)
        raise
    except Exception as exc:
        # Handle unexpected errors (500)
        raise InternalServerError("Failed to create resource", exc) from exc
```

---

## HTTP Status Codes

| Status Code               | Usage               | Exception Type                |
| ------------------------- | ------------------- | ----------------------------- |
| 200 OK                    | Successful request  | N/A                           |
| 201 Created               | Resource created    | N/A                           |
| 400 Bad Request           | Invalid request     | `APIException`                |
| 404 Not Found             | Resource not found  | `NotFoundError`               |
| 422 Unprocessable Entity  | Validation failed   | `ValidationError` or Pydantic |
| 429 Too Many Requests     | Rate limit exceeded | `APIException`                |
| 500 Internal Server Error | Server error        | `InternalServerError`         |
| 503 Service Unavailable   | Service degraded    | Health check                  |

---

## Client Error Handling

### JavaScript/TypeScript

```typescript
try {
  const response = await fetch("/v1/approvals", {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();

    if (error.error === "not_found") {
      // Handle 404
      console.error("Resource not found:", error.detail);
    } else if (error.error === "validation_error") {
      // Handle 422
      console.error("Validation errors:", error.detail);
    } else {
      // Handle other errors
      console.error("API error:", error.detail);
    }
  }
} catch (error) {
  console.error("Network error:", error);
}
```

### Python

```python
import httpx

try:
    response = httpx.post("/v1/approvals", json=data)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    error_data = exc.response.json()

    if error_data["error"] == "not_found":
        print(f"Resource not found: {error_data['detail']}")
    elif error_data["error"] == "validation_error":
        print(f"Validation errors: {error_data['detail']}")
    else:
        print(f"API error: {error_data['detail']}")
except httpx.RequestError as exc:
    print(f"Network error: {exc}")
```

---

## Best Practices

### 1. Use Appropriate Exception Types

✅ **Good**:

```python
if not resource:
    raise NotFoundError("resource", resource_id)
```

❌ **Bad**:

```python
if not resource:
    raise APIException(404, "Not found")  # Less descriptive
```

### 2. Provide Context

✅ **Good**:

```python
raise NotFoundError("approval request", request_id)
# Returns: "approval request '123' not found"
```

❌ **Bad**:

```python
raise NotFoundError("Resource", None)
# Returns: "Resource not found" (less helpful)
```

### 3. Preserve Exception Chain

✅ **Good**:

```python
try:
    result = await operation()
except Exception as exc:
    raise InternalServerError("Operation failed", exc) from exc
```

### 4. Don't Expose Internals

✅ **Good**:

```python
raise InternalServerError("Failed to create resource", exc)
# Client sees: "Failed to create resource"
```

❌ **Bad**:

```python
raise InternalServerError(str(exc), exc)
# Client might see: "Database connection failed: connection refused..." (too detailed)
```

---

## Testing Error Handling

### Test NotFoundError

```python
def test_not_found_error(client: TestClient):
    """Test NotFoundError response."""
    response = client.get("/approvals/nonexistent-id")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
    assert "not found" in response.json()["detail"].lower()
```

### Test ValidationError

```python
def test_validation_error(client: TestClient):
    """Test ValidationError response."""
    response = client.post(
        "/approvals",
        json={"conversation_id": ""},  # Invalid
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
```

---

## Troubleshooting

### Error Not Caught

**Problem**: Exception not handled by global handler.

**Solution**: Ensure exception inherits from `APIException`:

```python
# ✅ Correct
raise NotFoundError("resource", id)

# ❌ Wrong - won't be caught by handler
raise ValueError("Not found")
```

### Error Response Missing Fields

**Problem**: Error response doesn't include `error` field.

**Solution**: Ensure you're using custom exceptions:

```python
# ✅ Correct
raise NotFoundError("resource", id)

# ❌ Wrong - returns different format
raise HTTPException(status_code=404, detail="Not found")
```

---

## Additional Resources

- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Exception Handling Guide](./fastapi-best-practices.md#exception-handling)
- [API Reference](./fastapi-best-practices.md)

---

**Last Updated**: Current Session
**Maintained By**: AgenticFleet Team
