"""Attendance tracking routes.

Provides endpoints for marking attendance, checking today's status,
and generating monthly or yearly reports.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceMarkRequest,
    AttendanceReportResponse,
    AttendanceResponse,
    AttendanceStatusResponse,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


async def _resolve_user_id(
    user_id: uuid.UUID | None,
    current_user: User,
) -> uuid.UUID:
    if user_id is None:
        return current_user.id
    if current_user.role not in ("admin", "manager", "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view other users",
        )
    return user_id


@router.post(
    "/mark", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED
)
async def mark_attendance(
    data: AttendanceMarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark today's attendance (check-in or check-out)."""
    record = await AttendanceService.mark_attendance(db, current_user.id, data.notes)
    return record


@router.get("/today", response_model=AttendanceStatusResponse)
async def today_status(
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's attendance status."""
    target_id = await _resolve_user_id(user_id, current_user)
    record = await AttendanceService.get_today_status(db, target_id)
    if not record:
        return AttendanceStatusResponse(
            date=date.today(), check_in=None, status="not_marked", notes=None
        )
    return AttendanceStatusResponse(
        id=record.id,
        date=record.date,
        check_in=record.check_in,
        status=record.status,
        notes=record.notes,
    )


@router.get("/report", response_model=AttendanceReportResponse)
async def monthly_report(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance report for a specific month."""
    target_id = await _resolve_user_id(user_id, current_user)
    report = await AttendanceService.get_monthly_report(db, target_id, year, month)
    return AttendanceReportResponse(
        records=[AttendanceResponse.model_validate(r) for r in report["records"]],
        total_present=report["total_present"],
        total_absent=report["total_absent"],
        total_late=report["total_late"],
        total_half_day=report["total_half_day"],
        total_wfh=report["total_wfh"],
    )


@router.get("/yearly", response_model=AttendanceReportResponse)
async def yearly_report(
    year: int = Query(..., ge=2020, le=2100),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance report for a full year."""
    target_id = await _resolve_user_id(user_id, current_user)
    report = await AttendanceService.get_yearly_report(db, target_id, year)
    return AttendanceReportResponse(
        records=[AttendanceResponse.model_validate(r) for r in report["records"]],
        total_present=report["total_present"],
        total_absent=report["total_absent"],
        total_late=report["total_late"],
        total_half_day=report["total_half_day"],
        total_wfh=report["total_wfh"],
    )
