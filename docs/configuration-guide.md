# Configuration Guide

**Version**: 0.5.5
**Last Updated**: Current Session

---

## Overview

AgenticFleet uses Pydantic Settings for type-safe, validated configuration management. All settings can be overridden via environment variables or `.env` file.

---

## Configuration Sources

Configuration is loaded in this order (later sources override earlier):

1. **Default values** (in `AppSettings` class)
2. **Environment variables** (from system environment)
3. **`.env` file** (project root)

---

## Available Settings

### API Configuration

```python
api_title: str = "AgenticFleet API"
api_version: str = "0.5.5"
api_description: str = "Multi-agent orchestration system..."
```

**Environment Variables**: None (internal use)

---

### Redis Configuration

```python
redis_url: str = "redis://localhost:6379"
redis_ttl_seconds: int = 3600
redis_enabled: bool = True
```

**Environment Variables**:

```bash
REDIS_URL=redis://your-server:6379
REDIS_TTL_SECONDS=7200
REDIS_ENABLED=true
```

**Example**:

```bash
# Production Redis Cloud
REDIS_URL=redis://default:password@redis-12345.c259.us-central1-2.gce.redns.redis-cloud.com:12345
REDIS_TTL_SECONDS=7200
```

---

### Workflow Configuration

```python
workflow_timeout_seconds: float = 120.0
default_workflow_id: str = "magentic_fleet"
```

**Environment Variables**:

```bash
WORKFLOW_TIMEOUT_SECONDS=300
DEFAULT_WORKFLOW_ID=collaboration
```

---

### Database Configuration

```python
database_url: str = "sqlite:///var/agenticfleet/approvals.db"
```

**Environment Variables**:

```bash
DATABASE_URL=sqlite:///var/agenticfleet/approvals.db
```

**Example** (PostgreSQL):

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/agenticfleet
```

---

### CORS Configuration

```python
cors_origins: list[str] = ["*"]
cors_allow_credentials: bool = True
cors_allow_methods: list[str] = ["*"]
cors_allow_headers: list[str] = ["*"]
```

**Environment Variables**:

```bash
CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]
CORS_ALLOW_CREDENTIALS=true
```

**Note**: For list values, use JSON array format in `.env` file.

---

### Logging Configuration

```python
log_level: str = "INFO"
```

**Environment Variables**:

```bash
LOG_LEVEL=DEBUG
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

### Server Configuration

```python
server_host: str = "0.0.0.0"
server_port: int = 8000
```

**Environment Variables**:

```bash
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
```

---

## .env File Example

Create `.env` file in project root:

```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_TTL_SECONDS=3600
REDIS_ENABLED=true

# Database Configuration
DATABASE_URL=sqlite:///var/agenticfleet/approvals.db

# Workflow Configuration
WORKFLOW_TIMEOUT_SECONDS=300
DEFAULT_WORKFLOW_ID=magentic_fleet

# CORS Configuration
CORS_ORIGINS=["*"]
CORS_ALLOW_CREDENTIALS=true

# Logging
LOG_LEVEL=INFO

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

---

## Accessing Settings in Code

### Direct Access

```python
from agenticfleet.core.settings import settings

# Type-safe access
redis_url = settings.redis_url
ttl = settings.redis_ttl_seconds
```

### Using in Functions

```python
from agenticfleet.core.settings import settings

def create_redis_client():
    """Create Redis client using settings."""
    return RedisClient(
        redis_url=settings.redis_url,
        ttl_seconds=settings.redis_ttl_seconds,
    )
```

### Using in Routes

```python
from agenticfleet.core.settings import settings

@router.get("/config")
async def get_config():
    """Return current configuration (without secrets)."""
    return {
        "redis_enabled": settings.redis_enabled,
        "workflow_timeout": settings.workflow_timeout_seconds,
    }
```

---

## Production Configuration

### Recommended Production Settings

```bash
# .env.production

# Redis (Production)
REDIS_URL=redis://your-production-redis:6379
REDIS_TTL_SECONDS=7200
REDIS_ENABLED=true

