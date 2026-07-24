"""Work update routes.

Provides endpoints for creating, listing, editing, and deleting
daily work logs with optional filters for date, department, and user.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.models.work_update import WorkUpdate
from app.schemas.work_update import (
    WorkUpdateCreate,
    WorkUpdateResponse,
    WorkUpdateUpdate,
)
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api/work-updates", tags=["work-updates"])


@router.post("", response_model=WorkUpdateResponse, status_code=status.HTTP_201_CREATED)
async def create_work_update(
    data: WorkUpdateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a work update. Admin/manager/hr can assign to other users."""
    target_user_id = current_user.id
    if data.assigned_user_id and current_user.role in ("admin", "manager", "hr"):
        target_user_id = data.assigned_user_id

    update = WorkUpdate(
        user_id=target_user_id,
        title=data.title,
        description=data.description,
        date=data.date,
        department=data.department,
        tags=data.tags,
    )
    db.add(update)
    await db.flush()
    await db.refresh(update)
    await cache_service.invalidate_work_updates(str(current_user.id))
    logger.info("Work update created by user %s", current_user.id)
    return update


@router.get("/my", response_model=list[WorkUpdateResponse])
async def my_updates(
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get my work updates, optionally filtered by year/month."""
    stmt = select(WorkUpdate).where(WorkUpdate.user_id == current_user.id)
    if year is not None:
        stmt = stmt.where(func.extract("year", WorkUpdate.date) == year)
    if month is not None:
        stmt = stmt.where(func.extract("month", WorkUpdate.date) == month)
    stmt = stmt.order_by(WorkUpdate.date.desc())
    result = await db.execute(stmt)
    updates = list(result.scalars().all())
    logger.info(
        "Work updates list fetched for user %s (%d updates)",
        current_user.id,
        len(updates),
    )
    return updates


@router.get("/all", response_model=list[WorkUpdateResponse])
async def all_updates(
    user_id: uuid.UUID | None = Query(None),
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    department: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Get all work updates, optionally filtered by user_id, year, month, department."""
    stmt = select(WorkUpdate).order_by(WorkUpdate.created_at.desc())
    if user_id:
        stmt = stmt.where(WorkUpdate.user_id == user_id)
    if year is not None:
        stmt = stmt.where(func.extract("year", WorkUpdate.date) == year)
    if month is not None:
        stmt = stmt.where(func.extract("month", WorkUpdate.date) == month)
    if department:
        stmt = stmt.where(WorkUpdate.department == department)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{update_id}", response_model=WorkUpdateResponse)
async def get_update(
    update_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single work update."""
    result = await db.execute(select(WorkUpdate).where(WorkUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work update not found"
        )
    return update


@router.patch("/{update_id}", response_model=WorkUpdateResponse)
async def update_work_update(
    update_id: uuid.UUID,
    data: WorkUpdateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit own work update. Admin/manager/hr can edit any update."""
    result = await db.execute(select(WorkUpdate).where(WorkUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work update not found"
        )
    if update.user_id != current_user.id and current_user.role not in (
        "admin",
        "manager",
        "hr",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own updates",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(update, field, value)

    await db.flush()
    await db.refresh(update)
    await cache_service.invalidate_work_updates(str(current_user.id))
    return update


@router.delete("/{update_id}")
async def delete_work_update(
    update_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete own work update. Admin/manager/hr can delete any update."""
    result = await db.execute(select(WorkUpdate).where(WorkUpdate.id == update_id))
    update = result.scalar_one_or_none()
    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work update not found"
        )
    if update.user_id != current_user.id and current_user.role not in (
        "admin",
        "manager",
        "hr",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own updates",
        )

    await db.delete(update)
    await db.flush()
    await cache_service.invalidate_work_updates(str(current_user.id))
    return {"message": "Work update deleted"}
