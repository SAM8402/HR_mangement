"""Multi-tier memory system for the AI assistant.

Provides 10 Redis-backed memory layers covering session, working,
long-term, episodic, semantic, procedural, state, execution,
knowledge (RAG), and retrieval (hybrid search) memory.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import desc, select

from app.core.config import settings
from app.db.session import async_session
from app.models.chat_session import ChatMessage, ChatSession


class MemoryService:
    """Multi-tier memory system for the AI assistant.

    Provides 10 memory layers:
    - Session Memory: active conversation sessions
    - Working Memory: current conversation context (messages)
    - Long-term Memory: persistent user facts and preferences
    - Episodic Memory: past interaction summaries
    - Semantic Memory: learned facts about the user
    - Procedural Memory: cached tool call patterns
    - State Memory: persisted agent state machine state
    - Execution Memory: tool call trace records
    - Knowledge Memory (RAG): ChromaDB-adjacent cache layer
    - Retrieval Cache: hybrid search result caching
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Open a Redis connection using the configured REDIS_URL."""
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def disconnect(self) -> None:
        """Close the Redis connection gracefully."""
        if self._redis:
            await self._redis.close()

    async def _ensure_redis(self) -> aioredis.Redis:
        """Lazy-init Redis if not already connected, then return the client."""
        if not self._redis:
            await self.connect()
        return self._redis

    # ────────────────────────────────────────────────────────────────────
    # 1. Session Memory — active conversation sessions
    # ────────────────────────────────────────────────────────────────────

    async def list_sessions(self, user_id: str) -> list[dict]:
        """Return all ChatSession metadata (id, title, timestamps, message count) for a user."""
        try:
            user_uuid = uuid.UUID(str(user_id))
        except ValueError:
            return []
        async with async_session() as db:
            result = await db.execute(
                select(ChatSession)
                .where(ChatSession.user_id == user_uuid)
                .order_by(desc(ChatSession.updated_at))
            )
            sessions = result.scalars().all()
            return [
                {
                    "session_id": str(s.id),
                    "title": s.title,
                    "created_at": s.created_at.isoformat() if s.created_at else "",
                    "updated_at": s.updated_at.isoformat() if s.updated_at else "",
                    "message_count": len(s.messages),
                }
                for s in sessions
            ]

    async def create_session(self, user_id: str, title: str = "New Chat") -> str:
        """Create a new ChatSession and return its UUID string."""
        try:
            user_uuid = uuid.UUID(str(user_id))
        except ValueError:
            # Fallback to a random generated UUID if invalid user_id format
            user_uuid = uuid.uuid4()
        async with async_session() as db:
            session = ChatSession(
                user_id=user_uuid,
                title=title,
            )
            db.add(session)
            await db.commit()
            return str(session.id)

    async def delete_session(self, user_id: str, session_id: str) -> None:
        """Delete a ChatSession (and its cascade messages) by session_id."""
        try:
            session_uuid = uuid.UUID(str(session_id))
        except ValueError:
            return
        async with async_session() as db:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            if session:
                await db.delete(session)
                await db.commit()

    async def rename_session(self, user_id: str, session_id: str, title: str) -> None:
        """Update the title of an existing ChatSession."""
        try:
            session_uuid = uuid.UUID(str(session_id))
        except ValueError:
            return
        async with async_session() as db:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            if session:
                session.title = title
                session.updated_at = datetime.now(timezone.utc)
                await db.commit()

    async def touch_session(self, user_id: str, session_id: str) -> None:
        """Bump the updated_at timestamp of a session (used to keep it from expiring)."""
        try:
            session_uuid = uuid.UUID(str(session_id))
        except ValueError:
            return
        async with async_session() as db:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            if session:
                session.updated_at = datetime.now(timezone.utc)
                await db.commit()

    # ────────────────────────────────────────────────────────────────────
    # 2. Working Memory — current conversation context (messages)
    # ────────────────────────────────────────────────────────────────────

    async def get_history(
        self, user_id: str, session_id: str, limit: int = 50
    ) -> list[dict]:
        """Return the last N ChatMessage entries for a session, oldest first."""
        try:
            session_uuid = uuid.UUID(str(session_id))
        except ValueError:
            return []
        async with async_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_uuid)
                .order_by(ChatMessage.created_at.asc())
            )
            messages = result.scalars().all()
            if len(messages) > limit:
                messages = messages[-limit:]
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "citations": m.citations or [],
                    "timestamp": m.created_at.isoformat() if m.created_at else "",
                }
                for m in messages
            ]

    async def append_history(self, user_id: str, session_id: str, entry: dict) -> None:
        """Persist a new message (role, content, citations) to a session."""
        try:
            session_uuid = uuid.UUID(str(session_id))
        except ValueError:
            return
        async with async_session() as db:
            msg = ChatMessage(
                session_id=session_uuid,
                role=entry.get("role", "user"),
                content=entry.get("content", ""),
                citations=entry.get("citations"),
            )
            db.add(msg)
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            if session:
                session.updated_at = datetime.now(timezone.utc)
            await db.commit()

    async def set_working_context(
        self, user_id: str, session_id: str, context: dict
    ) -> None:
        """Store ephemeral working context in Redis (TTL: 2 hours)."""
        r = await self._ensure_redis()
        key = f"working:{user_id}:{session_id}"
        await r.set(key, json.dumps(context, default=str), ex=7200)

    async def get_working_context(self, user_id: str, session_id: str) -> dict | None:
        """Retrieve ephemeral working context for a conversation."""
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

    async def set_long_term(
        self, user_id: str, key: str, value: Any, ttl: int = 2592000
    ) -> None:
        """Store a persistent user fact with index tracking (default TTL: 30 days)."""
        r = await self._ensure_redis()
        mem_key = f"ltm:{user_id}:{key}"
        await r.set(mem_key, json.dumps(value, default=str), ex=ttl)
        await r.sadd(f"ltm:{user_id}:index", key)

    async def get_long_term(self, user_id: str, key: str) -> Any | None:
        """Retrieve a persistent user fact by key."""
        r = await self._ensure_redis()
        raw = await r.get(f"ltm:{user_id}:{key}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    async def get_all_long_term(self, user_id: str) -> dict[str, Any]:
        """Return every stored long-term fact for a user."""
        r = await self._ensure_redis()
        keys = await r.smembers(f"ltm:{user_id}:index")
        result = {}
        for k in keys:
            val = await self.get_long_term(user_id, k)
            if val is not None:
                result[k] = val
        return result

    async def delete_long_term(self, user_id: str, key: str) -> None:
        """Remove a specific long-term fact and its index entry."""
        r = await self._ensure_redis()
        await r.delete(f"ltm:{user_id}:{key}")
        await r.srem(f"ltm:{user_id}:index", key)

    # ────────────────────────────────────────────────────────────────────
    # 4. Episodic Memory — past interaction summaries
    # ────────────────────────────────────────────────────────────────────

    async def store_episode(
        self, user_id: str, summary: str, session_id: str, metadata: dict | None = None
    ) -> str:
        """Save an episodic memory with auto-generated ID. Keeps only the 50 most recent episodes."""
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
        """Return the N most recent episodic memories for a user."""
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
        """Store or update a semantic fact. Increments confidence on each update (capped at 1.0)."""
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
        existing_data["confidence"] = min(
            existing_data.get("confidence", 0.0) + 0.2, 1.0
        )
        existing_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await r.set(key, json.dumps(existing_data, default=str), ex=2592000)
        await r.sadd(f"semantic:{user_id}:index", fact_key)

    async def get_fact(self, user_id: str, fact_key: str) -> Any | None:
        """Retrieve the value of a stored semantic fact."""
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
        """Return every stored semantic fact for a user."""
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

    async def store_procedure(
        self, domain: str, procedure: dict, ttl: int = 86400
    ) -> None:
        """Cache a tool-call pattern / system prompt by domain (default TTL: 1 day)."""
        r = await self._ensure_redis()
        await r.set(f"procedural:{domain}", json.dumps(procedure, default=str), ex=ttl)

    async def get_procedure(self, domain: str) -> dict | None:
        """Retrieve a cached procedure by domain name."""
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

    async def save_agent_state(
        self, user_id: str, session_id: str, state: dict
    ) -> None:
        """Persist the agent state machine's current state (TTL: 2 hours)."""
        r = await self._ensure_redis()
        key = f"agent_state:{user_id}:{session_id}"
        await r.set(key, json.dumps(state, default=str), ex=7200)

    async def load_agent_state(self, user_id: str, session_id: str) -> dict | None:
        """Restore a previously saved agent state."""
        r = await self._ensure_redis()
        raw = await r.get(f"agent_state:{user_id}:{session_id}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def clear_agent_state(self, user_id: str, session_id: str) -> None:
        """Remove a persisted agent state from Redis."""
        r = await self._ensure_redis()
        await r.delete(f"agent_state:{user_id}:{session_id}")

    # ────────────────────────────────────────────────────────────────────
    # 8. Execution Memory — tool call trace records
    # ────────────────────────────────────────────────────────────────────

    async def record_execution(
        self,
        user_id: str,
        session_id: str,
        tool_name: str,
        input_data: Any,
        output_data: Any,
        duration_ms: float,
    ) -> None:
        """Append a tool-call trace entry. Keeps only the last 50 records per session."""
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

    async def get_execution_trace(
        self, user_id: str, session_id: str, limit: int = 20
    ) -> list[dict]:
        """Return the N most recent tool-call trace entries for a session."""
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

    async def cache_knowledge(
        self, query_hash: str, data: Any, ttl: int = 3600
    ) -> None:
        """Cache a RAG result keyed by query hash (default TTL: 1 hour)."""
        r = await self._ensure_redis()
        await r.set(
            f"knowledge_cache:{query_hash}", json.dumps(data, default=str), ex=ttl
        )

    async def get_knowledge(self, query_hash: str) -> Any | None:
        """Retrieve a cached RAG result by query hash."""
        r = await self._ensure_redis()
        raw = await r.get(f"knowledge_cache:{query_hash}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    async def invalidate_knowledge_cache(self) -> None:
        """Delete all cached knowledge entries matching knowledge_cache:*."""
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
        """Cache a hybrid-search result keyed by SHA-256 hash (default TTL: 5 minutes). Returns the hash."""
        r = await self._ensure_redis()
        cache_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        key = f"retrieval_cache:{cache_hash}"
        await r.set(key, json.dumps(data, default=str), ex=ttl)
        return cache_hash

    async def get_retrieval(self, query: str) -> Any | None:
        """Retrieve a cached hybrid-search result by original query text."""
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
        """Delete all cached retrieval entries matching retrieval_cache:*."""
        r = await self._ensure_redis()
        keys = []
        async for key in r.scan_iter(match="retrieval_cache:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)


memory_service = MemoryService()
