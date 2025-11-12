"""Redis integration for Agentic Fleet.

This module provides utilities for setting up and using Redis for:
- Caching LLM responses
- Message storage and retrieval
- Rate limiting
- Conversation state management
"""

import asyncio
import logging
import os
from typing import Any, TypeVar
from uuid import uuid4

from langcache import LangCache
from pydantic import BaseModel
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RedisMessage(BaseModel):
    """A message in a conversation thread."""

    role: str
    content: str
    timestamp: float
    metadata: dict[str, Any] | None = None


class RedisCacheManager:
    """Manager for Redis integration with support for caching, message storage, and rate limiting."""

    _instance = None

    def __init__(
        self,
        redis_url: str | None = None,
        thread_id: str | None = None,
        max_messages: int = 100,
        **kwargs: Any,
    ) -> None:
        """Initialize the Redis cache manager.

        Args:
            redis_url: Optional Redis URL. If not provided, will use REDIS_URL from environment.
            thread_id: Optional thread ID for conversation tracking. Auto-generated if not provided.
            max_messages: Maximum number of messages to store per thread before trimming.
            **kwargs: Additional Redis client parameters. Recognized keys include:
                - ``langcache_server_url``: Override for LANGCACHE_SERVER_URL
                - ``langcache_api_key``: Override for LANGCACHE_API_KEY
                - ``langcache_cache_id``: Override for LANGCACHE_CACHE_ID
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.redis_url = redis_url
        self.thread_id = thread_id or f"thread_{uuid4().hex}"
        self.max_messages = max_messages
        self._client: Redis | None = None  # type: ignore
        self._async_client: AsyncRedis | None = None  # type: ignore
        self._langcache: LangCache | None = None

        self.langcache_server_url: str | None = kwargs.pop(
            "langcache_server_url", os.getenv("LANGCACHE_SERVER_URL")
        )
        self.langcache_api_key: str | None = kwargs.pop(
            "langcache_api_key", os.getenv("LANGCACHE_API_KEY")
        )
        self.langcache_cache_id: str | None = kwargs.pop(
            "langcache_cache_id", os.getenv("LANGCACHE_CACHE_ID")
        )

        self._client_params = kwargs

    @classmethod
    def get_instance(cls) -> "RedisCacheManager":
        """Get or create a singleton instance of the cache manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def client(self) -> Redis:  # type: ignore
        """Get the synchronous Redis client instance."""
        if self._client is None:
            self._client = Redis.from_url(
                self.redis_url, decode_responses=True, **self._client_params
            )
        return self._client

    @property
    def async_client(self) -> AsyncRedis:  # type: ignore
        """Get the asynchronous Redis client instance."""
        if self._async_client is None:
            self._async_client = AsyncRedis.from_url(
                self.redis_url, decode_responses=True, **self._client_params
            )
        return self._async_client

    @property
    def langcache(self) -> LangCache:
        """Get the LangCache instance."""
        if self._langcache is None:
            if not self.langcache_server_url:
                raise RuntimeError(
                    "LangCache server URL is not configured. "
                    "Set LANGCACHE_SERVER_URL or provide langcache_server_url to RedisCacheManager."
                )
            self._langcache = LangCache(
                server_url=self.langcache_server_url,
                api_key=self.langcache_api_key,
                cache_id=self.langcache_cache_id,
            )
            logger.debug(
                "Initialized LangCache client",
                extra={
                    "langcache_server_url": self.langcache_server_url,
                    "langcache_cache_id": self.langcache_cache_id,
                    "has_api_key": bool(self.langcache_api_key),
                },
            )
        return self._langcache

    # Message Storage Methods
    def _get_message_key(self, message_id: str) -> str:
        """Get the Redis key for a message."""
        return f"messages:{self.thread_id}:{message_id}"

    def _get_thread_key(self) -> str:
        """Get the Redis key for the message list of the current thread."""
        return f"thread:{self.thread_id}:messages"

    async def add_message(self, role: str, content: str, **metadata: Any) -> str:
        """Add a message to the current thread.

        Args:
            role: The role of the message sender (e.g., 'user', 'assistant')
            content: The message content
            **metadata: Additional metadata to store with the message

        Returns:
            The ID of the created message
        """
        message = RedisMessage(
            role=role,
            content=content,
            timestamp=asyncio.get_event_loop().time(),
            metadata=metadata or None,
        )

        message_id = f"msg_{uuid4().hex}"
        message_key = self._get_message_key(message_id)
        thread_key = self._get_thread_key()

        pipeline_info = {
            "thread_key": thread_key,
            "message_key": message_key,
            "max_messages": self.max_messages,
            "metadata_keys": sorted(metadata.keys()) if metadata else [],
        }

        logger.debug(
            "Redis pipeline storing message",
            extra={
                "redis_pipeline_info": pipeline_info,
                "message_id": message_id,
                "message_role": role,
            },
        )

        try:
            async with self.async_client.pipeline() as pipe:
                # Store message data (Redis pipeline ops return int synchronously)
                pipe.hset(message_key, mapping=message.model_dump())  # type: ignore
                # Add message ID to thread's message list
                pipe.lpush(thread_key, message_id)
                # Trim if needed
                if self.max_messages > 0:
                    pipe.ltrim(thread_key, 0, self.max_messages - 1)
                result = await pipe.execute()
        except RedisError:
            logger.exception(
                "Redis pipeline failed to store message",
                extra={
                    "redis_pipeline_info": pipeline_info,
                    "message_id": message_id,
                },
            )
            raise
        else:
            logger.debug(
                "Redis pipeline stored message",
                extra={
                    "redis_pipeline_info": pipeline_info,
                    "message_id": message_id,
                    "pipeline_result_len": len(result) if isinstance(result, list) else None,
                },
            )

        return message_id

    async def get_messages(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """Get messages from the current thread.

        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of message dictionaries
        """
        thread_key = self._get_thread_key()
        message_ids = await self.async_client.lrange(thread_key, offset, offset + limit - 1)

        if not message_ids:
            return []

        messages = []
        for msg_id in message_ids:
            message_key = self._get_message_key(msg_id)
            message_data = await self.async_client.hgetall(message_key)
            if message_data:
                messages.append(message_data)

        return messages

    async def clear_messages(self) -> None:
        """Clear all messages from the current thread."""
        thread_key = self._get_thread_key()
        message_ids = await self.async_client.lrange(thread_key, 0, -1)

        if not message_ids:
            return

        pipeline_info = {
            "thread_key": thread_key,
            "message_count": len(message_ids),
        }

        logger.debug(
            "Redis pipeline clearing messages",
            extra={"redis_pipeline_info": pipeline_info},
        )

        try:
            async with self.async_client.pipeline() as pipe:
                # Delete all message hashes
                for msg_id in message_ids:
                    await pipe.delete(self._get_message_key(msg_id))
                # Delete the thread's message list
                await pipe.delete(thread_key)
                result = await pipe.execute()
        except RedisError:
            logger.exception(
                "Redis pipeline failed to clear messages",
                extra={"redis_pipeline_info": pipeline_info},
            )
            raise
        else:
            logger.debug(
                "Redis pipeline cleared messages",
                extra={
                    "redis_pipeline_info": pipeline_info,
                    "pipeline_result_len": len(result) if isinstance(result, list) else None,
                },
            )

    # Connection Management
    async def ping(self) -> bool:
        """Check if the Redis server is reachable."""
        try:
            return await self.async_client.ping()
        except RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            self._client.close()
            self._client = None

        if self._async_client:
            await self._async_client.close()
            self._async_client = None

        self._langcache = None

    # Context manager support
    async def __aenter__(self) -> "RedisCacheManager":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


def get_redis_cache() -> RedisCacheManager:
    """Get or create a RedisCacheManager instance for dependency injection."""
    return RedisCacheManager.get_instance()


def get_async_redis_client() -> AsyncRedis:  # type: ignore
    """Get an async Redis client for use in FastAPI dependencies."""
    return RedisCacheManager.get_instance().async_client