# Database (Production)
DATABASE_URL=postgresql://user:pass@db-host:5432/agenticfleet

# CORS (Production - restrict origins)
CORS_ORIGINS=["https://app.yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true

# Logging (Production)
LOG_LEVEL=INFO

# Workflow (Production)
WORKFLOW_TIMEOUT_SECONDS=600
```

---

## Development Configuration

### Recommended Development Settings

```bash
# .env.development

# Redis (Local)
REDIS_URL=redis://localhost:6379
REDIS_TTL_SECONDS=3600
REDIS_ENABLED=true

# Database (Local SQLite)
DATABASE_URL=sqlite:///var/agenticfleet/approvals.db

# CORS (Development - allow all)
CORS_ORIGINS=["*"]
CORS_ALLOW_CREDENTIALS=true

# Logging (Development)
LOG_LEVEL=DEBUG

# Workflow (Development - shorter timeout)
WORKFLOW_TIMEOUT_SECONDS=120
```

---

## Configuration Validation

Settings are validated at startup:

### Type Validation

```python
# Invalid: Wrong type
REDIS_TTL_SECONDS=abc  # Error: must be integer

# Valid: Correct type
REDIS_TTL_SECONDS=3600  # OK
```

### Value Validation

```python
# Invalid: Negative timeout
WORKFLOW_TIMEOUT_SECONDS=-10  # Error: must be positive

# Valid: Positive timeout
WORKFLOW_TIMEOUT_SECONDS=300  # OK
```

---

## Troubleshooting

### Settings Not Loading

**Problem**: Settings have default values instead of environment values.

**Solution**:

1. Check `.env` file exists in project root
2. Verify environment variable names match exactly
3. Restart the application

### Type Errors

**Problem**: Type errors when accessing settings.

**Solution**: Settings are type-safe. Use them directly:

```python
# ✅ Correct
redis_url: str = settings.redis_url

# ❌ Wrong - unnecessary type checking
if isinstance(settings.redis_url, str):
    redis_url = settings.redis_url
```

### List Values Not Working

**Problem**: List values like `CORS_ORIGINS` not parsed correctly.

**Solution**: Use JSON array format in `.env`:

```bash
# ✅ Correct
CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]

# ❌ Wrong
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

---

## Adding New Settings

### Step 1: Add to AppSettings

Edit `src/agenticfleet/core/settings.py`:

```python
class AppSettings(BaseSettings):
    # Existing settings...

    # New setting
    new_feature_enabled: bool = Field(
        default=True,
        description="Enable new feature",
    )

    new_feature_timeout: int = Field(
        default=60,
        ge=1,
        description="Timeout for new feature",
    )
```

### Step 2: Use in Code

```python
from agenticfleet.core.settings import settings

if settings.new_feature_enabled:
    result = await asyncio.wait_for(
        new_feature.run(),
        timeout=settings.new_feature_timeout,
    )
```

### Step 3: Document

Add to this guide under "Available Settings" section.

---

## Environment Variable Reference

| Setting          | Environment Variable       | Type         | Default                  | Required |
| ---------------- | -------------------------- | ------------ | ------------------------ | -------- |
| Redis URL        | `REDIS_URL`                | string       | `redis://localhost:6379` | No       |
| Redis TTL        | `REDIS_TTL_SECONDS`        | integer      | `3600`                   | No       |
| Redis Enabled    | `REDIS_ENABLED`            | boolean      | `true`                   | No       |
| Database URL     | `DATABASE_URL`             | string       | `sqlite:///...`          | No       |
| Workflow Timeout | `WORKFLOW_TIMEOUT_SECONDS` | float        | `120.0`                  | No       |
| Default Workflow | `DEFAULT_WORKFLOW_ID`      | string       | `magentic_fleet`         | No       |
| CORS Origins     | `CORS_ORIGINS`             | list[string] | `["*"]`                  | No       |
| CORS Credentials | `CORS_ALLOW_CREDENTIALS`   | boolean      | `true`                   | No       |
| Log Level        | `LOG_LEVEL`                | string       | `INFO`                   | No       |
| Server Host      | `SERVER_HOST`              | string       | `0.0.0.0`                | No       |
| Server Port      | `SERVER_PORT`              | integer      | `8000`                   | No       |

