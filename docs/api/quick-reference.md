# Quick Reference Guide - FastAPI Improvements

**Version**: 0.5.5
**Quick Reference for Developers**

---

## 🚀 Creating a New Endpoint

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from agenticfleet.api.exceptions import NotFoundError
from agenticfleet.api.models.your_model import YourRequestModel
from agenticfleet.persistance.database import get_db

router = APIRouter(prefix="/v1/your-resource", tags=["your-resource"])

@router.post("")
async def create_resource(
    request: YourRequestModel,  # Pydantic validation
    db: Session = Depends(get_db),  # Auto transaction management
) -> JSONResponse:
    """Create a new resource."""
    resource = Resource(**request.model_dump())
    db.add(resource)
    # Commit happens automatically
    return JSONResponse(status_code=201, content={"id": resource.id})
```

---

## ✅ Checklist for New Endpoints

- [ ] Use Pydantic model for request body
- [ ] Use `Depends(get_db)` for database access
- [ ] Use custom exceptions (`NotFoundError`, etc.)
- [ ] Add docstring
- [ ] Handle edge cases (not found, validation)
- [ ] Write tests

---

## 📝 Common Patterns

### Create Resource

```python
@router.post("")
async def create(request: CreateModel, db: Session = Depends(get_db)):
    item = Resource(**request.model_dump())
    db.add(item)
    return ResponseModel.from_orm(item)
```

### Get Resource

```python
@router.get("/{id}")
async def get(id: str, db: Session = Depends(get_db)):
    item = db.query(Resource).filter_by(id=id).first()
    if not item:
        raise NotFoundError("resource", id)
    return ResponseModel.from_orm(item)
```

### Update Resource

```python
@router.put("/{id}")
async def update(id: str, request: UpdateModel, db: Session = Depends(get_db)):
    item = db.query(Resource).filter_by(id=id).first()
    if not item:
        raise NotFoundError("resource", id)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    return ResponseModel.from_orm(item)
```

### Delete Resource

```python
@router.delete("/{id}")
async def delete(id: str, db: Session = Depends(get_db)):
    item = db.query(Resource).filter_by(id=id).first()
    if not item:
        raise NotFoundError("resource", id)
    db.delete(item)
    return Response(status_code=204)
```

---

## 🔧 Imports Cheat Sheet

```python
# Database
from agenticfleet.persistance.database import get_db

# Exceptions
from agenticfleet.api.exceptions import (
    NotFoundError,
    ValidationError,
    InternalServerError,
    APIException,
)

# Configuration
from agenticfleet.core.settings import settings

# Models (create your own)
from agenticfleet.api.models.your_model import YourRequestModel
```

---

## ⚠️ Exception Types

| Exception             | Status  | When to Use              |
| --------------------- | ------- | ------------------------ |
| `NotFoundError`       | 404     | Resource not found       |
| `ValidationError`     | 422     | Business rule validation |
| `InternalServerError` | 500     | Unexpected errors        |
| `APIException`        | 400-499 | Custom error codes       |

---

## ⚙️ Settings Cheat Sheet

```python
from agenticfleet.core.settings import settings

# Access settings
redis_url = settings.redis_url
ttl = settings.redis_ttl_seconds
timeout = settings.workflow_timeout_seconds
```

---

## 📋 Request Model Template

```python
from pydantic import BaseModel, Field
from typing import Optional

class CreateResourceRequest(BaseModel):
    """Request model for creating resources."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Resource name",
        examples=["My Resource"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional description",
    )
```

---

## 🧪 Testing Template

```python
def test_create_resource(client: TestClient):
    """Test resource creation."""
    response = client.post(
        "/v1/resources",
        json={"name": "Test", "description": "Test desc"},
    )
    assert response.status_code == 201
    assert "id" in response.json()

def test_not_found(client: TestClient):
    """Test NotFoundError."""
    response = client.get("/v1/resources/nonexistent")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
```

---

## 🔍 Common Issues & Solutions

| Issue                | Solution                |
| -------------------- | ----------------------- |
| Changes not saving   | Use `Depends(get_db)`   |
| Validation errors    | Use Pydantic models     |
| Inconsistent errors  | Use custom exceptions   |
| Config not loading   | Check `.env` file       |
| Health check failing | Check dependency status |

---

**Quick Links**: [Full Docs](./api/fastapi-best-practices.md) | [Developer Guide](./api/developer-guide.md)
