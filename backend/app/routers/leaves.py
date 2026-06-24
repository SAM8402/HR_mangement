from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave import (LeaveActionRequest, LeaveApplyRequest,
                               LeaveBalanceResponse, LeaveResponse,
                               LeaveTypeResponse, LeaveTypeUpdateRequest)
from app.services.cache_service import cache_service
from app.services.leave_service import LeaveService

router = APIRouter(prefix="/api/leaves", tags=["leaves"])


@router.post(
    "/apply", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED
)
async def apply_leave(
    data: LeaveApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply for leave."""
    try:
        leave = await LeaveService.apply_leave(db, current_user.id, data)
        await cache_service.invalidate_leave_balance(str(current_user.id))
        return leave
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my", response_model=list[LeaveResponse])
async def my_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get my leave history."""
    return await LeaveService.get_my_leaves(db, current_user.id)


@router.get("/balance", response_model=list[LeaveBalanceResponse])
async def my_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get my leave balances (cached in Redis)."""
    user_id = str(current_user.id)
    cached = await cache_service.get_leave_balance(user_id)
    if cached:
        return cached

    balances = await LeaveService.get_balance(db, current_user.id)
    await cache_service.set_leave_balance(user_id, balances)
    return balances


@router.get("/pending", response_model=list[LeaveResponse])
async def pending_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Get pending leaves for current user's approval."""
    return await LeaveService.get_pending_leaves(db, current_user.id)


@router.patch("/{leave_id}/approve", response_model=LeaveResponse)
async def approve_leave(
    leave_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Approve a leave request."""
    try:
        leave = await LeaveService.approve_leave(db, leave_id, current_user.id)
        await cache_service.invalidate_leave_balance(str(leave.applicant_id))
        return leave
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{leave_id}/reject", response_model=LeaveResponse)
async def reject_leave(
    leave_id: uuid.UUID,
    data: LeaveActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Reject a leave request."""
    try:
        return await LeaveService.reject_leave(
            db, leave_id, current_user.id, data.rejection_reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{leave_id}/cancel", response_model=LeaveResponse)
async def cancel_leave(
    leave_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending leave request."""
    try:
        leave = await LeaveService.cancel_leave(db, leave_id, current_user.id)
        await cache_service.invalidate_leave_balance(str(current_user.id))
        return leave
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/types/{type_id}", response_model=LeaveTypeResponse)
async def update_leave_type(
    type_id: uuid.UUID,
    data: LeaveTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Update leave type days per year (admin/manager only)."""
    try:
        leave_type = await LeaveService.update_leave_type_days(
            db, type_id, data.days_per_year
        )
        return leave_type
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/all", response_model=list[LeaveResponse])
async def all_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Get all leave requests (admin/manager/hr)."""
    return await LeaveService.get_all_leaves(db)
