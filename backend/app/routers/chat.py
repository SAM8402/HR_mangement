from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import get_agent
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.models.chat_feedback import ChatFeedback
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    intent: str = ""
    citations: list[dict] = []


class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: bool
    feedback_text: str | None = None
    session_id: str | None = None


# Lazy-load agent
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Non-streaming chat endpoint with Redis response caching."""
    # 1. Check cache
    query_hash = hashlib.sha256(f"{current_user.id}:{data.query}".encode()).hexdigest()
    cache_key = f"llm_response:{query_hash}"
    try:
        cached = await cache_service.get(cache_key)
        if cached:
            return ChatResponse(
                answer=cached["answer"],
                intent=cached["intent"],
                citations=cached.get("citations", []),
            )
    except Exception:
        pass

    agent = _get_agent()

    # Load session history from Redis (session memory)
    history_key = f"chat_history:{current_user.id}"
    history = await cache_service.get(history_key) or []
    
    # Feed last 10 messages of history to preserve context
    messages = []
    for msg in history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    
    messages.append(HumanMessage(content=data.query))

    initial_state = {
        "messages": messages,
        "intent": "",
        "context": "",
        "user_id": str(current_user.id),
        "rewritten_queries": [],
        "citations": [],
    }

    result = await agent.ainvoke(initial_state)

    # Extract response & citations
    answer = ""
    intent = result.get("intent", "")
    citations = result.get("citations", [])
    
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            answer = msg.content
            break

    # Store in history
    history.append({"role": "user", "content": data.query})
    history.append({"role": "assistant", "content": answer})
    if len(history) > 100:
        history = history[-100:]
    await cache_service.set(history_key, history, ttl=86400)

    # Cache the result in Redis
    try:
        cache_data = {"answer": answer, "intent": intent, "citations": citations}
        await cache_service.set(cache_key, cache_data, ttl=3600)
    except Exception:
        pass

    return ChatResponse(answer=answer, intent=intent, citations=citations)


@router.get("/stream")
async def chat_stream(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE streaming chat endpoint with simulated token-by-token streaming."""
    agent = _get_agent()

    async def event_generator() -> AsyncGenerator[str, None]:
        # Check cache first even in streaming
        query_hash = hashlib.sha256(f"{current_user.id}:{query}".encode()).hexdigest()
        cache_key = f"llm_response:{query_hash}"
        try:
            cached = await cache_service.get(cache_key)
            if cached:
                answer = cached["answer"]
                citations = cached.get("citations", [])
                
                # Stream cached answer
                words = answer.split(" ")
                for i, word in enumerate(words):
                    space = " " if i < len(words) - 1 else ""
                    yield f"data: {json.dumps({'content': word + space, 'done': False})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'content': '', 'done': True, 'citations': citations})}\n\n"
                return
        except Exception:
            pass

        # Load history
        history_key = f"chat_history:{current_user.id}"
        history = await cache_service.get(history_key) or []
        
        messages = []
        for msg in history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=query))

        initial_state = {
            "messages": messages,
            "intent": "",
            "context": "",
            "user_id": str(current_user.id),
            "rewritten_queries": [],
            "citations": [],
        }

        result = await agent.ainvoke(initial_state)

        answer = ""
        citations = result.get("citations", [])
        intent = result.get("intent", "")
        
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                answer = msg.content
                break

        # Simulate streaming token-by-token
        words = answer.split(" ")
        for i, word in enumerate(words):
            space = " " if i < len(words) - 1 else ""
            yield f"data: {json.dumps({'content': word + space, 'done': False})}\n\n"
            await asyncio.sleep(0.015)
            
        yield f"data: {json.dumps({'content': '', 'done': True, 'citations': citations})}\n\n"

        # Store in history
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 100:
            history = history[-100:]
        await cache_service.set(history_key, history, ttl=86400)

        # Cache response
        try:
            cache_data = {"answer": answer, "intent": intent, "citations": citations}
            await cache_service.set(cache_key, cache_data, ttl=3600)
        except Exception:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
):
    """Get chat history from Redis."""
    history_key = f"chat_history:{current_user.id}"
    history = await cache_service.get(history_key) or []
    return {"history": history}


@router.delete("/history")
async def clear_history(
    current_user: User = Depends(get_current_user),
):
    """Clear chat history."""
    await cache_service.delete(f"chat_history:{current_user.id}")
    return {"message": "Chat history cleared"}


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def post_feedback(
    data: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit thumbs up/down user feedback for a chatbot response."""
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
    return {"message": "Feedback submitted successfully", "id": str(feedback.id)}


@router.get("/evaluation/metrics")
async def get_evaluation_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Get summarized chat feedback metrics for the evaluation dashboard."""
    # 1. Total count
    total_res = await db.execute(select(func.count(ChatFeedback.id)))
    total_count = total_res.scalar() or 0

    # 2. Positive feedback count
    pos_res = await db.execute(select(func.count(ChatFeedback.id)).where(ChatFeedback.rating == True))
    pos_count = pos_res.scalar() or 0

    # 3. Negative feedback count
    neg_res = await db.execute(select(func.count(ChatFeedback.id)).where(ChatFeedback.rating == False))
    neg_count = neg_res.scalar() or 0

    satisfaction_rate = (pos_count / total_count * 100) if total_count > 0 else 100.0

    # 4. Fetch recent negative feedbacks to identify issues
    recent_neg_res = await db.execute(
        select(ChatFeedback)
        .where(ChatFeedback.rating == False)
        .order_by(desc(ChatFeedback.created_at))
        .limit(10)
    )
    recent_negatives = []
    for item in recent_neg_res.scalars().all():
        recent_negatives.append({
            "id": str(item.id),
            "query": item.query,
            "response": item.response,
            "feedback_text": item.feedback_text,
            "created_at": item.created_at.isoformat(),
        })

    return {
        "total_count": total_count,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "satisfaction_rate": round(satisfaction_rate, 2),
        "recent_negatives": recent_negatives,
    }
