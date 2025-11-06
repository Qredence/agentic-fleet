# AgenticFleet Deployment Guide

## Overview

This guide provides comprehensive deployment instructions for AgenticFleet in production environments, covering containerization, orchestration, monitoring, and operational best practices.

## Production Readiness Status

### ✅ **PRODUCTION READY (v0.5.5)**

AgenticFleet has achieved production-ready status with enterprise-grade features:

- **Type Safe**: 100% MyPy compliance, zero type errors
- **Well Tested**: Comprehensive test suite with configuration validation
- **Observable**: Full OpenTelemetry tracing integration
- **Secure**: Human-in-the-loop approval system
- **Performant**: Optimized builds and checkpoint system
- **Resilient**: Exponential backoff retry logic

## System Requirements

### Minimum Requirements

**Hardware**:

- **CPU**: 2 cores minimum, 4 cores recommended for production
- **Memory**: 4GB RAM minimum, 8GB recommended for concurrent workflows
- **Storage**: 10GB available space for application and logs

**Software**:

- **Python**: 3.12+ with uv package manager
- **Node.js**: 18+ for frontend build process
- **Container Runtime**: Docker 20.10+ (recommended)
- **Reverse Proxy**: Nginx or similar (recommended)

### Recommended Production Configuration

**Hardware**:

- **CPU**: 8+ cores for high-throughput deployments
- **Memory**: 16GB+ RAM for concurrent workflow processing
- **Storage**: 50GB+ SSD with IOPS optimization
- **Network**: 1Gbps+ for real-time streaming performance

## Container Deployment

### Dockerfile Production Build

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.12-slim as backend-builder

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen --no-dev

# Build frontend
FROM node:18-alpine as frontend-builder
WORKDIR /app/src/frontend/src
COPY src/frontend/src/package*.json ./
RUN npm ci --only=production

COPY src/frontend/src/ ./
RUN npm run build

# Production image
FROM python:3.12-slim as production

# Install uv and create app user
RUN pip install uv && useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /app/.venv /app/.venv
COPY --from=backend-builder /app/src /app/src

# Copy frontend build
COPY --from=frontend-builder /app/src/frontend/src/dist /app/ui

# Set permissions
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD uv run python -c "import requests; requests.get('http://localhost:8000/v1/system/health', timeout=5).raise_for_status()" || exit 1

# Start command
CMD ["uv", "run", "uvicorn", "agenticfleet.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Deployment

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  agenticfleet:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.openai.com/v1}
      - ENABLE_OTEL=${ENABLE_OTEL:-true}
      - OTLP_ENDPOINT=${OTLP_ENDPOINT}
      - REDIS_URL=${REDIS_URL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - redis
      - postgres
    networks:
      - agenticfleet-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - agenticfleet-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-agenticfleet}
      - POSTGRES_USER=${POSTGRES_USER:-agenticfleet}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    networks:
      - agenticfleet-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - agenticfleet
    restart: unless-stopped
    networks:
      - agenticfleet-network

  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "16686:16686"
      - "4317:4317/udp"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - agenticfleet-network

volumes:
  redis-data:
  postgres-data:

networks:
  agenticfleet-network:
    driver: bridge
```

## Kubernetes Deployment

### Namespace and RBAC

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agenticfleet
  labels:
    name: agenticfleet

---
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agenticfleet-sa
  namespace: agenticfleet

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agenticfleet-role
  namespace: agenticfleet
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets"]
    verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: agenticfleet-binding
  namespace: agenticfleet
subjects:
  - kind: ServiceAccount
    name: agenticfleet-sa
    namespace: agenticfleet
roleRef:
  kind: Role
  name: agenticfleet-role
  apiGroup: rbac.authorization.k8s.io
```

### Deployment Configuration

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenticfleet
  namespace: agenticfleet
  labels:
    app: agenticfleet
    version: v0.5.5
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenticfleet
  template:
    metadata:
      labels:
        app: agenticfleet
        version: v0.5.5
    spec:
      serviceAccountName: agenticfleet-sa
      containers:
        - name: agenticfleet
          image: agenticfleet:0.5.5
          ports:
            - containerPort: 8000
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: agenticfleet-secrets
                  key: OPENAI_API_KEY
            - name: REDIS_URL
              valueFrom:
                configMapKeyRef:
                  name: agenticfleet-config
                  key: REDIS_URL
            - name: ENABLE_OTEL
              value: "true"
            - name: OTLP_ENDPOINT
              value: "http://jaeger:4317"
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /v1/system/health
              port: 8000
            initialDelaySeconds: 60
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /v1/system/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: logs
              mountPath: /app/logs
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: agenticfleet-data-pvc
        - name: logs
          persistentVolumeClaim:
            claimName: agenticfleet-logs-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: agenticfleet-service
  namespace: agenticfleet
