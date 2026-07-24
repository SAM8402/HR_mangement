"""Business logic for attendance tracking.

Handles daily check-in/out, status queries, and monthly or yearly
report generation with status counts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance

LATE_CUTOFF_HOUR = 10

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service layer encapsulating attendance business rules."""

    @staticmethod
    async def mark_attendance(
        db: AsyncSession, user_id: uuid.UUID, notes: str | None = None
    ) -> Attendance:
        """Check in (or check out if already checked in today). Automatically marks late after 10 AM."""
        today = date.today()
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    Attendance.date == today,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if not existing.check_out:
                existing.check_out = datetime.now(timezone.utc)
                logger.info("Checking out user %s", user_id)
            await db.flush()
            await db.refresh(existing)
            return existing

        now = datetime.now(timezone.utc)
        status = "late" if now.hour >= LATE_CUTOFF_HOUR else "present"
        logger.info("Checking in user %s", user_id)

        record = Attendance(
            user_id=user_id,
            date=today,
            check_in=now,
            status=status,
            notes=notes,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        logger.info("Check-in successful for user %s at %s", user_id, now)
        return record

    @staticmethod
    async def get_today_status(
        db: AsyncSession, user_id: uuid.UUID
    ) -> Attendance | None:
        """Return today's attendance record for the user, or None if not yet marked."""
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    Attendance.date == date.today(),
                )
            )
        )
        record = result.scalar_one_or_none()
        logger.info("Fetching today attendance for user %s", user_id)
        return record

    @staticmethod
    async def get_monthly_report(
        db: AsyncSession, user_id: uuid.UUID, year: int, month: int
    ) -> dict:
        """Return a monthly attendance report with per-status counts and full record list."""
        result = await db.execute(
            select(Attendance)
            .where(
                and_(
                    Attendance.user_id == user_id,
                    func.extract("year", Attendance.date) == year,
                    func.extract("month", Attendance.date) == month,
                )
            )
            .order_by(Attendance.date)
        )
        records = list(result.scalars().all())
        logger.info(
            "Fetching attendance for user %s from %04d-%02d", user_id, year, month
        )
        counts = AttendanceService._compute_counts(records)
        counts["records"] = records
        return counts

    @staticmethod
    async def get_yearly_report(
        db: AsyncSession, user_id: uuid.UUID, year: int
    ) -> dict:
        """Return a yearly attendance report with per-status counts and full record list."""
        result = await db.execute(
            select(Attendance)
            .where(
                and_(
                    Attendance.user_id == user_id,
                    func.extract("year", Attendance.date) == year,
                )
            )
            .order_by(Attendance.date)
        )
        records = list(result.scalars().all())
        logger.info("Fetching attendance for user %s from %04d", user_id, year)
        counts = AttendanceService._compute_counts(records)
        counts["records"] = records
        return counts

    @staticmethod
    def _compute_counts(records: list[Attendance]) -> dict:
        """Tally attendance records by status (present, absent, late, half_day, wfh)."""
        return {
            "total_present": sum(1 for r in records if r.status == "present"),
            "total_absent": sum(1 for r in records if r.status == "absent"),
            "total_late": sum(1 for r in records if r.status == "late"),
            "total_half_day": sum(1 for r in records if r.status == "half_day"),
            "total_wfh": sum(1 for r in records if r.status == "wfh"),
        }
