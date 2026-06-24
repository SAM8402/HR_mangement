from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import search_similar
from app.db.session import async_session
from app.models.leave import LeaveBalance, LeaveType
from app.models.work_update import WorkUpdate


async def rag_tool(query: str) -> str:
    """Search the vector store and return relevant context."""
    results = await search_similar(query, k=5)
    if not results:
        return "No relevant documents found in the knowledge base."

    context_parts = []
    for r in results:
        context_parts.append(
            f"[Source: {r['metadata'].get('title', 'Unknown')}]\n{r['content']}"
        )
    return "\n\n---\n\n".join(context_parts)


async def leave_balance_tool(user_id: str) -> str:
    """Query leave balances for a user."""
    async with async_session() as db:
        result = await db.execute(
            select(LeaveBalance, LeaveType.name)
            .join(LeaveType, LeaveBalance.leave_type_id == LeaveType.id)
            .where(LeaveBalance.user_id == uuid.UUID(user_id))
        )
        rows = result.all()
        if not rows:
            return f"No leave balance found for user {user_id}."

        lines = [f"Leave Balances for user {user_id}:"]
        for balance, type_name in rows:
            lines.append(
                f"- {type_name.title()}: {balance.remaining_days} remaining "
                f"(used {balance.used_days}/{balance.total_days})"
            )
        return "\n".join(lines)


async def work_updates_tool(user_id: str) -> str:
    """Query recent work updates for a user."""
    async with async_session() as db:
        result = await db.execute(
            select(WorkUpdate)
            .where(WorkUpdate.user_id == uuid.UUID(user_id))
            .order_by(WorkUpdate.created_at.desc())
            .limit(10)
        )
        updates = result.scalars().all()
        if not updates:
            return f"No work updates found for user {user_id}."

        lines = [f"Recent work updates for user {user_id}:"]
        for u in updates:
            tags_str = ", ".join(u.tags) if u.tags else "none"
            lines.append(
                f"- [{u.date}] {u.title}: {u.description[:100]}... (Tags: {tags_str})"
            )
        return "\n".join(lines)


async def web_search_tool(query: str) -> str:
    """Fallback search on the web using DuckDuckGo."""
    from duckduckgo_search import DDGS
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if not results:
                return "No external web results found."
            lines = []
            for r in results:
                lines.append(f"[Web Source: {r.get('title', 'Unknown')}] ({r.get('href', '')})\n{r.get('body', '')}")
            return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"Web search failed: {str(e)}"

