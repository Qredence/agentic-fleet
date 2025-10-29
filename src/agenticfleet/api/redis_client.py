"""Redis client for workflow execution state management."""

import logging

import redis.asyncio as redis

from agenticfleet.api.models.chat_models import ExecutionState, ExecutionStatus

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for managing workflow execution state."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600) -> None:
        """Initialize Redis client.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379 or Redis Cloud URL)
            ttl_seconds: Time-to-live for execution state (default 3600 = 1 hour)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._client: redis.Redis[str] | None = None

    async def connect(self) -> None:
        """Connect to Redis server."""
        if self._client is not None:
            return

        try:
            client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await client.ping()
        except Exception as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            raise

        self._client = client
        logger.info("Connected to Redis successfully")

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    def _get_key(self, execution_id: str) -> str:
        """Generate Redis key for execution state."""
        return f"execution:{execution_id}"

    async def save_state(self, state: ExecutionState) -> None:
        """Save execution state to Redis.

        Args:
            state: Execution state to save
        """
        if not self._client:
            raise RuntimeError("Redis client not connected")

        key = self._get_key(state.execution_id)
        value = state.model_dump_json()

        await self._client.setex(key, self.ttl_seconds, value)
        logger.debug(f"Saved state for execution {state.execution_id}")

    async def get_state(self, execution_id: str) -> ExecutionState | None:
        """Retrieve execution state from Redis.

        Args:
            execution_id: Execution ID to retrieve

        Returns:
            Execution state or None if not found
        """
        if not self._client:
            raise RuntimeError("Redis client not connected")

        key = self._get_key(execution_id)
        value = await self._client.get(key)

        if not value:
            return None

        return ExecutionState.model_validate_json(value)

    async def update_status(
        self, execution_id: str, status: ExecutionStatus, error: str | None = None
    ) -> None:
        """Update execution status.

        Args:
            execution_id: Execution ID
            status: New status
            error: Optional error message
        """
        state = await self.get_state(execution_id)
        if not state:
            logger.warning(f"Cannot update status - execution {execution_id} not found")
            return

        state.status = status
        if error:
            state.error = error

        await self.save_state(state)

    async def delete_state(self, execution_id: str) -> None:
        """Delete execution state from Redis.

        Args:
            execution_id: Execution ID to delete
        """
        if not self._client:
            raise RuntimeError("Redis client not connected")

        key = self._get_key(execution_id)
        await self._client.delete(key)
        logger.debug(f"Deleted state for execution {execution_id}")

    async def list_executions(self, pattern: str = "*") -> list[str]:
        """List all execution IDs matching pattern.

        Args:
            pattern: Redis key pattern (default: all executions)

        Returns:
            List of execution IDs
        """
        if not self._client:
            raise RuntimeError("Redis client not connected")

        keys = await self._client.keys(f"execution:{pattern}")
        return [key.replace("execution:", "") for key in keys]
