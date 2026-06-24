from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings


class MemoryService:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    async def _ensure_redis(self) -> aioredis.Redis:
        if not self._redis:
            await self.connect()
        return self._redis

    # ────────────────────────────────────────────────────────────────────
    # 1. Session Memory — active conversation sessions
    # ────────────────────────────────────────────────────────────────────

    async def list_sessions(self, user_id: str) -> list[dict]:
        r = await self._ensure_redis()
        key = f"chat_sessions:{user_id}"
        ids = await r.zrevrange(key, 0, -1)
        sessions = []
        for sid in ids:
            data = await r.hgetall(f"chat_session:{user_id}:{sid}")
            if data:
                sessions.append({
                    "session_id": sid,
                    "title": data.get("title", "New Chat"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": int(data.get("message_count", 0)),
                })
        return sessions

    async def create_session(self, user_id: str, title: str = "New Chat") -> str:
        r = await self._ensure_redis()
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await r.hset(f"chat_session:{user_id}:{session_id}", mapping={
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": "0",
        })
        await r.zadd(f"chat_sessions:{user_id}", {session_id: time.time()})
        return session_id

    async def delete_session(self, user_id: str, session_id: str) -> None:
        r = await self._ensure_redis()
        await r.delete(f"chat_history:{user_id}:{session_id}")
        await r.delete(f"working:{user_id}:{session_id}")
        await r.delete(f"agent_state:{user_id}:{session_id}")
        await r.delete(f"execution:{user_id}:{session_id}:trace")
        await r.delete(f"chat_session:{user_id}:{session_id}")
        await r.zrem(f"chat_sessions:{user_id}", session_id)

    async def rename_session(self, user_id: str, session_id: str, title: str) -> None:
        r = await self._ensure_redis()
        now = datetime.now(timezone.utc).isoformat()
        await r.hset(f"chat_session:{user_id}:{session_id}", "title", title)
        await r.hset(f"chat_session:{user_id}:{session_id}", "updated_at", now)

    async def touch_session(self, user_id: str, session_id: str) -> None:
        r = await self._ensure_redis()
        now = datetime.now(timezone.utc).isoformat()
        await r.hset(f"chat_session:{user_id}:{session_id}", "updated_at", now)
        await r.zadd(f"chat_sessions:{user_id}", {session_id: time.time()})

    # ────────────────────────────────────────────────────────────────────
    # 2. Working Memory — current conversation context (messages)
    # ────────────────────────────────────────────────────────────────────

    async def get_history(self, user_id: str, session_id: str, limit: int = 50) -> list[dict]:
        r = await self._ensure_redis()
        key = f"chat_history:{user_id}:{session_id}"
        raw = await r.lrange(key, -limit, -1)
        messages = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return messages

    async def append_history(self, user_id: str, session_id: str, entry: dict) -> None:
        r = await self._ensure_redis()
        key = f"chat_history:{user_id}:{session_id}"
        await r.rpush(key, json.dumps(entry, default=str))
        await r.ltrim(key, -100, -1)
        await r.hincrby(f"chat_session:{user_id}:{session_id}", "message_count", 1)

    async def set_working_context(self, user_id: str, session_id: str, context: dict) -> None:
        r = await self._ensure_redis()
        key = f"working:{user_id}:{session_id}"
        await r.set(key, json.dumps(context, default=str), ex=7200)

    async def get_working_context(self, user_id: str, session_id: str) -> dict | None:
        r = await self._ensure_redis()
        key = f"working:{user_id}:{session_id}"
        raw = await r.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    # ────────────────────────────────────────────────────────────────────
    # 3. Long-term Memory — persistent user facts, preferences
    # ────────────────────────────────────────────────────────────────────

    async def set_long_term(self, user_id: str, key: str, value: Any, ttl: int = 2592000) -> None:
        r = await self._ensure_redis()
        mem_key = f"ltm:{user_id}:{key}"
        await r.set(mem_key, json.dumps(value, default=str), ex=ttl)
        await r.sadd(f"ltm:{user_id}:index", key)

    async def get_long_term(self, user_id: str, key: str) -> Any | None:
        r = await self._ensure_redis()
        raw = await r.get(f"ltm:{user_id}:{key}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    async def get_all_long_term(self, user_id: str) -> dict[str, Any]:
        r = await self._ensure_redis()
        keys = await r.smembers(f"ltm:{user_id}:index")
        result = {}
        for k in keys:
            val = await self.get_long_term(user_id, k)
            if val is not None:
                result[k] = val
        return result

    async def delete_long_term(self, user_id: str, key: str) -> None:
        r = await self._ensure_redis()
        await r.delete(f"ltm:{user_id}:{key}")
        await r.srem(f"ltm:{user_id}:index", key)

    # ────────────────────────────────────────────────────────────────────
    # 4. Episodic Memory — past interaction summaries
    # ────────────────────────────────────────────────────────────────────

    async def store_episode(self, user_id: str, summary: str, session_id: str, metadata: dict | None = None) -> str:
        r = await self._ensure_redis()
        episode_id = str(uuid.uuid4())
        now = time.time()
        episode = {
            "episode_id": episode_id,
            "session_id": session_id,
            "summary": summary,
            "metadata": metadata or {},
            "timestamp": now,
        }
        await r.set(
            f"episodic:{user_id}:{episode_id}",
            json.dumps(episode, default=str),
            ex=604800,
        )
        await r.zadd(f"episodic:{user_id}:index", {episode_id: now})
        await r.zremrangebyrank(f"episodic:{user_id}:index", 0, -51)
        return episode_id

    async def get_recent_episodes(self, user_id: str, limit: int = 10) -> list[dict]:
        r = await self._ensure_redis()
        ids = await r.zrevrange(f"episodic:{user_id}:index", 0, limit - 1)
        episodes = []
        for eid in ids:
            raw = await r.get(f"episodic:{user_id}:{eid}")
            if raw:
                try:
                    episodes.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        return episodes

    # ────────────────────────────────────────────────────────────────────
    # 5. Semantic Memory — learned facts & concepts about the user
    # ────────────────────────────────────────────────────────────────────

    async def store_fact(self, user_id: str, fact_key: str, fact_value: Any) -> None:
        r = await self._ensure_redis()
        key = f"semantic:{user_id}:{fact_key}"
        existing = await r.get(key)
        if existing:
            try:
                existing_data = json.loads(existing)
            except json.JSONDecodeError:
                existing_data = {"value": existing, "confidence": 1.0}
        else:
            existing_data = {"value": None, "confidence": 0.0}
        existing_data["value"] = fact_value
        existing_data["confidence"] = min(existing_data.get("confidence", 0.0) + 0.2, 1.0)
        existing_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await r.set(key, json.dumps(existing_data, default=str), ex=2592000)
        await r.sadd(f"semantic:{user_id}:index", fact_key)

    async def get_fact(self, user_id: str, fact_key: str) -> Any | None:
        r = await self._ensure_redis()
        raw = await r.get(f"semantic:{user_id}:{fact_key}")
        if raw:
            try:
                data = json.loads(raw)
                return data.get("value")
            except json.JSONDecodeError:
                return raw
        return None

    async def get_all_facts(self, user_id: str) -> dict[str, Any]:
        r = await self._ensure_redis()
        keys = await r.smembers(f"semantic:{user_id}:index")
        result = {}
        for k in keys:
            val = await self.get_fact(user_id, k)
            if val is not None:
                result[k] = val
        return result

    # ────────────────────────────────────────────────────────────────────
    # 6. Procedural Memory — cached tool call patterns / system prompts
    # ────────────────────────────────────────────────────────────────────

    async def store_procedure(self, domain: str, procedure: dict, ttl: int = 86400) -> None:
        r = await self._ensure_redis()
        await r.set(f"procedural:{domain}", json.dumps(procedure, default=str), ex=ttl)

    async def get_procedure(self, domain: str) -> dict | None:
        r = await self._ensure_redis()
        raw = await r.get(f"procedural:{domain}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    # ────────────────────────────────────────────────────────────────────
    # 7. State Memory — persisted agent state machine state
    # ────────────────────────────────────────────────────────────────────

    async def save_agent_state(self, user_id: str, session_id: str, state: dict) -> None:
        r = await self._ensure_redis()
        key = f"agent_state:{user_id}:{session_id}"
        await r.set(key, json.dumps(state, default=str), ex=7200)

    async def load_agent_state(self, user_id: str, session_id: str) -> dict | None:
        r = await self._ensure_redis()
        raw = await r.get(f"agent_state:{user_id}:{session_id}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def clear_agent_state(self, user_id: str, session_id: str) -> None:
        r = await self._ensure_redis()
        await r.delete(f"agent_state:{user_id}:{session_id}")

    # ────────────────────────────────────────────────────────────────────
    # 8. Execution Memory — tool call trace records
    # ────────────────────────────────────────────────────────────────────

    async def record_execution(self, user_id: str, session_id: str, tool_name: str, input_data: Any, output_data: Any, duration_ms: float) -> None:
        r = await self._ensure_redis()
        key = f"execution:{user_id}:{session_id}:trace"
        entry = {
            "tool": tool_name,
            "input": str(input_data)[:500],
            "output": str(output_data)[:1000],
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await r.rpush(key, json.dumps(entry, default=str))
        await r.ltrim(key, -50, -1)

    async def get_execution_trace(self, user_id: str, session_id: str, limit: int = 20) -> list[dict]:
        r = await self._ensure_redis()
        key = f"execution:{user_id}:{session_id}:trace"
        raw = await r.lrange(key, -limit, -1)
        trace = []
        for item in raw:
            try:
                trace.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return trace

    # ────────────────────────────────────────────────────────────────────
    # 9. Knowledge Memory (RAG) — ChromaDB-adjacent cache layer
    # ────────────────────────────────────────────────────────────────────

    async def cache_knowledge(self, query_hash: str, data: Any, ttl: int = 3600) -> None:
        r = await self._ensure_redis()
        await r.set(f"knowledge_cache:{query_hash}", json.dumps(data, default=str), ex=ttl)

    async def get_knowledge(self, query_hash: str) -> Any | None:
        r = await self._ensure_redis()
        raw = await r.get(f"knowledge_cache:{query_hash}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    async def invalidate_knowledge_cache(self) -> None:
        r = await self._ensure_redis()
        keys = []
        async for key in r.scan_iter(match="knowledge_cache:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)

    # ────────────────────────────────────────────────────────────────────
    # 10. Retrieval Cache — hybrid search result caching
    # ────────────────────────────────────────────────────────────────────

    async def cache_retrieval(self, query: str, data: Any, ttl: int = 300) -> str:
        r = await self._ensure_redis()
        cache_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        key = f"retrieval_cache:{cache_hash}"
        await r.set(key, json.dumps(data, default=str), ex=ttl)
        return cache_hash

    async def get_retrieval(self, query: str) -> Any | None:
        r = await self._ensure_redis()
        cache_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        raw = await r.get(f"retrieval_cache:{cache_hash}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    async def invalidate_retrieval_cache(self) -> None:
        r = await self._ensure_redis()
        keys = []
        async for key in r.scan_iter(match="retrieval_cache:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)


memory_service = MemoryService()