---

## Security Best Practices

### 1. Never Commit .env File

`.env` files contain secrets and should be gitignored:

```bash
# .gitignore
.env
.env.local
.env.production
```

### 2. Use Environment Variables in Production

Instead of `.env` file, use environment variables:

```bash
# Kubernetes
env:
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: redis-secret
        key: url

# Docker Compose
environment:
  - REDIS_URL=${REDIS_URL}
  - DATABASE_URL=${DATABASE_URL}
```

### 3. Rotate Secrets Regularly

Periodically rotate API keys and database credentials.

### 4. Logging Security

To prevent log injection and terminal escape manipulation, all workflow identifiers
and other user-controlled values are sanitized before logging using
`agentic_fleet.utils.logging_sanitize.sanitize_log_value`.

Removed characters:

```text
\n (newline)
\r (carriage return)
     (tab)
\u2028 (Unicode line separator)
\u2029 (Unicode paragraph separator)
\u0085 (next line)
\f (form feed)
\v (vertical tab)
\x1b (ESC / ANSI escape initiator)
```

Example usage in code:

```python
from agentic_fleet.utils.logging_sanitize import sanitize_log_value
logger.info("Created workflow %s", sanitize_log_value(workflow_id))
```

Sanitization affects only log output; internal IDs remain unchanged for lookup
and persistence. If future requirements expand the set of disallowed characters,
update `REMOVED_LOG_CHARS` in `logging_sanitize.py` and extend tests in
`tests/test_logging_sanitization.py`.

---

---

### Fast-Path Optimization

**Available Since**: 0.5.6

AgenticFleet supports fast-path routing for simple queries, bypassing the full multi-agent orchestration to provide sub-second responses.

```python
enable_fast_path: bool = True
fast_path_max_length: int = 100
fast_path_model: str = "gpt-5-mini"
```

**Environment Variables**:

```bash
# Enable/disable fast-path optimization (default: true)
# Accepted values: "1", "true", "yes" (case-insensitive) for enabled
# Any other value disables fast-path
ENABLE_FAST_PATH=true

# Maximum message length for fast-path eligibility (characters)
FAST_PATH_MAX_LENGTH=100

# OpenAI model to use for fast-path responses
FAST_PATH_MODEL=gpt-5-mini
```

**Usage**:

Fast-path automatically detects simple queries like:

- Simple acknowledgments: "ok", "thanks", "yes", "no"
- Short questions without complexity indicators
- Messages under 100 characters without code/implementation keywords

Complex queries requiring full orchestration:

- Messages containing keywords like "implement", "create", "code", "analyze"
- Multi-sentence requests
- Messages over 100 characters
- Technical or multi-step tasks

**Example**:

```bash
# Enable fast-path with custom model and length
ENABLE_FAST_PATH=1
FAST_PATH_MAX_LENGTH=150
FAST_PATH_MODEL=gpt-5-mini

# OpenAI credentials (required for fast-path)
OPENAI_API_KEY=your-api-key
# Optional: Use custom endpoint
OPENAI_BASE_URL=https://custom.openai.endpoint.com
```

**Performance Impact**:

- Simple queries: < 1 second (fast-path)
- Complex queries: 10-45 seconds (full orchestration with 5 agents)
- Fast-path uses a lightweight single LLM call vs multi-agent coordination

**Monitoring**:

Check logs for fast-path usage:

```text
[CHAT] Using fast-path for simple query: ok
[FAST-PATH] Processing message with gpt-5-mini: ok
[FAST-PATH] Completed response (15 chars)
```

---

## Additional Resources

- [Pydantic Settings Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Environment Variables Guide](https://12factor.net/config)
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)

---

**Last Updated**: Current Session
**Maintained By**: AgenticFleet Team
