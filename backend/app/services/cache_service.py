"""Redis-backed caching service.

Provides generic key-value operations with TTL, and convenience
methods for caching leave balances, work updates, and RAG queries.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis cache wrapper with serialisation and pattern deletion."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Open a Redis connection using the configured REDIS_URL."""
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def disconnect(self) -> None:
        """Close the Redis connection gracefully."""
        if self._redis:
            await self._redis.close()

    async def get(self, key: str) -> Any | None:
        """Retrieve a JSON-deserialised value by key. Returns None on cache miss or error."""
        if not self._redis:
            return None
        try:
            val = await self._redis.get(key)
            if val is None:
                logger.info("Cache miss for key %s", key)
                return None
            logger.info("Cache hit for key %s", key)
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception as e:
            logger.error("Redis connection error: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store a value with TTL (seconds). Non-string values are JSON-serialised."""
        if not self._redis:
            return
        try:
            serialized = (
                json.dumps(value, default=str) if not isinstance(value, str) else value
            )
            await self._redis.set(key, serialized, ex=ttl)
            logger.info("Setting cache key %s with TTL %d", key, ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        """Remove a single key from the cache."""
        if self._redis:
            try:
                await self._redis.delete(key)
                logger.info("Invalidating cache key %s", key)
            except Exception:
                pass

    async def delete_pattern(self, pattern: str) -> None:
        """Remove all keys matching a glob pattern (e.g. \"rag:*\")."""
        if not self._redis:
            return
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
                logger.info(
                    "Clearing all cache for pattern %s (%d keys)", pattern, len(keys)
                )
        except Exception:
            pass

    # ── Convenience methods ──────────────────────────────────────────────

    async def get_leave_balance(self, user_id: str) -> Any | None:
        """Retrieve cached leave balance for a user."""
        return await self.get(f"leave_balance:{user_id}")

    async def set_leave_balance(self, user_id: str, data: Any) -> None:
        """Cache leave balance data for a user (TTL: 10 minutes)."""
        await self.set(f"leave_balance:{user_id}", data, ttl=600)

    async def invalidate_leave_balance(self, user_id: str) -> None:
        """Remove cached leave balance for a user."""
        await self.delete(f"leave_balance:{user_id}")

    async def get_work_updates(self, user_id: str) -> Any | None:
        """Retrieve cached work updates for a user."""
        return await self.get(f"work_updates:{user_id}")

    async def set_work_updates(self, user_id: str, data: Any) -> None:
        """Cache work updates for a user (TTL: 5 minutes)."""
        await self.set(f"work_updates:{user_id}", data, ttl=300)

    async def invalidate_work_updates(self, user_id: str) -> None:
        """Remove cached work updates for a user."""
        await self.delete(f"work_updates:{user_id}")

    async def cache_rag_query(self, query_hash: str, data: Any) -> None:
        """Cache a RAG query result (TTL: 1 hour)."""
        await self.set(f"rag:{query_hash}", data, ttl=3600)

    async def get_rag_query(self, query_hash: str) -> Any | None:
        """Retrieve a cached RAG query result."""
        return await self.get(f"rag:{query_hash}")

    async def invalidate_rag_cache(self) -> None:
        """Clear all cached RAG responses and LLM responses."""
        await self.delete_pattern("rag:*")
        await self.delete_pattern("llm_response:*")


cache_service = CacheService()