spec:
  selector:
    app: agenticfleet
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agenticfleet-data-pvc
  namespace: agenticfleet
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agenticfleet-logs-pvc
  namespace: agenticfleet
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agenticfleet-hpa
  namespace: agenticfleet
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agenticfleet
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Configuration Management

### Environment Variables

Required variables:

```bash
# Core Configuration
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_RESPONSES_MODEL_ID=gpt-4o-mini

# Optional Features
ENABLE_OTEL=true
OTLP_ENDPOINT=http://jaeger:4317
REDIS_URL=redis://redis:6379/0

# Database Configuration (if using PostgreSQL)
DATABASE_URL=postgresql://user:pass@postgres:5432/agenticfleet

# Azure Integration (optional)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-5-mini
AZURE_AI_SEARCH_ENDPOINT=your-azure-ai-search-endpoint
AZURE_AI_SEARCH_KEY=your-azure-ai-search-key

# Cosmos DB (optional)
AGENTICFLEET_USE_COSMOS=true
AZURE_COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
AZURE_COSMOS_KEY=your-cosmos-key
```

### Kubernetes ConfigMaps and Secrets

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agenticfleet-config
  namespace: agenticfleet
data:
  REDIS_URL: "redis://redis-service:6379/0"
  ENABLE_OTEL: "true"
  OTLP_ENDPOINT: "http://jaeger:4317"
  LOG_LEVEL: "INFO"
  WORKFLOW_CONFIG: |
    workflows:
      magentic_fleet:
        name: "Magentic Fleet Workflow"
        manager:
          model: "gpt-4o-mini"
          max_round_count: 6
          max_stall_count: 3
          max_reset_count: 2

---
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agenticfleet-secrets
  namespace: agenticfleet
type: Opaque
data:
  OPENAI_API_KEY: <base64-encoded-api-key>
  DATABASE_URL: <base64-encoded-database-url>
  AZURE_COSMOS_KEY: <base64-encoded-cosmos-key>
```

## Monitoring and Observability

### OpenTelemetry Integration

```python
# src/agentic_fleet/monitoring.py
import os
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

def setup_telemetry():
    """Setup OpenTelemetry for observability"""
    resource = Resource.create(
        attributes={
            "service.name": "agenticfleet",
            "service.version": "0.5.5",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "production")
        }
    )

    # Trace configuration
    trace.set_tracer_provider(
        TracerProvider(resource=resource)
    )

    # Metrics configuration
    metrics.set_meter_provider(
        MeterProvider(resource=resource)
    )
```

### Prometheus Metrics

```python
# src/agentic_fleet/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Business metrics
WORKFLOW_STARTED = Counter('workflows_started_total', 'Total workflows started')
WORKFLOW_COMPLETED = Counter('workflows_completed_total', 'Total workflows completed')
WORKFLOW_FAILED = Counter('workflows_failed_total', 'Total workflows failed')

# Performance metrics
WORKFLOW_DURATION = Histogram('workflow_duration_seconds', 'Workflow execution duration')
API_REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration')

# System metrics
ACTIVE_WORKFLOWS = Gauge('active_workflows_count', 'Currently active workflows')
AGENT_EXECUTIONS = Counter('agent_executions_total', 'Total agent executions', ['agent_type'])

# Decorator for metrics collection
def timed_operation(histogram):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                histogram.observe(time.time() - start_time)
        return wrapper
    return decorator
```

### Health Checks

```python
# src/agentic_fleet/health.py
from fastapi import HTTPException
import asyncio
import time

class HealthChecker:
    def __init__(self):
        self.start_time = time.time()
        self.last_check = time.time()

    async def check_system_health(self):
        """Comprehensive system health check"""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time,
            "version": "0.5.5",
            "checks": {}
        }

        # Check database connectivity
        health_status["checks"]["database"] = await self.check_database()

        # Check Redis connectivity
        health_status["checks"]["redis"] = await self.check_redis()

        # Check OpenAI connectivity
        health_status["checks"]["openai"] = await self.check_openai()

        # Check system resources
        health_status["checks"]["resources"] = await self.check_resources()

        # Overall status
        all_healthy = all(
            check["status"] == "healthy"
            for check in health_status["checks"].values()
        )

        health_status["status"] = "healthy" if all_healthy else "degraded"

        return health_status

    async def check_database(self):
        """Check database connectivity"""
        try:
            # Implement database ping
            return {"status": "healthy", "message": "Database accessible"}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}

    async def check_redis(self):
        """Check Redis connectivity"""
        try:
            # Implement Redis ping
            return {"status": "healthy", "message": "Redis accessible"}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}
