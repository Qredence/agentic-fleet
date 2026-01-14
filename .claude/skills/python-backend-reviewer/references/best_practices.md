# Python Backend Best Practices

Fundamental principles and practices for writing maintainable Python backend code.

## Core Principles

### DRY (Don't Repeat Yourself)

Avoid duplicating code. If you write the same logic twice, extract it into a function or class.

**Good:**

```python
# utils/validation.py
def validate_email(email: str) -> None:
    if not email or "@" not in email:
        raise ValueError("Invalid email")

# Used everywhere
from utils.validation import validate_email
```

**Bad:**

```python
# Same validation logic copied in 10 different files
if not email or "@" not in email:
    raise ValueError("Invalid email")
```

### SOLID Principles

#### Single Responsibility Principle

Each class/function should have one reason to change.

**Good:**

```python
class UserRepository:
    def save(self, user: User): ...
    def find_by_id(self, user_id: str): ...

class EmailService:
    def send_welcome_email(self, user: User): ...
```

**Bad:**

```python
class UserManager:
    def save(self, user: User): ...
    def find_by_id(self, user_id: str): ...
    def send_welcome_email(self, user: User): ...
    def hash_password(self, password: str): ...
```

#### Open/Closed Principle

Open for extension, closed for modification.

**Good:**

```python
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def process(self, amount: float): ...

class StripeProcessor(PaymentProcessor):
    def process(self, amount: float): ...

class PayPalProcessor(PaymentProcessor):
    def process(self, amount: float): ...
```

#### Dependency Inversion

Depend on abstractions, not concretions.

**Good:**

```python
class OrderService:
    def __init__(self, payment_processor: PaymentProcessor):
        self.payment = payment_processor  # Depends on abstraction

# Can inject any processor
service = OrderService(StripeProcessor())
```

## Code Organization

### Module Structure

```
backend/
├── api/              # API endpoints
│   ├── routes/       # Route handlers
│   └── dependencies/ # FastAPI/Flask dependencies
├── services/         # Business logic
├── repositories/     # Data access
├── models/           # Data models
├── schemas/          # Validation schemas (Pydantic)
├── utils/            # Shared utilities
│   ├── validation/
│   ├── formatting/
│   └── helpers/
└── config/           # Configuration
```

### Import Guidelines

1. **Group imports:** Standard library, third-party, local
2. **Use absolute imports:** `from myapp.utils import helper`
3. **Avoid wildcards:** Never `from module import *`
4. **Import what you need:** `from module import specific_function`

**Good:**

```python
# Standard library
import json
import logging
from typing import Any

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from myapp.services import UserService
from myapp.utils import validate_email
```

## Type Hints

Always use type hints for function signatures and complex variables.

**Good:**

```python
def process_order(order_id: str, items: list[dict[str, Any]]) -> OrderResult:
    ...

# Modern Python 3.10+ syntax
def get_user(user_id: str) -> User | None:
    ...
```

**Avoid:**

```python
def process_order(order_id, items):  # No type hints
    ...

# Old-style Optional
from typing import Optional
def get_user(user_id: str) -> Optional[User]:  # Use | None instead
    ...
```

## Error Handling

### Specific Exceptions

**Good:**

```python
try:
    result = parse_json(data)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    raise ValueError("Invalid JSON format") from e
```

**Bad:**

```python
try:
    result = parse_json(data)
except Exception:  # Too broad
    pass  # Silently fails
```

### Custom Exceptions

Create domain-specific exceptions.

```python
class UserNotFoundError(Exception):
    """Raised when user is not found."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")

# Usage
def get_user(user_id: str) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    return user
```

## Async Best Practices

### Use Async Consistently

**Good:**

```python
async def fetch_user_data(user_id: str) -> dict:
    user = await db.get_user(user_id)
    orders = await db.get_orders(user_id)
    return {"user": user, "orders": orders}
```

**Bad:**

```python
async def fetch_user_data(user_id: str) -> dict:
    user = db.get_user(user_id)  # Blocking call in async function!
    orders = await db.get_orders(user_id)
    return {"user": user, "orders": orders}
```

### Parallel Async Operations

**Good:**

```python
import asyncio

async def fetch_all_data(user_ids: list[str]) -> list[dict]:
    tasks = [fetch_user_data(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)
```

## Logging

### Structured Logging

**Good:**

```python
import structlog

logger = structlog.get_logger()

def process_order(order_id: str):
    logger.info("processing_order", order_id=order_id)
    try:
        result = process(order_id)
        logger.info("order_processed", order_id=order_id, result=result)
        return result
    except Exception as e:
        logger.exception("order_processing_failed", order_id=order_id, error=str(e))
        raise
```

### Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical failures requiring immediate attention

## Configuration

### Environment-Based Config

**Good:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Bad:**

```python
# Hardcoded configuration
DATABASE_URL = "postgresql://localhost/mydb"
API_KEY = "sk-1234567890"
```

## Testing

### Test Structure

