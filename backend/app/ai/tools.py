"""Tool functions called by the AI agent.

Provides the concrete implementations invoked by the LangGraph agent
nodes for RAG queries, leave lookups, work updates, web fallback
search, leave application, and work update creation.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import search_similar
from app.db.session import async_session
from app.models.leave import LeaveBalance, LeaveType
from app.models.work_update import WorkUpdate
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


async def rag_tool(query: str) -> str:
    """Search the vector store and return relevant context."""
    logger.info("rag_tool called with query: %s", query[:100])
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
    logger.info("leave_balance_tool called for user: %s", user_id)
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
    logger.info("work_updates_tool called for user: %s", user_id)
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
    logger.info("web_search_tool called with query: %s", query[:100])
    from duckduckgo_search import DDGS

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if not results:
                return "No external web results found."
            lines = []
            for r in results:
                lines.append(
                    f"[Web Source: {r.get('title', 'Unknown')}] ({r.get('href', '')})\n{r.get('body', '')}"
                )
            return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"Web search failed: {str(e)}"


async def apply_leave_tool(
    user_id: str, leave_type: str, from_date: str, to_date: str, reason: str
) -> str:
    """Apply for leave in the system."""
    logger.info("apply_leave_tool called for user: %s, type: %s", user_id, leave_type)
    from datetime import date

    from app.schemas.leave import LeaveApplyRequest
    from app.services.leave_service import LeaveService

    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except ValueError:
        return (
            f"Invalid date format '{from_date}' or '{to_date}'. Please use YYYY-MM-DD."
        )

    data = LeaveApplyRequest(
        leave_type=leave_type,
        from_date=from_date_obj,
        to_date=to_date_obj,
        reason=reason,
    )

    async with async_session() as db:
        try:
            leave = await LeaveService.apply_leave(db, uuid.UUID(user_id), data)
            await db.commit()
            await cache_service.invalidate_leave_balance(user_id)
            return (
                f"Leave request submitted successfully!\n"
                f"  Type: {leave_type.title()}\n"
                f"  From: {from_date}\n"
                f"  To: {to_date}\n"
                f"  Business Days: {leave.business_days}\n"
                f"  Reason: {reason}\n"
                f"  Status: {leave.status.title()}"
            )
        except ValueError as e:
            return f"Failed to apply for leave: {str(e)}"


async def add_work_update_tool(
    user_id: str,
    title: str,
    description: str,
    date_str: str,
    tags: list[str] | None = None,
) -> str:
    """Add a work update entry."""
    logger.info("add_work_update_tool called for user: %s, title: %s", user_id, title)
    from datetime import date

    try:
        update_date = date.fromisoformat(date_str)
    except ValueError:
        return f"Invalid date format '{date_str}'. Please use YYYY-MM-DD."

    async with async_session() as db:
        update = WorkUpdate(
            user_id=uuid.UUID(user_id),
            title=title,
            description=description,
            date=update_date,
            tags=tags or [],
        )
        db.add(update)
        await db.flush()
        await db.refresh(update)
        await db.commit()
        await cache_service.invalidate_work_updates(user_id)
        tag_str = ", ".join(tags) if tags else "none"
        return (
            f"Work update created successfully!\n"
            f"  Title: {title}\n"
            f"  Date: {date_str}\n"
            f"  Tags: {tag_str}"
        )