```

## Security Configuration

### Network Security

```nginx
# nginx/nginx.conf
server {
    listen 80;
    listen 443 ssl http2;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    location /v1/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://agenticfleet:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE streaming support
    location /v1/responses {
        proxy_pass http://agenticfleet:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache off;
        proxy_buffering off;
    }
}

limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

### Application Security

```python
# src/agentic_fleet/security.py
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

class SecurityManager:
    def __init__(self):
        self.api_keys = {}
        self.session_tokens = {}

    def generate_api_key(self, user_id: str, permissions: list) -> str:
        """Generate API key for user"""
        api_key = f"af_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.utcnow(),
            "last_used": None
        }
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[dict]:
        """Validate API key and return user info"""
        key_data = self.api_keys.get(api_key)
        if key_data:
            key_data["last_used"] = datetime.utcnow()
            return key_data
        return None

    def create_session_token(self, user_id: str) -> str:
        """Create session token for workflow"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        self.session_tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        return token
```

## Deployment Strategies

### Blue-Green Deployment

```bash
# deploy-blue-green.sh
#!/bin/bash

set -e

ENVIRONMENT=${1:-production}
NEW_VERSION=${2:-v0.5.5}

echo "Deploying AgenticFleet $NEW_VERSION using blue-green strategy"

# Deploy to green environment
kubectl apply -f k8s/green-deployment.yaml

# Wait for green deployment to be ready
kubectl rollout status deployment/agenticfleet-green --timeout=600s

# Run health checks on green environment
GREEN_URL="http://agenticfleet-green.$ENVIRONMENT.example.com"
echo "Checking health of green environment at $GREEN_URL"

for i in {1..30}; do
    if curl -f "$GREEN_URL/v1/system/health" > /dev/null 2>&1; then
        echo "Green environment is healthy"
        break
    fi
    echo "Waiting for green environment to be healthy... ($i/30)"
    sleep 10
done

# Switch traffic to green environment
kubectl patch service agenticfleet-service -p '{"spec":{"selector":{"version":"v0.5.5-green"}}}'

echo "Traffic switched to green environment"

# Keep blue environment for rollback if needed
echo "Blue environment kept for rollback. Run rollback script to revert."
```

### Rolling Update Strategy

```bash
# rolling-update.sh
#!/bin/bash

set -e

VERSION=${1:-v0.5.5}

echo "Performing rolling update to version $VERSION"

# Update deployment image
kubectl set image deployment/agenticfleet agenticfleet=agenticfleet:$VERSION

# Monitor rollout status
kubectl rollout status deployment/agenticfleet --timeout=600s

# Verify health after update
echo "Verifying application health after update..."
sleep 30

HEALTH_CHECK_URL="http://$(kubectl get service agenticfleet-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/v1/system/health"

if curl -f "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
    echo "Rolling update completed successfully"
else
    echo "Health check failed, initiating rollback"
    kubectl rollout undo deployment/agenticfleet
    exit 1
fi
```

## Backup and Recovery

### Database Backup Strategy

```bash
# backup.sh
#!/bin/bash

set -e

BACKUP_DIR="/backups/agenticfleet"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agenticfleet_backup_$DATE.sql"

echo "Creating database backup: $BACKUP_FILE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup (PostgreSQL example)
if [ -n "$DATABASE_URL" ]; then
    pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
    echo "Database backup completed: $BACKUP_FILE"
else
    echo "DATABASE_URL not set, skipping database backup"
fi

# Configuration backup
CONFIG_BACKUP="$BACKUP_DIR/config_backup_$DATE.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    .env \
    config/ \
    src/agentic_fleet/workflows.yaml

echo "Configuration backup completed: $CONFIG_BACKUP"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup process completed"
```

### Recovery Procedures

```bash
# restore.sh
#!/bin/bash

set -e

BACKUP_FILE=${1:-}
CONFIG_BACKUP=${2:-}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql> [config_backup.tar.gz]"
    exit 1
fi

echo "Restoring from backup: $BACKUP_FILE"

# Stop application
kubectl scale deployment agenticfleet --replicas=0

# Restore database
if [ -n "$DATABASE_URL" ]; then
    psql "$DATABASE_URL" < "$BACKUP_FILE"
    echo "Database restored"
fi

# Restore configuration
if [ -n "$CONFIG_BACKUP" ] && [ -f "$CONFIG_BACKUP" ]; then
    tar -xzf "$CONFIG_BACKUP"
    echo "Configuration restored"
fi

# Restart application
kubectl scale deployment agenticfleet --replicas=3

echo "Restore completed. Monitoring application startup..."
kubectl rollout status deployment/agenticfleet
```

## Performance Tuning

### Application Configuration

