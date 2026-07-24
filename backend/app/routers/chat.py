"""AI chat and feedback routes.

Provides endpoints for conversational AI (with streaming support),
session management, and user feedback collection for evaluating
assistant response quality.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import get_agent
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.chat_feedback import ChatFeedback
from app.models.user import User
from app.services.cache_service import cache_service
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str = ""
    citations: list[dict] = []
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: bool
    feedback_text: str | None = None
    session_id: str | None = None


class RenameRequest(BaseModel):
    title: str


_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


async def _resolve_session(user_id: str, session_id: str | None) -> str:
    if session_id:
        sessions = await memory_service.list_sessions(user_id)
        if any(s["session_id"] == session_id for s in sessions):
            return session_id
    return await memory_service.create_session(user_id)


# ── Session CRUD ──────────────────────────────────────────────────────────────


@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    sessions = await memory_service.list_sessions(str(current_user.id))
    return {"sessions": sessions}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    title: str = Query("New Chat", description="Optional session title"),
    current_user: User = Depends(get_current_user),
):
    session_id = await memory_service.create_session(str(current_user.id), title)
    return {"session_id": session_id, "title": title}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    await memory_service.delete_session(str(current_user.id), session_id)
    return {"message": "Session deleted"}


@router.put("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    data: RenameRequest,
    current_user: User = Depends(get_current_user),
):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    await memory_service.rename_session(
        str(current_user.id), session_id, data.title.strip()
    )
    return {"message": "Session renamed"}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    sessions = await memory_service.list_sessions(str(current_user.id))
    for s in sessions:
        if s["session_id"] == session_id:
            return s
    raise HTTPException(status_code=404, detail="Session not found")


# ── Chat Endpoints ────────────────────────────────────────────────────────────


@router.get("/history")
async def get_history(
    session_id: str = Query(None, description="Session ID, or create new if empty"),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    sid = session_id or await memory_service.create_session(uid)
    history = await memory_service.get_history(uid, sid)
    ltm = await memory_service.get_all_long_term(uid)
    return {"history": history, "session_id": sid, "long_term_memory": ltm}


@router.delete("/history")
async def clear_history(
    session_id: str = Query(None, description="Session ID, or clear all if empty"),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    if session_id:
        await memory_service.delete_session(uid, session_id)
    else:
        sessions = await memory_service.list_sessions(uid)
        for s in sessions:
            await memory_service.delete_session(uid, s["session_id"])
    return {"message": "Chat history cleared"}


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    session_id = await _resolve_session(uid, data.session_id)

    query_hash = hashlib.sha256(f"{uid}:{data.query}".encode()).hexdigest()
    cache_key = f"llm_response:{query_hash}"
    try:
        cached = await cache_service.get(cache_key)
        if cached:
            return ChatResponse(
                answer=cached["answer"],
                intent=cached["intent"],
                citations=cached.get("citations", []),
                session_id=session_id,
            )
    except Exception:
        pass

    agent = _get_agent()
    history = await memory_service.get_history(uid, session_id, limit=10)

    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=data.query))

    ltm = await memory_service.get_all_long_term(uid)
    facts = await memory_service.get_all_facts(uid)
    memory_context = ""
    if ltm:
        memory_context += f"User profile: {json.dumps(ltm)}"
    if facts:
        if memory_context:
            memory_context += "\n"
        memory_context += f"Learned facts: {json.dumps(facts)}"
    episodes = await memory_service.get_recent_episodes(uid, limit=3)
    if episodes:
        summaries = [e["summary"] for e in episodes if e.get("summary")]
        if summaries:
            if memory_context:
                memory_context += "\n"
            memory_context += f"Past sessions: {' | '.join(summaries[:3])}"

    initial_state = {
        "messages": messages,
        "intent": "",
        "context": memory_context,
        "user_id": uid,
        "rewritten_queries": [],
        "citations": [],
    }

    t0 = time.time()
    result = await agent.ainvoke(initial_state)
    elapsed = (time.time() - t0) * 1000

    await memory_service.record_execution(
        uid,
        session_id,
        "agent.ainvoke",
        {"query": data.query},
        result.get("intent", ""),
        elapsed,
    )

    answer = ""
    intent = result.get("intent", "")
    citations = result.get("citations", [])

    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            answer = msg.content
            break

    now = (
        __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat()
    )
    await memory_service.append_history(
        uid, session_id, {"role": "user", "content": data.query, "timestamp": now}
    )
    await memory_service.append_history(
        uid,
        session_id,
        {
            "role": "assistant",
            "content": answer,
            "citations": citations,
            "timestamp": now,
        },
    )
    await memory_service.touch_session(uid, session_id)

    for item in (data.query, answer):
        for prefix in ("My name is ", "I am ", "I work in ", "My role is "):
            if item.lower().startswith(prefix.lower()):
                fact_key = prefix.lower().replace(" ", "_").rstrip("_")
                fact_value = item[len(prefix) :].split(".")[0].strip()
                await memory_service.store_fact(uid, fact_key, fact_value)

    try:
        await cache_service.set(
            cache_key,
            {"answer": answer, "intent": intent, "citations": citations},
            ttl=3600,
        )
    except Exception:
        pass

    return ChatResponse(
        answer=answer, intent=intent, citations=citations, session_id=session_id
    )


@router.get("/stream")
async def chat_stream(
    query: str = Query(..., description="User query"),
    session_id: str = Query(None, description="Session ID, or create new if empty"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    sid = await _resolve_session(uid, session_id)
    agent = _get_agent()

    async def event_generator() -> AsyncGenerator[str, None]:
        query_hash = hashlib.sha256(f"{uid}:{query}".encode()).hexdigest()
        cache_key = f"llm_response:{query_hash}"
        try:
            cached = await cache_service.get(cache_key)
            if cached:
                answer = cached["answer"]
                citations = cached.get("citations", [])
                words = answer.split(" ")
                for i, word in enumerate(words):
                    space = " " if i < len(words) - 1 else ""
                    yield f"data: {json.dumps({'content': word + space, 'done': False, 'session_id': sid})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'content': '', 'done': True, 'citations': citations, 'session_id': sid})}\n\n"
                return
        except Exception:
            pass

        history = await memory_service.get_history(uid, sid, limit=10)
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        ltm = await memory_service.get_all_long_term(uid)
        facts = await memory_service.get_all_facts(uid)
        memory_context = ""
        if ltm:
            memory_context += f"User profile: {json.dumps(ltm)}"
        if facts:
            if memory_context:
                memory_context += "\n"
            memory_context += f"Learned facts: {json.dumps(facts)}"
        episodes = await memory_service.get_recent_episodes(uid, limit=3)
        if episodes:
            summaries = [e["summary"] for e in episodes if e.get("summary")]
            if summaries:
                if memory_context:
                    memory_context += "\n"
                memory_context += f"Past sessions: {' | '.join(summaries[:3])}"

        initial_state = {
            "messages": messages,
            "intent": "",
            "context": memory_context,
            "user_id": uid,
            "rewritten_queries": [],
            "citations": [],
        }

        t0 = time.time()
        result = await agent.ainvoke(initial_state)
        elapsed = (time.time() - t0) * 1000

        await memory_service.record_execution(
            uid,
            sid,
            "agent.ainvoke",
            {"query": query},
            result.get("intent", ""),
            elapsed,
        )

        answer = ""
        citations = result.get("citations", [])
        intent = result.get("intent", "")

        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                answer = msg.content
                break

        now = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat()
        )
        await memory_service.append_history(
            uid, sid, {"role": "user", "content": query, "timestamp": now}
        )
        await memory_service.append_history(
            uid,
            sid,
            {
                "role": "assistant",
                "content": answer,
                "citations": citations,
                "timestamp": now,
            },
        )
        await memory_service.touch_session(uid, sid)

        words = answer.split(" ")
        for i, word in enumerate(words):
            space = " " if i < len(words) - 1 else ""
            yield f"data: {json.dumps({'content': word + space, 'done': False, 'session_id': sid})}\n\n"
            await asyncio.sleep(0.015)

        yield f"data: {json.dumps({'content': '', 'done': True, 'citations': citations, 'session_id': sid})}\n\n"

        try:
            await cache_service.set(
                cache_key,
                {"answer": answer, "intent": intent, "citations": citations},
                ttl=3600,
            )
        except Exception:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def post_feedback(
    data: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = ChatFeedback(
        user_id=current_user.id,
        session_id=data.session_id or str(uuid.uuid4()),
        query=data.query,
        response=data.response,
        rating=data.rating,
        feedback_text=data.feedback_text,
    )
    db.add(feedback)
    await db.flush()

    if data.rating and data.session_id:
        await memory_service.store_episode(
            str(current_user.id),
            f"Chat: {data.query[:100]}",
            data.session_id,
            {"rating": "up", "feedback": (data.feedback_text or "")},
        )

    return {"message": "Feedback submitted successfully", "id": str(feedback.id)}


@router.get("/evaluation/metrics")
async def get_evaluation_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    total_res = await db.execute(select(func.count(ChatFeedback.id)))
    total_count = total_res.scalar() or 0
    pos_res = await db.execute(
        select(func.count(ChatFeedback.id)).where(ChatFeedback.rating == True)
    )
    pos_count = pos_res.scalar() or 0
    neg_res = await db.execute(
        select(func.count(ChatFeedback.id)).where(ChatFeedback.rating == False)
    )
    neg_count = neg_res.scalar() or 0
    satisfaction_rate = (pos_count / total_count * 100) if total_count > 0 else 100.0
    recent_neg_res = await db.execute(
        select(ChatFeedback)
        .where(ChatFeedback.rating == False)
        .order_by(desc(ChatFeedback.created_at))
        .limit(10)
    )
    recent_negatives = []
    for item in recent_neg_res.scalars().all():
        recent_negatives.append(
            {
                "id": str(item.id),
                "query": item.query,
                "response": item.response,
                "feedback_text": item.feedback_text,
                "created_at": item.created_at.isoformat(),
            }
        )
    return {
        "total_count": total_count,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "satisfaction_rate": round(satisfaction_rate, 2),
        "recent_negatives": recent_negatives,
    }
