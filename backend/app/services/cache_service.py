from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings


class CacheService:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    async def get(self, key: str) -> Any | None:
        if not self._redis:
            return None
        try:
            val = await self._redis.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._redis:
            return
        try:
            serialized = json.dumps(value, default=str) if not isinstance(value, str) else value
            await self._redis.set(key, serialized, ex=ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass

    async def delete_pattern(self, pattern: str) -> None:
        if not self._redis:
            return
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            pass

    # ── Convenience methods ──────────────────────────────────────────────

    async def get_leave_balance(self, user_id: str) -> Any | None:
        return await self.get(f"leave_balance:{user_id}")

    async def set_leave_balance(self, user_id: str, data: Any) -> None:
        await self.set(f"leave_balance:{user_id}", data, ttl=600)

    async def invalidate_leave_balance(self, user_id: str) -> None:
        await self.delete(f"leave_balance:{user_id}")

    async def get_work_updates(self, user_id: str) -> Any | None:
        return await self.get(f"work_updates:{user_id}")

    async def set_work_updates(self, user_id: str, data: Any) -> None:
        await self.set(f"work_updates:{user_id}", data, ttl=300)

    async def invalidate_work_updates(self, user_id: str) -> None:
        await self.delete(f"work_updates:{user_id}")

    async def cache_rag_query(self, query_hash: str, data: Any) -> None:
        await self.set(f"rag:{query_hash}", data, ttl=3600)

    async def get_rag_query(self, query_hash: str) -> Any | None:
        return await self.get(f"rag:{query_hash}")

    async def invalidate_rag_cache(self) -> None:
        await self.delete_pattern("rag:*")
        await self.delete_pattern("llm_response:*")


cache_service = CacheService()