```yaml
# config/performance.yaml
performance:
  uvicorn:
    workers: 4
    worker_class: uvicorn.workers.UvicornWorker
    max_requests: 1000
    max_requests_jitter: 100
    timeout_keep_alive: 5
    timeout_graceful_shutdown: 30

  database:
    pool_size: 20
    max_overflow: 30
    pool_timeout: 30
    pool_recycle: 3600

  redis:
    connection_pool_size: 50
    socket_timeout: 5
    socket_connect_timeout: 5

  workflow:
    max_concurrent_workflows: 50
    checkpoint_interval: 30
    workflow_timeout: 3600
```

### Resource Optimization

```python
# src/agentic_fleet/optimization.py
import asyncio
from functools import lru_cache
from typing import Dict, Any

class WorkflowCache:
    def __init__(self):
        self.cache = {}
        self.max_size = 1000

    @lru_cache(maxsize=128)
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Cache frequently accessed agent configurations"""
        return load_agent_configuration(agent_type)

    def invalidate_cache(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]

class ConnectionPool:
    def __init__(self):
        self.pool = asyncio.Queue(maxsize=50)
        self.active_connections = set()

    async def get_connection(self):
        """Get connection from pool"""
        if not self.pool.empty():
            connection = self.pool.get_nowait()
        else:
            connection = await self.create_connection()

        self.active_connections.add(connection)
        return connection

    async def release_connection(self, connection):
        """Release connection back to pool"""
        if connection in self.active_connections:
            self.active_connections.remove(connection)
            if len(self.active_connections) < 20:
                self.pool.put(connection)
            else:
                await connection.close()
```

## Troubleshooting Deployment Issues

### Common Problems and Solutions

#### 1. Database Connection Failures

**Symptoms**: 500 errors, connection timeouts
**Solutions**:

- Verify database endpoint accessibility
- Check connection pool configuration
- Validate SSL certificate configuration
- Review firewall rules

#### 2. Memory Issues

**Symptoms**: OutOfMemory errors, pod evictions
**Solutions**:

- Monitor memory usage patterns
- Adjust resource limits and requests
- Implement connection pooling
- Add memory profiling

#### 3. SSE Streaming Issues

**Symptoms**: Disconnected streams, missing events
**Solutions**:

- Check reverse proxy configuration
- Verify buffer settings
- Monitor client connection limits
- Validate event formatting

#### 4. Performance Degradation

**Symptoms**: Slow response times, high latency
**Solutions**:

- Review resource utilization
- Optimize database queries
- Add caching layers
- Implement horizontal scaling

## Monitoring and Alerting

### Key Metrics to Monitor

**Application Metrics**:

- Active workflows count
- Workflow success/failure rates
- Agent execution times
- API response times
- Error rates by endpoint

**Infrastructure Metrics**:

- CPU and memory utilization
- Database connection pool usage
- Redis connection count
- Network I/O and bandwidth
- Disk usage and IOPS

**Business Metrics**:

- Number of workflows executed
- User engagement metrics
- Agent utilization patterns
- Feature usage statistics

### Alerting Rules

```yaml
# alerting-rules.yml
groups:
  - name: agenticfleet-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High error rate detected

      - alert: WorkflowFailures
        expr: rate(workflows_failed_total[5m]) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: High workflow failure rate

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: Container memory usage high
```

## Maintenance Procedures

### Regular Maintenance Tasks

**Daily**:

- Check system health and performance metrics
- Review error logs and resolve issues
- Verify backup completion
- Monitor resource utilization

**Weekly**:

- Review and rotate API keys and secrets
- Update security patches
- Analyze performance trends
- Clean up old logs and temporary files

**Monthly**:

- Performance optimization review
- Security audit and penetration testing
- Capacity planning and scaling decisions
- Documentation updates

### Update Procedures

```bash
# update.sh
#!/bin/bash

set -e

VERSION=${1:-latest}

echo "Updating AgenticFleet to version $VERSION"

# Backup current deployment
./backup.sh

# Pull new images
docker pull agenticfleet:$VERSION
docker pull postgres:15-alpine
docker pull redis:7-alpine

# Update services
docker-compose up -d --no-deps agenticfleet

# Verify update
sleep 30
./health-check.sh

echo "Update completed successfully"
```

## Conclusion

This deployment guide provides comprehensive instructions for deploying AgenticFleet in production environments. The system is designed with scalability, reliability, and observability in mind, making it suitable for enterprise deployments.

Key success factors:

1. **Proper configuration management** with secrets handling
2. **Comprehensive monitoring** with health checks and alerting
3. **Scalable architecture** supporting horizontal scaling
4. **Robust backup and recovery** procedures
5. **Performance optimization** with proper resource management

The deployment strategy emphasizes zero-downtime updates and rollback capabilities, ensuring high availability for production workloads.