```python
import pytest

def test_validate_email_valid():
    """Test that valid emails pass validation."""
    # Arrange
    email = "user@example.com"

    # Act & Assert
    validate_email(email)  # Should not raise

def test_validate_email_invalid():
    """Test that invalid emails raise ValueError."""
    # Arrange
    email = "invalid-email"

    # Act & Assert
    with pytest.raises(ValueError):
        validate_email(email)
```

### Fixtures for Reusability

```python
@pytest.fixture
def sample_user():
    return User(
        id="123",
        email="test@example.com",
        name="Test User"
    )

def test_process_user(sample_user):
    result = process_user(sample_user)
    assert result.status == "processed"
```

## Database Best Practices

### Use ORMs Properly

**Good:**

```python
# Eager loading to avoid N+1
users = session.query(User).options(
    joinedload(User.orders)
).all()

for user in users:
    print(user.orders)  # No additional queries
```

**Bad:**

```python
# N+1 query problem
users = session.query(User).all()

for user in users:
    print(user.orders)  # Fires a query for each user!
```

### Connection Management

**Good:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## API Design

### RESTful Endpoints

```python
# Good RESTful design
GET    /api/users           # List users
GET    /api/users/{id}      # Get specific user
POST   /api/users           # Create user
PUT    /api/users/{id}      # Update user
DELETE /api/users/{id}      # Delete user
```

### Input Validation

**Good:**

```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)

@app.post("/users")
async def create_user(request: CreateUserRequest):
    # Request is automatically validated
    user = await user_service.create(request)
    return user
```

## Code Style

### Use Modern Python Syntax

**Good (Python 3.10+):**

```python
def get_user(user_id: str) -> User | None:
    match user_type:
        case "admin":
            return AdminUser()
        case "regular":
            return RegularUser()
        case _:
            return None
```

### Naming Conventions

- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Descriptive names over abbreviations

**Good:**

```python
def calculate_user_score(user: User) -> int:
    MAX_SCORE = 100
    return min(user.points, MAX_SCORE)
```

**Bad:**

```python
def calc_usr_scr(u):  # Unclear abbreviations
    ms = 100
    return min(u.pts, ms)
```

## When to Abstract vs. When to Duplicate

### When to Abstract

✅ Same logic used in 3+ places
✅ Complex logic that benefits from naming
✅ Logic that changes frequently across the codebase
✅ Cross-cutting concerns (logging, validation, auth)

### When to Duplicate

✅ Simple logic (1-2 lines) that's easier to read inline
✅ Context-specific behavior that might diverge
✅ Temporary code that will change soon
✅ Tests (each test should be independent)

**Example - OK to duplicate:**

```python
# Simple checks can be duplicated
if not user:
    return None

if not product:
    return None
```

**Example - Should abstract:**

```python
# Complex validation should be extracted
def validate_order(order):
    if not order.items:
        raise ValueError("Order must have items")
    if order.total < 0:
        raise ValueError("Order total cannot be negative")
    if not order.customer_id:
        raise ValueError("Order must have customer")
    # ... 10 more validation rules
```

## Performance Considerations

### Use Generators for Large Datasets

**Good:**

```python
def process_large_file(filepath: str):
    with open(filepath) as f:
        for line in f:  # Generator, memory efficient
            yield process_line(line)
```

**Bad:**

```python
def process_large_file(filepath: str):
    with open(filepath) as f:
        lines = f.readlines()  # Loads entire file into memory
        return [process_line(line) for line in lines]
```

### Batch Database Operations

**Good:**

```python
# Bulk insert
users = [User(name=name) for name in names]
session.bulk_save_objects(users)
session.commit()
```

**Bad:**

```python
# Individual inserts
for name in names:
    user = User(name=name)
    session.add(user)
    session.commit()  # Commits for each user!
```

## Security

### Never Trust User Input

```python
# Always validate and sanitize
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    username: str

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v
```

### Use Parameterized Queries

**Good:**

```python
# Parameterized query (safe from SQL injection)
user = session.execute(
    "SELECT * FROM users WHERE email = :email",
    {"email": user_email}
).first()
```

**Bad:**

```python
# String interpolation (SQL injection risk!)
user = session.execute(
    f"SELECT * FROM users WHERE email = '{user_email}'"
).first()
```

## Documentation

### Docstrings

```python
def calculate_discount(price: float, customer_tier: str) -> float:
    """
    Calculate discount based on customer tier.

    Args:
        price: Original price of the item
        customer_tier: Customer tier ("bronze", "silver", "gold")

    Returns:
        Discounted price

    Raises:
        ValueError: If customer_tier is invalid
    """
    # Implementation...
```

## Code Review Checklist

- [ ] No duplicate code
- [ ] Functions are small and focused
- [ ] Type hints are present
- [ ] Error handling is specific
- [ ] Tests are included
- [ ] Code follows naming conventions
- [ ] No hardcoded values
- [ ] Performance is reasonable
- [ ] Security considerations addressed
