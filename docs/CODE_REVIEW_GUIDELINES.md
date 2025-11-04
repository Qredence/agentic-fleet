# Code Review Guidelines

This document outlines the automated feedback criteria used for code reviews in the AgenticFleet project. These guidelines ensure consistent code quality, security, and maintainability.

## Table of Contents

- [Code Quality Standards](#code-quality-standards)
- [Security Best Practices](#security-best-practices)
- [Performance Considerations](#performance-considerations)
- [Type Safety & Documentation](#type-safety--documentation)
- [Testing Requirements](#testing-requirements)

## Code Quality Standards

### 1. Code Style & Formatting

**Required Tools:**
- `ruff` for linting (configured in `pyproject.toml`)
- `black` for formatting
- `mypy` for type checking

**Standards:**
- Line length: 100 characters
- Python version: 3.12+
- Import sorting: isort style (via ruff)
- Type hints: Required for all functions and methods

**Automated Checks:**
```bash
make check  # Runs lint + type-check
make format # Auto-formats code
```

### 2. Import Organization

**Required Order:**
1. Future imports (`from __future__ import annotations`)
2. Standard library imports
3. Third-party imports
4. Local application imports

**Example:**
```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from agentic_fleet.api.chat.service import ChatService
```

### 3. Function & Class Design

**Single Responsibility:**
- Each function/class should have one clear purpose
- Avoid functions longer than 50 lines
- Extract complex logic into helper functions

**Naming Conventions:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### 4. Error Handling

**Required Patterns:**
- Use specific exception types (not bare `except`)
- Provide meaningful error messages
- Log errors appropriately
- Clean up resources in `finally` blocks or use context managers

**Example:**
```python
async def process_request(request_id: str) -> Response:
    """Process a workflow request with proper error handling."""
    try:
        # Implementation
        return response
    except ValueError as e:
        logger.error(f"Invalid request {request_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing {request_id}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Security Best Practices

### 1. Input Validation

**Always validate:**
- User inputs
- API request payloads
- Configuration values
- File paths

**Use Pydantic models:**
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str = Field(..., regex=r"^[a-zA-Z0-9-]+$")
    
    @validator("message")
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v
```

### 2. Secrets Management

**Never:**
- Hardcode API keys, passwords, or tokens
- Commit `.env` files to git
- Log sensitive information

**Always:**
- Use environment variables
- Use `.env.example` for templates
- Redact sensitive data in logs

### 3. SQL Injection Prevention

**Use:**
- Parameterized queries
- ORM (SQLAlchemy) for database access
- Input sanitization

### 4. API Security

**Implement:**
- Rate limiting
- Authentication/authorization
- CORS configuration
- Request size limits
- Timeout settings

## Performance Considerations

### 1. Async/Await Usage

**Async operations for:**
- Database queries
- HTTP requests
- File I/O
- Long-running computations

**Example:**
```python
async def fetch_multiple_resources(ids: list[str]) -> list[Resource]:
    """Fetch resources concurrently for better performance."""
    tasks = [fetch_resource(id) for id in ids]
    return await asyncio.gather(*tasks)
```

### 2. Database Optimization

- Use connection pooling
- Implement proper indexing
- Avoid N+1 queries
- Use pagination for large result sets

### 3. Caching

- Cache expensive computations
- Use Redis for distributed caching
- Implement cache invalidation strategy
- Set appropriate TTLs

### 4. Resource Management

- Close database connections
- Release file handles
- Clean up temporary files
- Limit memory usage for large operations

## Type Safety & Documentation

### 1. Type Hints

**Required for:**
- All function parameters
- All function return values
- Class attributes
- Complex data structures

**Example:**
```python
from typing import Any, TypedDict

class WorkflowConfig(TypedDict):
    name: str
    max_rounds: int
    agents: list[str]

def create_workflow(
    config: WorkflowConfig,
    context: dict[str, Any] | None = None
) -> MagenticFleet:
    """Create a workflow from configuration."""
    ...
```

### 2. Docstrings

**Required Format (Google Style):**
```python
def execute_workflow(
    workflow_id: str,
    input_data: dict[str, Any],
    timeout: int = 300
) -> WorkflowResult:
    """Execute a workflow with the given input.
    
    Args:
        workflow_id: Unique identifier for the workflow
        input_data: Input parameters for workflow execution
        timeout: Maximum execution time in seconds (default: 300)
        
    Returns:
        WorkflowResult containing execution status and output
        
    Raises:
        ValueError: If workflow_id is invalid
        TimeoutError: If execution exceeds timeout
        WorkflowError: If workflow execution fails
        
    Example:
        >>> result = execute_workflow(
        ...     "magentic-fleet",
        ...     {"task": "analyze data"},
        ...     timeout=600
        ... )
    """
    ...
```

### 3. Documentation Requirements

**Every module must have:**
- Module-level docstring explaining purpose
- Class docstrings with attributes documented
- Function docstrings with Args, Returns, Raises
- Complex algorithms should have inline comments

## Testing Requirements

### 1. Test Coverage

**Minimum Coverage:** 90% overall, 100% for critical paths

**Required Tests:**
- Unit tests for all functions/classes
- Integration tests for API endpoints
- End-to-end tests for workflows
- Edge case handling

### 2. Test Organization

**Structure:**
```
tests/
├── test_api_*.py      # API endpoint tests
├── test_workflows_*.py # Workflow tests
├── test_unit_*.py     # Unit tests
└── test_e2e_*.py      # End-to-end tests
```

### 3. Test Quality

**Good tests are:**
- Independent (can run in any order)
- Repeatable (same input → same output)
- Fast (< 1 second for unit tests)
- Meaningful (test behavior, not implementation)

**Example:**
```python
@pytest.mark.asyncio
async def test_chat_endpoint_validates_input():
    """Test that chat endpoint rejects invalid input."""
    # Arrange
    invalid_request = {"message": "", "conversation_id": "123"}
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(**invalid_request)
    
    assert "message cannot be empty" in str(exc_info.value)
```

### 4. Mocking

**Mock external dependencies:**
- API calls
- Database operations
- File system access
- Time-dependent operations

**Example:**
```python
@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client for testing."""
    mock = mocker.patch("openai.ChatCompletion.create")
    mock.return_value = {
        "choices": [{"message": {"content": "Test response"}}]
    }
    return mock
```

## Automated Feedback Checklist

When reviewing code, check for:

### Code Quality
- [ ] Follows project style guidelines
- [ ] No linting errors (`ruff check`)
- [ ] Properly formatted (`black`)
- [ ] Type hints present and correct (`mypy`)
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Meaningful variable/function names

### Security
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] SQL injection prevented
- [ ] XSS prevention in place
- [ ] Authentication/authorization checked
- [ ] Sensitive data properly handled

### Performance
- [ ] Async/await used appropriately
- [ ] No N+1 queries
- [ ] Database queries optimized
- [ ] Caching implemented where beneficial
- [ ] Resource cleanup implemented

### Documentation
- [ ] All public functions have docstrings
- [ ] Complex logic has inline comments
- [ ] Module docstring present
- [ ] API endpoints documented
- [ ] README updated if needed

### Testing
- [ ] New functionality has tests
- [ ] Edge cases covered
- [ ] Tests are meaningful
- [ ] Coverage > 90%
- [ ] Tests pass locally

### Dependencies
- [ ] Minimal new dependencies added
- [ ] Dependencies have compatible licenses
- [ ] Security vulnerabilities checked
- [ ] Version constraints specified

## Review Process

### Automated Checks (CI)

1. **Linting:** `ruff check .`
2. **Formatting:** `black --check .`
3. **Type Checking:** `mypy src`
4. **Tests:** `pytest -v --cov`
5. **Security:** CodeQL, Bandit
6. **Build:** Package building and validation

### Manual Review Focus

1. **Architecture:** Does it fit the overall design?
2. **Complexity:** Is it simple and maintainable?
3. **Readability:** Can others understand it?
4. **Edge Cases:** Are all scenarios handled?
5. **Performance:** Are there bottlenecks?

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [pytest Documentation](https://docs.pytest.org/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## Enforcement

These guidelines are enforced through:
- **Pre-commit hooks** (optional, recommended)
- **CI/CD pipeline** (required)
- **Code review process** (required)
- **Automated feedback** (this system)

For questions or suggestions, please open an issue or discussion.
